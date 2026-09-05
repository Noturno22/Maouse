# Spec — Voz Profissional: cloud-first STT com fallback local (2026-09-05)

## Contexto e problema

A funcionalidade de voz do Mãouse (feature PRO `voice`) é hoje, na prática,
não-fiável para o utilizador. Queixas observadas em teste real e reportadas:

1. **Comandos diretos não funcionam** — com o default `voice_always_on=False`,
   dizer "pausa" / "clica" sem dizer antes "jarvis" não faz nada.
2. **Flow de wake word frágil** — ao dizer "jarvis", o primeiro comando carrega o
   Whisper local na hora (20-70 s em silêncio, sem feedback de UI), e o
   reconhecimento pequeno erra muito (em teste, um "sim" foi transcrito como
   "Seguindo!" e fala baixa deu texto vazio).
3. **Não liga / sem feedback** — em Free o recurso está Pro-locked, e mesmo a
   ligar não há estados claros na UI; sons e rótulos são amadores e não
   localizados ("VOZ ON", "IA <A PENSAR>").
4. **Bug de captura** já corrigido nesta sessão: `_capture_utterance` trimava o
   buffer para 0.45 s sempre, enviando só o fim da frase ao transcritor.

Decisões do proprietário:
- O reconhecimento deve ser **cloud quando houver internet** (mais preciso,
  sobretudo para PT com sotaque angolano), com **fallback local** offline.
- A voz é um recurso pago e **deve funcionar perfeitamente nos planos pagos**.

## Meta / critérios de sucesso

- Ligar a voz dá feedback imediato e localizado (preparar → pronta → a ouvir → a
  pensar → ação), via `voice_bar`/toast e som.
- Comandos diretos (sem "jarvis") funcionam por defeito quando ligados.
- O 1.º comando após ligar executa em **≤ 3 s** (backend STT escolhido e
  aquecido em background; nada de períodos de 20-70 s em silêncio).
- Reconhecimento sensivelmente melhor: Groq `whisper-large-v3-turbo` quando
  online; Whisper small local como fallback offline.
- Frases bem ditas deixam de produzir "Não entendi"; quando acontece, é
  substantivo, localizado e pede para repetir.
- VAD com piso de ruído adaptativo (não precisa de falar alto) — resolve o caso
  real de capturas ~450-800 RMS em volta do limiar fixo 550.
- Tudo localizado via `i18n` (sem strings EN hardcoded).

## Não-objetivos (v1)

- Sem relay de STT primeiro-party no servidor de licenças. O endpoint é
  configurável (`stt_base_url`) para que um relay Mãouse seja drop-in no futuro;
  v1 usa a chave do utilizador (Groq) + fallback local.
- Sem streaming contínuo cloud: captura por frases curtas (já implementado no VAD).
- Sem UI de teste de microfone dedicada (fica para mais tarde).
- Sem mudanças ao pipeline de LLM de conversa (`core/llm.py`) além de reutilização.

## Arquitetura

### 1. `core/stt.py` (novo) — camada STT

Três classes, sem novas dependências (urllib, como o resto do projeto):

- **`CloudSTT(cfg)`**
  - `ping()` → verifica chave + reachability com timeout de 2 s (um POST de
    microfone de silêncio ou HEAD ao endpoint); devolve `True/False`.
  - `transcribe(pcm_int16) -> str` → envia WAV 16k mono (encoder wave em
    memória) a `{base}/audio/transcriptions` com `model`, `temperature=0`,
    timeout de 15 s (o resultado devolve `""` em erro — o router cai para local).
  - Base/configurado por `stt_provider` (default groq), `stt_model`
    (`whisper-large-v3-turbo`), `stt_base_url`, `stt_api_key_env`
    (default `GROQ_API_KEY`, reutiliza `core.llm._load_api_key`).
- **`LocalSTT(cfg)`**
  - Wraps do atual `_get_whisper`/`_transcribe` (migrados do `core/voice.py`):
    faster-whisper small int8, lazy + thread-safe.
  - `preload()` para aquecer em background no arranque.
  - `transcribe(pcm_int16) -> str` com `language="pt"`, `beam_size=5`.
- **`STTRouter(cfg)`**
  - `backend()` → `"cloud"` se `ping()` OK (cache com TTL ~60 s), senão
    `"local"`; visto do exterior por uma única API `transcribe(pcm)`.
  - `stt_provider == "cloud"` força cloud (falha→local); `"local"` força local;
    `"auto"` (default) escolhe.

### 2. `core/voice.py` — mudanças

- `self._stt = STTRouter(cfg)` no `__init__`.
- `_transcribe(pcm)` delega no router (remove lógica Whisper daqui).
- `start()`: continua a abrir mic + Vosk (sempre), e lança **thread de
  aquecimento** em background: `stt.ping()` (cloud) ou `stt.local.preload()`
  conforme `stt_provider`; só depois marca `status="ready"`. Enquanto isso
  `status="preparing"`.
- **Comandos diretos por defeito**: default `voice_always_on: bool = True`.
  No modo sempre-ligado, o Vosk serve apenas de **detetor de fala** (final
  não-vazio) e o `_capture_utterance` (VAD) apanha a frase; o PCM capturado vai
  a `self._stt.transcribe()` numa worker thread e é despachado
  (reusa `_dispatch`). Sem dependência de wake word; `_handle_vosk_result`
  mantém-se como gatilho + modo wake word preservado quando
  `voice_always_on=False`.
- **VAD adaptativo**: `_rms` baseline contínuo (janela ~1.5 s de silêncio para
  recalibrar); gatilho = `rms > max(baseline * 1.6, 300)`; fim = `rms < 380`.
- `status` exposto à UI: `"off" | "preparing" | "ready" | "listening" |
  "thinking" | "stt:{cloud|local}"`. Remover `print()`s de ruído → `core.log`.
- Mensagens TTS embutidas ("Sim?", "Nao ouvi nada.", "Nao entendi.") → `i18n`
  (`voice.prompt`, `voice.not_heard`, `voice.not_understood`), com `tr()` (i18n
  é headless-safe).
- `toggle()` e `stop()` mantêm o contrato atual (a UI / tray já usam).

### 3. Config (`config.py`)

- `voice_always_on: bool = True` (mudança de default).
- `stt_provider: str = "auto"` (`"auto" | "cloud" | "local"`).
- `stt_model: str = "whisper-large-v3-turbo"`.
- `stt_base_url: str = "https://api.groq.com/openai/v1"`.
- `stt_api_key_env: str = "GROQ_API_KEY"`.
- Persistência em `settings.json` (mesmo padrão dos campos `voice_*` atuais).
- Nota: `settings.json` atual com `voice_enabled: false` continua a ser
  respeitado (voz não liga sozinha sem o utilizador a ligar).

### 4. UI / feedback (`ui/voice_bar.py`, `ui/main_window.py`, `settings_dlg.py`)

- `voice_bar` mostra estados localizados: A PREPARAR / PRONTA [ouve jarvis] /
  A OUVIR / A PENSAR / (off esconde). Backend ativo pequeno: `stt:groq` /
  `stt:local`. Cores atuais mantidas.
- `_toggle_voice` ganha tratamento assíncrono: ligar já mostra "VOZ A PREPARAR"
  e o botão fica marcado quando `status != off`.
- `settings_dlg.py`: grupo "Voz" com
  - combo "Reconhecimento": Automático / Cloud (chave) / Local;
  - checkbox "Comandos diretos (sem dizer 'jarvis')" → `voice_always_on`;
  - campo/aviso "Chave Groq (GROQ_API_KEY)" com link para `.env.example`.
  (Rótulos i18n.)
- Toasts já existentes (`VOZ ON/OFF`) passam a `i18n` (`toast.voice_on/off`
  já existem — garantir posterioridade).

### 5. i18n — novas chaves

`voice.prompt`, `voice.not_heard`, `voice.not_understood`,
`voice.status.preparing`, `voice.status.ready`, `voice.status.listening`,
`voice.status.thinking`, `voice.backend.cloud`, `voice.backend.local`,
`settings.voice.stt_provider`, `settings.voice.direct_commands`,
`settings.voice.groq_key`. Todas com as 6 línguas (PT, EN, ES, FR, DE, IT,
PT_BR) — padrão existente.

### 6. Fluxo de dados (modo sempre-ligado, default)

1. `start()`: abre mic+Vosk; thread-background prepara STT; `status=preparing`.
2. Streams do mic → `_audio_q` (Vosk a correr em `_loop` para fala/gate).
3. Vosk final não-vazio → `_capture_utterance()` apanha frase inteira (VAD
   adaptativo) → worker thread: `stt.transcribe(pcm)` → `_dispatch(text)`.
4. `_dispatch` reusa regras locais (`core.nlu`) → fila de comandos → engine; ou
   conversa via `core.llm` (inalterado).
5. UI faz polling de `status` (já existe em `_tick`) e mostra estados.

## Erros e degradação

- Sem internet/chave → router usa local (Whisper small). `status` mostra
  `stt:local`.
- Sem key e sem Whisper local → `start()` falha com mensagem localizada
  ("Voz indisponível") e `status=off`.
- Cloud lenta/timeout (transcribe > 15 s) → router re-avalia e cai para local nessa frase.
- Erros de transcrição "vazios" → TTS "Não ouvi — repete, por favor" (i18n).

## Licença (planos pagos)

`voice` continua em `PRO_LOCKED`. Com Pro ativo, a voz deve funcionar
diretamente: cloud usando a chave configurada ou local. O spec assume que o
cliente Pro traz/chave Groq do utilizador em v1; um relay primeiro-party fica
fora de scope, mas `stt_base_url` já existe na config para o suportar no futuro
(sem mudanças de código no cliente).

## Testes

- `tests/test_stt.py` (novo):
  - router escolhe cloud quando `ping()` OK; cai para local se falhar;
  - `CloudSTT.transcribe` envia WAV válido + `model` certo (transporte fake);
  - `LocalSTT` lazy-load, `preload` thread-safe;
  - `voice_always_on` default `True`; `stt_provider` normalize.
- `tests/test_voice.py` (atualizar): manter todos os dispatch/Área (fake chat,
  fila, TTS) a passar com o novo default; novos testes para o fluxo
  sempre-ligado (gate por fala → captura → router) com STT fake.
- `tools/test_voice_runtime.py`: alargar para imprimir backend escolhido,
  latência da frase e transcrição + ação parseada (uso real com microfone).
- Antes do fim: `pytest -q` (baseline 120 testes; falha ambiental pré-existente
  `test_active_license_defaults_to_free` ignorada), `py_compile` dos ficheiros
  alterados, `tools/test_voice_llm.py` (23 PASS).

## Ficheiros afetados

- Novo: `core/stt.py`, `tests/test_stt.py`.
- Alterados: `core/voice.py`, `config.py`, `settings.json` (persistência),
  `ui/voice_bar.py`, `ui/main_window.py` (`_toggle_voice`, `_tick`),
  `settings_dlg.py`, `i18n.py`, `tests/test_voice.py`, `tools/test_voice_runtime.py`,
  `.env.example` (documentar `GROQ_API_KEY` para STT).