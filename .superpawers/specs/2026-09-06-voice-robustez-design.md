# Voz Robusta — Design (STT/voice: veto de ruído, mic profissional, fallback local)

- **Data:** 2026-09-06
- **Estado:** aprovado (design aprovado pelo utilizador a 2026-09-06)
- **Branch:** `feature/license-dialog-modernize`
- **Área:** voz (feature Pro-locked)
- **Pré-requisitos:** voz cloud-first com fallback local já em produção local (`core/stt.py`, `core/voice.py`)

## 1. Contexto

A voz funciona fim-a-fim (STT cloud Groq Whisper `whisper-large-v3-turbo` com
fallback local faster-whisper, captura com VAD adaptativo `_NoiseFloor`, self-deaf
anti-eco). A validação real com a api.groq.com expôs três lacunas de qualidade
que impedem o produto de ser "profissional":

1. **Falso disparo por ruído ambiente.** O VAD inicia captura quando o RMS passa o
   `trip_level`; um ambiente ruidoso (ventoinha, ar condicionado, chuva) pode
   ultrapassar o limiar e, combinado com uma alucinação do Vosk (partials), o clip
   de ruído é **enviado para a Groq**: gasta um round-trip pago/lento e alucina texto
   (verifica-se "Thank you." em silêncio/near-silence). O `_NoiseFloor` só recalibra
   em amostras de silêncio abaixo do limiar, logo uma sala persistentemente ruidosa
   mantém o limiar baixo e o risco alto.
2. **Microfone sem gestão.** O stream usa `sd.default.device[0]`; se o dispositivo
   falhar ou estiver ausente, a falha é apenas escrita para consola — o utilizador
   não vê nada, não há seleção de dispositivo e o erro é mudo.
3. **Fallback local fraco.** faster-whisper corre com `vad_filter=False`,
   `beam_size=5`, `condition_on_previous_text=True` (behavior por omissão) — mais
   lento e mais propenso a alucinar em silêncio; sem net, a qualidade offline sofre.

## 2. Objetivo e não-objetivos

### Objetivo
- Rejeitar clips **sem fala real** antes de qualquer chamada STT (cloud **ou** local),
  eliminando ruído/alucinações sem gastar round-trip nem CPU.
- Permitir **escolher o microfone** no UI, persistir a escolha e tornar qualquer
  falha de dispositivo **visível** (estado + razão + toast), sem nunca crashar.
- Tornar o **fallback local** decente para uso offline (VAD on, idioma pt, beam
  menor, sem condicionamento em texto anterior), com parâmetros em `Config`.

### Não-objetivos (YAGNI)
- Toasts/feedback de erro de rede no STT cloud e métricas de latência ao vivo
  (não selecionadas pelo utilizador).
- First-run onboarding guiado (mic + chave Groq).
- Hot-plug de microfones a meio da execução (o dispositivo é re-procurado no
  próximo arranque/toggle).
- Novas dependências Python.

## 3. Decisões de design

1. **Gate de qualidade de captura** num módulo puro numpy (`core/voice_quality.py`),
   executado em `_listen_and_dispatch` **depois** de `_capture_utterance` e **antes**
   de `STTRouter.transcribe`, nos dois backends. Captura rejeitada segue o mesmo
   caminho silencioso da captura vazia (sem `not_heard`, sem chamada STT); a razão
   fica em log debug. Filtros: energia global + vozeamento (cobertura + desvio
   padrão do ZCR), que distingue fala de ruído tonal/estacionário (ventoinha) e
   preserva comandos curtos ("clica").
2. **Gestão de microfone** com campo de config `mic_device`, módulo utilitário
   `core/audio_devices.py`, combo no Settings > Voz e estado de erro dedicado na
   voice bar com toast danger na transição para erro.
3. **Fallback local** com parâmetros configuráveis em `Config` e `LocalSTT` a consumir
   esses parâmetros com defaults seguros (`getattr`), passados a `model.transcribe`.

## 4. Arquitetura e componentes

Fluxo de voz (inalterado) com gate inserido:

```
captura (_capture_utterance: VAD _NoiseFloor + preroll/silence-tail)
   -> [CaptureQualityGate.evaluate]  (NOVO)
        rejeitada  -> caminho "sem fala" (silêncio/log debug)
        aceite     -> STTRouter.transcribe (cloud -> fallback local)
```

### 4.1 `core/voice_quality.py` (novo) — `CaptureQualityGate`

API mínima, sem dependências além de `numpy`:

- `CaptureQualityGate(rms_min: float = 200.0, voicing_coverage: float = 0.15,
  frame_ms: int = 30, zcr_std_min: float = 0.04)`
- `evaluate(pcm_int16: np.ndarray, trip_level: float) -> bool`
- `reject_reason() -> str | None` — última razão: `None` (aceite), `"energy"`,
  `"voicing"` ou `"short"`.

Critérios (por ordem):
1. **Energia global** — `rms_total = sqrt(mean(pcm^2))`. Se
   `rms_total < max(trip_level * 0.75, rms_min)` → rejeita `"energy"`.
2. **Frames de fala** — partição em frames de `frame_ms` (30ms). Um frame conta como
   fala se `rms_frame >= trip_level * 1.2`. Se `n_frames < 1` ou clip com
   duração `< 0.2s` → rejeita `"short"`.
3. **Cobertura** — `n_speech_frames >= max(3, voicing_coverage * n_frames)`; senão
   rejeita `"voicing"`.
4. **Vozeamento (ZCR)** — para `zcr` por frame de fala
   (`zcr = 0.5 * mean(|sign_diff|)`; frames com `rms_frame == 0` são excluídos do
   cálculo do desvio); se `std(zcr_frames_fala) < zcr_std_min` → rejeita `"voicing"`.
   Fala alterna voiced (ZCR baixo) / unvoiced (ZCR alto) → desvio alto;
   ruído tonal/estacionário tem ZCR quase constante → desvio ~0.
5. Aceite em caso contrário.

`reject_reason()` devolve a primeira razão que falhou na última chamada a
`evaluate`. `evaluate` com `pcm` vazio/curto devolve `False` (razão `"short"`),
sem exceções (guards numéricos; evitar divisão por zero).

### 4.2 `core/audio_devices.py` (novo)

- `list_input_devices() -> list[tuple[int, str]]` — envolve `sd.query_devices()`;
  só dispositivos com `max_input_channels > 0`; falha na query → `[]`.
- `select_device(pref: str | None) -> int | None` — `None`/`""` → dispositivo de
  entrada por omissão do sistema; senão: match **por substring do nome**
  (case-insensitive); se não, interpreta como índice (aceitar `"0"`); se não,
  eleva `DeviceError` com a lista dos disponíveis.
- `DeviceError(Exception)` com mensagem clara.

### 4.3 `config.py`

Novos campos em `Config` (com as interações load/save corretas):
- `mic_device: str = ""` — vazio = default do sistema; **persistido em
  settings.json** (por utilizador) e lido por `load_settings`/`save_settings`.
- `whisper_vad_filter: bool = True`
- `whisper_beam_size: int = 3`
- `whisper_language: str = "pt"`

`whisper_*` não são expostos no UI nesta fase (só defaults seguros em `Config`).

### 4.4 `core/voice.py`

- `VoiceEngine.__init__`: guarda `self._mic_device = cfg.mic_device` e
  `self.mic_error: str | None = None`.
- Abertura do stream em `_open_stream`/start: usar `select_device(self._mic_device)`;
  em `PortAudioError` (ou `DeviceError`) → `self.mic_error = <razão>`, status
  `"error"` (não prepara STT), **sem crash**.
- `mic_error` zerado quando um novo stream abre com sucesso.
- `_listen_and_dispatch`: instanciar um `CaptureQualityGate` (único por engine) e,
  após captura não-vazia, `if not gate.evaluate(pcm, trip_level): return` (log debug).
  O `trip_level` usado é o valor do `_NoiseFloor` no momento (acessível).
- Estados: manter os existentes (`preparing/ready/listening/thinking/wake/off`) e
  acrescentar `"error"` (só para falha de mic). O `_loop` não processa áudio quando
  status `"error"` (mesmo guard do `"off"`).
- `_toggle_voice`: se `mic_error` → toast danger (`danger=True`) em vez de arrancar.

### 4.5 `core/stt.py` — `LocalSTT`

Consome (via `getattr`, com defaults seguros):
- `language = cfg.whisper_language` (default `"pt"`)
- `vad_filter = cfg.whisper_vad_filter` (default `True`)
- `beam_size = cfg.whisper_beam_size` (default `3`)
- `condition_on_previous_text = False` (fixo — reduz alucinação em silêncio)

Mantém: `cpu_threads=4`, `compute_type="int8"`, modelo de `cfg.whisper_model`
(default `"small"`). Sem alterações de interface (a router `STTRouter` não muda).

### 4.6 UI

- `ui/settings_dlg.py` — no grupo Voz, adicionar combo **"Microfone"**: primeiro
  item `""` ("Por omissão do sistema") + um item por dispositivo de
  `list_input_devices()` (mostrar nome; valor interno = nome, para robustez a
  mudanças de índice). Guardar em `cfg.mic_device` no `_save`. Se a listagem
  devolver `[]`, mostrar label de aviso (chave nova) em vez do combo.
- `ui/voice_bar.py` — o `_tick`/`update_state` mapeia o estado `"error"` para o
  texto `voice.mic_error_status` + tooltip com a razão (`mic_error`).
- `ui/main_window.py` — na transição do status para `"error"` (com `mic_error`
  preenchido), mostrar toast danger uma única vez (flag por transição; reset no
  próximo arranque bem-sucedido).

### 4.7 `i18n.py` — novas chaves (7 línguas: pt/en/es/fr/de/it/pt_BR)

- `settings.voice.mic_label` — "Microfone"
- `settings.voice.mic_default` — "Por omissão do sistema"
- `settings.voice.mic_list_failed` — aviso quando não há dispositivos/query falha
- `voice.mic_error_status` — texto do estado na voice bar ("MICROFONE INACESSÍVEL")
- `voice.mic_error_tip` — tooltip (conteúdo: motivo + dica de verificação do nivel)

Sem outras chaves novas. `tr(key)` continua com 1 argumento (sem fallback).

## 5. Tratamento de erros e casos limite

- **Sem mic / query falha:** `list_input_devices()` → `[]`; Settings mostra aviso;
  `_toggle_voice` → toast danger; status `"error"`.
- **Dispositivo removido a meio:** `PortAudioError` na abertura → `mic_error`
  preenchido, status `"error"`, sem crash; próximo toggle re-tenta (re-seleção).
- **Gate numérico:** `pcm` vazio/curto → `False` com `"short"`; frame com
  `rms_frame == 0` excluído do ZCR; sem exceções.
- **Sala persistentemente ruidosa:** `trip_level` adapta-se; o gate continua a
  rejeitar clips sem variação de vozeamento.
- **Comandos curtos legítimos:** `coverage >= 0.15` e `>= 3 frames` garantem que
  "clica"/"abre" (0.3–0.5s) passam.

## 6. Testes

| Suíte | Casos |
|---|---|
| `tests/test_voice_quality.py` (novo) | silêncio→rejeita `"energy"`; zero-array→rejeita `"short"`; seno 440Hz→rejeita `"voicing"`; fala simulada (tons modulados + bursts)→aceite; clip <0.2s→`"short"`; parâmetros (`voicing_coverage`, `rms_min`, `trip_level`) têm efeito; `reject_reason()` após aceite = `None` |
| `tests/test_audio_devices.py` (novo) | select por substring de nome; por índice; `""`/`None`→default; desconhecido→`DeviceError`; `list_input_devices` só devolve entradas; falha de query→`[]` (injetar fake query) |
| `tests/test_stt.py` (extensão) | FakeModel: `LocalSTT.transcribe` passa `language="pt"`, `vad_filter=True`, `beam_size=3`, `condition_on_previous_text=False`; defaults via `getattr` quando campo em falta |
| `tests/test_voice_direct.py` (extensão) | gate rejeitadora → `_dispatch`/STT **não** chamado, sem `not_heard`; `sd.Stream` monkeypatched a levantar `PortAudioError` → `start()` sem crash e `mic_error` preenchido; `_toggle_voice` com `mic_error` → toast danger e sem arranque |
| `tests/test_config.py` (extensão) | defaults novos (`mic_device=""`, `whisper_vad_filter=True`, `whisper_beam_size=3`, `whisper_language="pt"`); round-trip de `mic_device` em settings.json |

## 7. Critérios de aceitação

- Suíte completa verde, exceto a única falha ambiental conhecida
  (`test_licensing.py::test_active_license_defaults_to_free`, máquina dev com PRO).
- `ruff check` limpo nos ficheiros tocados; `py_compile` ok.
- Zero novas dependências.
- `tools/test_voice_runtime.py` continua a funcionar (pipeline inalterado para o
  utilizador; o gate apenas rejeita clips sem fala antes do STT).
- Sem regressão dos fixes de eco self-deaf / resume (testes de `test_voice_direct.py`
  existentes continuam verdes).

## 8. Fora de âmbito (explícito)

- Toasts para falha de rede/STT cloud e métricas de latência ao vivo (decisão do
  utilizador).
- First-run onboarding (mic + chave) — posterior.
- Hot-plug automático de microfones; mudanças de volume de sistema.
- Alterações ao `GESTOS`/licença/web (pertencem ao plano-maior subsequente).