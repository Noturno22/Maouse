# Mãouse Remote — Teclado e Rato Remotos

Documento técnico de referência do subsistema de **controlo remoto** (rato + teclado
a partir do telemóvel). **Parte 1** descreve exactamente como funciona hoje, fase a fase,
com referências `ficheiro:linha`. **Parte 2** faz a análise de lacunas face às soluções
de referência do mercado. **Parte 3** é o plano para chegar a esse nível.

Estado do repositório em **2026-09-28**. Documento irmão: `RECONHECIMENTO_MAOS.md`
(reconhecimento por gestos, via câmara).

| | |
|---|---|
| **Domínio** | mobile · remote · Linux · CI |
| **Sócio responsável pelo domínio** | **Fortuna** (`josefortunafortuna54-byte`) — sócio-função, 4% com vesting |
| **Produzido por** | pipeline de agentes de IA da Luar Studio Angola (modelo "empresa nativa de IA", cf. `BUSSINES/07_ADMINISTRACAO/ESTRUTURA_DA_EMPRESA.md` §2) sob responsabilidade de domínio do Fortuna |
| **Âmbito** | `mobile/maouse-mobile/` (cliente) + `core/remote.py`, `core/mouse_ctl.py` (servidor) |
| **Plataformas** | 🟡 Windows validado · 🔴 macOS inexistente · 🟠 Linux por confirmar |

> **Nota de proveniência.** A análise que originou este documento foi produzida por
> agentes de IA a partir de leitura directa do código. Todas as afirmações
> estruturais foram **verificadas no repositório** (ver §1.14). O que este documento
> **não** é: uma revisão de produção executada em hardware. Não houve teste com rato
> ou teclado físicos durante a redacção — ver a Onda 0 da Parte 3.

---

## ÍNDICE

- [Parte 1 — Como funciona hoje](#parte-1--como-funciona-hoje)
  - [1.1 Visão geral da arquitectura](#11-visão-geral-da-arquitectura)
  - [1.2 Transporte e formato de mensagem](#12-transporte-e-formato-de-mensagem)
  - [1.3 Ciclo de vida da ligação](#13-ciclo-de-vida-da-ligação)
  - [1.4 Rato — do toque ao pixel (mobile)](#14-rato--do-toque-ao-pixel-mobile)
  - [1.5 Rato — injecção no desktop](#15-rato--injecção-no-desktop)
  - [1.6 Teclado — do texto à tecla (mobile)](#16-teclado--do-texto-à-tecla-mobile)
  - [1.7 Teclado — injecção no desktop](#17-teclado--injecção-no-desktop)
  - [1.8 Acentos e Unicode](#18-acentos-e-unicode)
  - [1.9 Segurança e modelo de ameaça actual](#19-segurança-e-modelo-de-ameaça-actual)
  - [1.10 Cobertura de testes](#110-cobertura-de-testes)
  - [1.11 Limitações conhecidas](#111-limitações-conhecidas)
  - [1.12 Mapa de ficheiros](#112-mapa-de-ficheiros)
  - [1.13 Referência de configuração](#113-referência-de-configuração)
  - [1.14 Verificação desta auditoria](#114-verificação-desta-auditoria)
  - [1.15 Descoberta automática do PC (mDNS)](#115-descoberta-automática-do-pc-mdns)
  - [1.16 Controlo remoto por Bluetooth (BLE)](#116-controlo-remoto-por-bluetooth-ble)
- [Parte 2 — Lacunas face ao mercado](#parte-2--lacunas-face-ao-mercado)
  - [2.1 Como o mercado faz](#21-como-o-mercado-faz)
  - [2.2 Tabela comparativa](#22-tabela-comparativa)
  - [2.3 As 7 lacunas estruturais](#23-as-7-lacunas-estruturais)
- [Parte 3 — Plano para nível profissional](#parte-3--plano-para-nível-profissional)
  - [3.0 Princípio: segurança antes de conforto](#30-princípio-segurança-antes-de-conforto)
  - [3.1 Onda 0 — Instrumentação e correções de bloqueio](#31-onda-0--instrumentação-e-correções-de-bloqueio)
  - [3.2 Onda 1 — Rato com feel profissional](#32-onda-1--rato-com-feel-profissional)
  - [3.3 Onda 2 — Robustez da ligação](#33-onda-2--robustez-da-ligação)
  - [3.4 Onda 3 — Teclado profissional](#34-onda-3--teclado-profissional)
  - [3.5 Onda 4 — Superfície de produto](#35-onda-4--superfície-de-produto)
  - [3.6 Roadmap](#36-roadmap)
  - [3.7 Métricas de aceitação](#37-métricas-de-aceitação)
  - [3.8 Riscos e não-objetivos](#38-riscos-e-não-objetivos)

---

# Parte 1 — Como funciona hoje

## 1.1 Visão geral da arquitectura

O controlo remoto é uma **segunda via de entrada**, independente do motor de gestos por
câmara. As duas partilham o mesmo `MouseCtl` — o que é deliberate (o rato é um só) e é
também a origem de uma condição de corrida documentada em [1.11](#111-limitações-conhecidas) #6.

```
┌─────────────────────────── TELEMÓVEL (Expo 57) ───────────────────────────┐
│                                                                             │
│  RemoteScreen.tsx                                                           │
│    ├─ touchpad (1 dedo) ──────────▶ move(dx, dy)      [relativo, px]        │
│    ├─ scroll    (2 dedos) ───────▶ scroll(dx, dy)                            │
│    ├─ tap 1/2/3 dedos ───────────▶ gesture(tap|click)                        │
│    ├─ hold 380 ms ───────────────▶ press/release  [arrastar]                  │
│    └─ TextInput + teclas ────────▶ text(str) · key(nome)                     │
│                                                                             │
│  RemoteClient (remoteClient.ts)                                             │
│    move    → acumulador fracionário → flush a cada 24 ms                     │
│    key/text→ imediato, 1 mensagem por acção                                   │
│    ping    → 15 s                                                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │  WebSocket  ws://IP:8765   ← PLAINTEXT
                                │  1 comando = 1 frame JSON
                                ▼
┌─────────────────────────── DESKTOP (Python) ───────────────────────────────┐
│                                                                             │
│  core/remote.py — asyncio server (thread dedicada + event loop próprio)      │
│    auth (token 64 bits) → dispatch por 'cmd'                                 │
│      move      → MouseCtl.move_by()      [relativo, clamp ao ecrã]           │
│      move_to   → mouse.position = (x,y) [absoluto, clamp 0..1]               │
│      click     → SendInput / pynput                                         │
│      press/rel → press_left / release_left                                   │
│      scroll    → MOUSEEVENTF_WHEEL (dy × 120)                                │
│      key       → mapa de nomes → pynput Key                                 │
│      text      → keyboard.type() → injecção caractere a caractere            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                ▼
                    Windows: ctypes SendInput (caminho rápido)
                    fallback: pynput (SetCursorPos / SendInput)
```

**Princípio de desenho dominante actual: um comando por mensagem, sem estado no
transporte.** O protocolo é elementar e legível — não há batching de comandos, nem
sequenciamento, nem número de sequência. A única medida de robustez é o
acumulador fraccionário de movimento e o batch de texto.

## 1.2 Transporte e formato de mensagem

| Aspecto | Implementação | Referência |
|---|---|---|
| Protocolo | WebSocket | `remoteClient.ts:84` |
| Esquema | **`ws://` forçado** — o cliente *remove* `wss://` do input do utilizador e reconstrói sempre em `ws://` | `remoteClient.ts:33-41` |
| Porto | `8765` (configurável 1024–65535) | `config.py:207`, `ui/settings_dlg.py:373-376` |
| Bind | `0.0.0.0` por omissão | `config.py:209` |
| TLS | **nenhum** — `serve()` sem `ssl=` | `core/remote.py:227-231` |
| Tamanho máx. msg | 2 MB | `core/remote.py:44` |
| Formato | JSON, 1 comando por frame | `remoteClient.ts:171-175` |

O `buildWsUrl` é o ponto de bloqueio mais relevante em matéria de segurança:

```ts
// src/services/remoteClient.ts:33-41
export function buildWsUrl(host: string, port: string | number): string {
  const h = String(host || '')
    .trim()
    .replace(/^wss:\/\//i, '')     // ← strip explícito de TLS
    .replace(/^ws:\/\//i, '')
    .replace(/\/+$/, '');
  const p = String(port || '8765').trim();
  return `ws://${h}:${p}`;          // ← sempre plaintext
}
```

Um utilizador que introduza conscientemente `wss://` recebe `ws://` sem aviso. **Não é
possível activar TLS a partir da app.**

### Vocabulário de comandos

| Comando | Campos | Efeito no desktop |
|---|---|---|
| `auth` | `token` | primeira frame obrigatória; responde `{cmd:"auth",ok,w,h}` |
| `move` | `dx, dy` (int, delta) | `MouseCtl.move_by` — relativo |
| `move_to` | `x, y` (float 0..1) | absoluto — **API morta**, ver [1.11](#111-limitações-conhecidas) #7 |
| `click` | `button, count` | `left`/`right`/`middle`, `count` clamp 1..4 |
| `press` / `release` | `button` | arrastar |
| `scroll` | `dx, dy` | roda (dy × 120) |
| `key` | `key` (nome) | mapa de teclas |
| `combo` | `mods, key` | modificador + tecla — **API morta** |
| `text` | `text` (string) | `keyboard.type` |
| `media` | `action` | play/pause/next/prev |
| `gesture` | `event, x, y, value` | caminho de gestos (câmara) |
| `ping` | — | keepalive de 15 s |

## 1.3 Ciclo de vida da ligação

```
connect() ──▶ new WebSocket(buildWsUrl(...))
                 │
                 ├─ onopen    ──▶ envia auth(token) → ready=true → arranca timers
                 ├─ onmessage ──▶ handleMessage()  ⚠️ só processa 'auth'; ignora pong
                 ├─ onerror   ──▶ setError()
                 └─ onclose   ──▶ ready=false, para timers, mostra erro
                                    ❌ NÃO reconecta. O utilizador tem de premir LIGAR.
```

**O que não existe** (verificado por pesquisa em `src/`, `App.tsx`):

- ❌ **auto-reconnect** — nenhuma ocorrência de `reconnect` / `backoff` / `retry`
- ❌ **AppState** — sem tratamento de background/foreground
- ❌ **verificação de pong** — o ping é enviado, a resposta é ignorada
- ❌ **fila de input** — `sendRaw` descarta em silêncio quando não está pronto

Consequências práticas:

1. Se o Wi-Fi cair a meio de uma sessão, **todo o input é perdido em silêncio** e o
   ecrã fica a fingir que está ligado até o TCP dar erro.
2. Se o sistema operativo matar o socket em background, ao voltar à frente a
   ligação está morta e o utilizador tem de a refazer à mão.
3. Texto escrito offline é **descartado sem aviso** — o buffer local mantém-se, e
   quando o utilizador volta a escrever, só o delta novo é enviado. O texto que
   "desapareceu" nunca chega ao PC.

## 1.4 Rato — do toque ao pixel (mobile)

### O movimento é relativo, em pixels crus do telemóvel

Este é o ponto mais importante do *feel*. A posição do toque **não** é normalizada
para a resolução do PC: o que viaja é o **delta em píxeis físicos do telemóvel**,
multiplicado por uma constante.

```ts
// src/components/RemoteScreen.tsx:166-183  (toque → delta)
const dx = cur.x - prev.x;              // px crus do telemóvel
const dy = cur.y - prev.y;
if (Math.abs(dx) > 2 || Math.abs(dy) > 2) ts.moved = true;
...
if (dx !== 0 || dy !== 0) remote.move(dx, dy);
```

```ts
// src/services/remoteClient.ts:110-114  (delta → wire)
move(dx: number, dy: number): void {
  if (!this.ready) return;
  this.pendingDx += Math.round(MOVE_GAIN * dx);   // MOVE_GAIN = 1.8
  this.pendingDy += Math.round(MOVE_GAIN * dy);
}
```

As dimensões do ecrã do PC (`w`, `h`) chegam na resposta de `auth` e são **apenas
apresentadas** ao utilizador (`RemoteScreen.tsx:270-274`) — nunca usadas para escalar.

⚠️ **Consequência:** o mesmo gesto físico produz movimentos diferentes conforme o
telemóvel. Um dispositivo de alta densidade parece demasiado rápido; um tablet de
baixa densidade demasiado lento. A sensibilidade é função da **hardware do telemóvel**,
não do PC nem da preferência do utilizador.

### Não há filtro nem aceleração no touchpad

O projecto **tem** os filtros certos — `OneEuroFilter` e `AccelCurve` em
`src/engine/filters.ts` — mas estão ligados **apenas ao caminho da câmara**
(`App.tsx:104,130,284-288,312-316`). O touchpad envia deltas crus.

Falta, no touchpad: deadzone, escala de resolução, curva de aceleração
(swipe rápido = cursor rápido), predição, e correcção de aspecto.

Os parâmetros `moveGain` / `filterMinCutoff` / `filterBeta` em `src/store/index.ts:24-27`
**não afectam o touchpad** — só a câmara e o `TouchController` nativo de arrastar.

### Gesto → comando

| Gesto | Condição | Comando |
|---|---|---|
| 1 dedo, toque rápido | `!moved && dur < 260 ms` | `gesture("tap", x, y)` normalizado 0..1 |
| 2 dedos, toque | — | `click("right")` |
| 3 dedos, toque | — | `click("middle")` |
| 1 dedo, manter 380 ms | sem mover | `press("left")` → `release("left")` ao levantar |
| 2 dedos, vertical | média de `dy` | `scroll(0, step)` |
| botão "Duplo" | — | `click("left", 2)` |

**Arrastar:** distingue-se de mover por **duração sem movimento**. `ts.moved` é
*sticky* — uma vez que o dedo passa dos 2 px, já não é possível iniciar arrasto
nesse mesmo gesto. Só o caminho "parado desde o início → arrastar" funciona.

⚠️ **Scroll só vertical, só com 2 dedos.** Não há scroll horizontal em lado nenhum,
nem zonas de scroll nas margens do ecrã, nem botão de scroll dedicado.

## 1.5 Rato — injecção no desktop

### Dois caminhos, ambos a contornar a aceleração do SO

| Comando | Caminho | Semântica |
|---|---|---|
| `move` | `MouseCtl.move_by` (`core/mouse_ctl.py:177-189`) | **relativo** (read-modify-write absoluto) |
| `move_to` | `mouse.position = (x, y)` (`core/remote.py:354-359`) | **absoluto** (`SetCursorPos`) |

Nenhum dos dois passa pela curva de aceleração do ponteiro do sistema — o
posicionamento é directo ao pixel. É o modelo correcto para um touchpad.

O acumulador fraccionário em `move_by` é um bom detalhe — impede que deltas
sub-pixel se percam:

```python
# core/mouse_ctl.py:177-189
def move_by(self, dx, dy):
    self._frac_x += dx
    self._frac_y += dy
    ix = int(self._frac_x)
    iy = int(self._frac_y)
    if not ix and not iy:
        return
    self._frac_x -= ix
    self._frac_y -= iy
    x, y = self.mouse.position
    nx = min(max(x + ix, 0), self.screen_w - 1)   # ⚠️ clamp 0..W-1 — ver #2
    ny = min(max(y + iy, 0), self.screen_h - 1)
    self.mouse.position = (int(nx), int(ny))
```

### Conversão normalizado → pixels

```python
# core/remote.py:354-359
def _move_to(self, data):
    x = min(max(self._float(data, "x", 0.0), 0.0), 1.0)
    y = min(max(self._float(data, "y", 0.0), 0.0), 1.0)
    w = max(getattr(self._mouse, "screen_w", 1920) - 1, 1)
    h = max(getattr(self._mouse, "screen_h", 1080) - 1, 1)
    self._mouse.mouse.position = (int(x * w), int(y * h))
```

`px = trunc(clamp(x,0,1) × (W − 1))`. Para 1920×1080: `0.5 → int(0.5×1919) = 959`.

Duas notas: usa `int()` (**truncamento, não arredondamento**) — viés sistemático de
até 1 px para o canto superior esquerdo. E a normalização acontece no **touchpad do
telemóvel** (`RemoteScreen.tsx:219-220`: `x = locationX / layoutRef.current.w`), não
no ecrã do PC — **sem correcção de aspecto**, pelo que mapear 9:19.5 num 16:9 produz
alongamento anisotrópico.

### 🟢 Bug crítico: multi-monitor sem origem — **corrigido a 2026-10-02**

`core/mouse_ctl.py:120-161` lia o **tamanho** do desktop virtual mas **nunca a origem**:

```python
# core/mouse_ctl.py:131-132
w = int(user32.GetSystemMetrics(78))  # SM_CXVIRTUALSCREEN
h = int(user32.GetSystemMetrics(79))  # SM_CYVIRTUALSCREEN
```

`SM_XVIRTUALSCREEN` (76) e `SM_YVIRTUALSCREEN` (77) **não apareciam em lado nenhum
do código** (verificado em `core/`, `ui/`, `main.py`). Entretanto o pynput posiciona
via `SetCursorPos`, que usa coordenadas de desktop virtual e **aceita valores
negativos**.

| Configuração | Origem virtual | Resultado (antes da correcção) |
|---|---|---|
| 2 monitores lado a lado, principal à esquerda | `(0, 0)` | ✅ correcto |
| Qualquer monitor **à esquerda ou acima** do principal | `(−W₂, 0)` | 🔴 faixa inalcançável; `move_by` encurrala o cursor no monitor principal |

É o bug clássico desta classe, e é exactamente o cenário de quem faz *trading* com
vários ecrãs.

**Correcção.** `MouseCtl` passou a ler também `SM_XVIRTUALSCREEN` (76) e
`SM_YVIRTUALSCREEN` (77), e a expor `screen_bounds()` — os limites reais,
`(screen_x, screen_y, screen_x + screen_w − 1, screen_y + screen_h − 1)`. `move_by`
passou a clampar contra isso em vez de `[0, screen_w−1]`, e o `move_to` do servidor
passou a somar a origem aoconverter de normalizado para píxeis. `screen_w`/`screen_h`
continuam a significar **tamanho**, porque `engine.py:555-556`, `main.py:551` e a
resposta de `auth` dependem disso.

⚠️ **O teste que enterrava o bug.** `tests/test_move_gesture.py` fixava o clamp
`[0, screen_w−1]` num ecrã sintético 2000×1200 sem qualquer noção de origem — e
`_ctl()` construía um `MouseCtl()` real, pelo que depois da correcção passou a herdar
a origem do ecrã de quem corre a suite. Passou a fixar `screen_x`/`screen_y` à mão, e
`tests/test_multi_monitor_origin.py` (17 testes) cobre a origem negativa nos dois
sentidos, para o mesmo bug não voltar a passar.

## 1.6 Teclado — do texto à tecla (mobile)

Não existe teclado customizado no ecrã. Usa-se o **teclado do sistema** via
`TextInput`, mais alguns botões de tecla especial.

O envio é por **diff** contra um buffer local:

```ts
// src/components/RemoteScreen.tsx:82-105
const onKbChange = useCallback((v: string) => {
  const prev = kbBufRef.current;
  kbBufRef.current = v;
  setKbText(v);
  if (!remote.isConnected) return;          // ⚠️ texto offline descartado em silêncio
  if (v.length < prev.length) {
    for (let i = prev.length - v.length; i > 0; i--) remote.key('backspace');
  } else if (v.length > prev.length) {
    const added = v.slice(prev.length);
    let batch = '';
    for (const ch of added) {              // code-point aware
      if (ch === '\n') { if (batch) { remote.text(batch); batch = ''; } remote.key('enter'); }
      else batch += ch;
    }
    if (batch) remote.text(batch);
  }
}, []);
```

Escrever "abc" envia **uma** mensagem `{"cmd":"text","text":"abc"}` — string crua, não
eventos por tecla.

✅ **Autocorrect está correctamente desligado** — `autoCorrect={false}`,
`autoCapitalize="none"`, `spellCheck={false}` (`RemoteScreen.tsx:287-291`). Sem
corrupção de texto.

### Teclas disponíveis na UI

`ESC · WIN · TAB · ENTER · backspace · ← ↑ ↓ → · SPACE` (`RemoteScreen.tsx:304-316`)

❌ **Faltam** Home, End, PageUp, PageDown. E a API `combo()` existe no cliente
(`remoteClient.ts:144-146`) mas **nenhum código de UI a chama** — não há Ctrl+C,
Ctrl+V, Alt+Tab, Win+D por botão.

### Bugs de teclado

1. **Double-Enter.** `onChangeText` com `\n` envia `key('enter')` (linha 95-96) **e**
   `onSubmitEditing` chama `onKbEnter`, que envia **outro** `key('enter')`
   (`RemoteScreen.tsx:113`). Premir Return no teclado do sistema produz dois Enters.
2. **Corrupção em edições não-append.** O índice do diff é `v.slice(prev.length)`.
   Editar no meio da string, colar por cima, ou um autocomplete que substitua texto
   envia **os caracteres errados** — sem backspaces de correcção. Só funciona para
   escrita puramente sequencial no fim.
3. **Backspace em caracteres compostos.** A contagem usa comprimento em code units.
   Apagar um emoji ou um carácter combinado dispara **dois** backspaces.
4. **Libertação de arrasto ao mudar o número de dedos.** `RemoteScreen.tsx:153-157`
   envia `release('left')` sempre que a contagem de dedos muda durante um gesto —
   pode cancelar um arrasto não relacionado.

## 1.7 Teclado — injecção no desktop

### Texto: caractere a caractere, sem clipboard

```python
# core/remote.py:484-491
def _type_text(self, text):
    if not text:
        return
    try:
        self.keyboard.type(text)
    except Exception:            # ⚠️ demasiado largo — ver abaixo
        for ch in text:
            self._tap_key(ch)
```

`pynput.keyboard.Controller.type` prime e solta cada carácter. **Sem clipboard, sem
paste** — decisão correcta: sequestrar o clipboard seria um problema de privacidade pior.

⚠️ O `except Exception` é largo demais. Se `type()` falhar depois de escrever 5 de
20 caracteres, o fallback **re-emite os 20 individualmente** → texto duplicado.
 Deveria ser `InvalidCharacterException`.

### Mapa de teclas — completo para o mercado-alvo

`core/remote.py:421-438` cobre: `ctrl` (l/r), `alt` (l/r), `shift` (l/r), `cmd`/`win`,
`tab`, `enter`/`return`, `esc`/`escape`, `space`, `delete`/`del`, `backspace`/`back`,
`home`, `end`, `pageup`/`pgup`, `pagedown`/`pgdn`, as 4 setas (ambas as grafias),
`f1`–`f12`, `caps`/`capslock`. Qualquer nome de 1 caractere cai para o literal
(`core/remote.py:442-451`).

⚠️ Existe um **segundo mapa duplicado** em `core/hotkeys.py:41-50` (caminho câmara/voz).
Deriva à espera de acontecer.

## 1.8 Acentos e Unicode

**Este é o ponto mais bem resolvido de todo o sistema, e é o crítico para Angola.**

Não existe nenhuma tabela de scancodes US-QWERTY fixa. E o pynput **não** faz um
mapeamento simples carácter→virtual-key. Em `.venv/…/pynput/keyboard/_win32.py:81-95`:

```python
res = VkKeyScan(self.char)           # VkKeyScanW — consciente do layout
if (res >> 8) & 0xFF == 0:           # byte de estado de shift == 0 → VK simples
    vk = res & 0xFF
    ...
else:
    vk = 0                           # ← fallback INDEPENDENTE do layout
    scan = ord(self.char)
    flags = KEYBDINPUT.UNICODE        #    KEYEVENTF_UNICODE
```

`VkKeyScanW` é consciente do layout, mas para `ã` num layout US devolve `−1`, pelo
que o byte de shift fica `0xFF ≠ 0` e o código **cai para `KEYEVENTF_UNICODE`**.

✅ **Consequência: o layout activo do PC é irrelevante.** `ã`, `ç`, `é`, `õ`, `Ê`
injectam correctamente com o desktop em US QWERTY, PT-PT ou PT-BR. Este é o
comportamento certo para o mercado-alvo, e foi **verificado por leitura do código da
biblioteca instalada**, não assumido.

No transporte: o `body` é `JSON.stringify`, logo UTF-8 preserva os caracteres; e a
iteração usa `for (const ch of added)`, consciente de code points.

**Três ressalvas honestas:**

1. **Sem composição por dead-key.** Não existe caminho `´` seguido de `e`. Na prática
   irrelevante, porque o teclado do telemóvel já produz o carácter composto.
2. **`KEYEVENTF_UNICODE` não é aceite universalmente.** Campos dependentes de IME,
   sessões RDP, prompts UAC, a UI de credenciais do Windows, e jogos que lêem input
   bruto vão ignorar ou distorcer. Um caminho por clipboard com `Ctrl+V` seria mais
   robusto para campos de texto.
3. ~~**Zero testes.**~~ **Parcialmente esbarrado a 2026-10-01:** o caminho do
   protocolo (`_type_text` é chamado, aceita texto vazio e não vazio) está coberto
   pelos testes de contrato, mas contra um **teclado falso**. A afirmação que importa
   para o mercado — que os caracteres acentuados chegam mesmo ao Windows —
   **continua sem um único teste**.

## 1.9 Segurança e modelo de ameaça actual

| Aspecto | Estado | Referência |
|---|---|---|
| TLS | ❌ **nenhum** | `core/remote.py:227-231` (sem `ssl=`) |
| URL deTLS no cliente | ❌ **impossível** — `wss://` é removido | `remoteClient.ts:36` |
| Token | 64 bits (`secrets.token_hex(8)`) | `core/remote.py:48-49` |
| Comparação do token | `==` em claro, não constante | `core/remote.py:250` |
| Rate limiting / lockout | ❌ **nenhum** — tentativas ilimitadas | — |
| Allowlist de IP | ❌ nenhuma | — |
| Limite de clientes | ❌ nenhum — `connected_count` é calculado e **nunca usado** | `core/remote.py:192` |
| Timeout de ociosidade | ❌ nenhum | — |
| Indicador de sessão activa | ❌ nenhum | — |
| Confirmação por acção destrutiva | ❌ nenhuma | — |
| Caminho remoto documentado | **port forwarding manual** do router | `RemoteScreen.tsx:406-409` |
| Logging de teclas | ✅ **limpo** | — |

⚠️ **Não existe ngrok.** A dependência `@expo/ngrok` no `package.json` é o túnel do
**Metro dev bundler** do Expo, não do remote. Não há código de tunnel em lado nenhum.
O remote pede ao utilizador que **encaminhe a porta 8765 manualmente no router** —
materialmente pior do que um túnel: sem TLS, sem obscuridade, sem rotação de URL.

### Bypass de pausa e de licença

Verificado por pesquisa em `core/remote.py`: **zero ocorrências** de `paused`.
`state["paused"]` é verificado por todos os caminhos de comando locais
(`core/commands.py:115,125,133`), mas **um telemóvel ligado mantém controlo
total enquanto a app está "pausada"**. E `cfg.remote_enabled` não é subjecto a
`is_pro_locked` (`main.py:247-259`). Este achado (#8) continua aberto.

~~🔴 **Bypass de monetização:** o touchpad e o teclado remotos **não** estão atrás do
gate Pro. Só o encaminhamento por gestos de câmara está (`App.tsx:153`). Um utilizador
Free obtém rato + teclado remotos completos, grátis.~~ **Corrigido a 2026-10-02:**
o `auth` do `core/remote.py` passou a exigir, além do token, uma lease ES256
assinada de tier pago, verificada com a chave pública embebida — sem ela a ligação
é recusada com `pro_required` e nenhum comando é despachado. `remote_enabled`
continua a arrancar o servidor para todos — é o que permite a um Pro já comprado
ligar, e o que dá a um Free o `pro_required` caso contorne a UI.

**Complemento a 2026-10-02** (`b2abad0`): o bypass também está fechado do lado do
cliente. O `RemoteScreen` mostra o `ProGate` (`feature="remote"`) em vez do
formulário de ligação, por isso um Free já não precisa de tentar para descobrir que
não comprou. A defence passa a ser dupla — o paywall evita a tentativa, o `auth`
recusa-a na mesma se chegar lá. O `entitlement` é passado por prop a partir de
`App.tsx`, e não por um segundo `useProEntitlement()`: o hook chama `useIAP()` e
`hydrate()` no mount, logo uma segunda instância duplicava os listeners de compra.

### Dois pontos positivos

- ✅ **Sem logging de teclas.** Só se regista o endereço de ligação
  (`core/remote.py:258`), um prefixo de 4 caracteres do token no arranque
  (`core/remote.py:238`), e o *nome* do comando em falha (`core/remote.py:277`).
  `_type_text` não regista nada. **Nenhum `Listener` de teclado do pynput é
  instanciado** (verificado: zero `on_press` / `Listener(` em `core/` e `main.py`).
- ✅ **Token de entropia adequada** — 64 bits de `secrets`.

## 1.10 Cobertura de testes

### Mobile: `src/__tests__/remoteClient.test.ts` (18 testes)

🟢 **Corrigido a 2026-10-01.** A auditoria encontrou zero cobertura; hoje há `jest-expo`
configurado, `test` script no `package.json` e 18 testes do `RemoteClient`:
`buildWsUrl` (host, porta, omissões, esquemas, limpeza, token fora do URL, `wss`→`ws`),
`auth` como primeira mensagem, comandos bloqueados antes de `auth.ok`, token recusado e
ausente, dimensões inválidas, JSON inválido e fechos.

### Contrato dos dois lados: `tests/test_remote_protocol_contract.py` (28 testes)

🟢 **Novo a 2026-10-01.** Os dois directórios nunca são compilados juntos, por isso
jogar só do lado TS deixaria passar uma renomeação de comando no PC. Estes testes
prendem o contrato **no lado do servidor**, sem toolchain TS: os 11 comandos que o
`remoteClient.ts` manda são aceites, as formas das respostas (`{cmd,ok,w,h}`,
`{ok,note}`, `bad_command`, `auth_required`) são as que o parser do TS consome,
`auth`/`ping` são inline e não passam por `_handle`, e um comando antes do `auth` é
recusado sem mover o rato um píxel. A simetria é testada nos dois sentidos — um
comando novo no PC que o app não manda também falha.

### Desktop: `tests/test_remote.py` existe, mas é fino

| Teste | O que realmente afirma |
|---|---|
| `test_dispatch_move_to_clamps` | Aritmética contra `FakeMouse` (`screen_w=1920`). **Não modela origem** — continua cego ao multi-monitor, mas deixou de ser o único: `tests/test_multi_monitor_origin.py` fixa a origem negativa nos dois sentidos. A 2026-10-02 `_ctl()` em `tests/test_move_gesture.py` passou a fixar `screen_x/screen_y` à mão, porque `MouseCtl()` lê a origem real da máquina e o teste dependeria do setup de ecrã de quem o corre. |
| `test_auth_and_commands_over_websocket` | Servidor real em `127.0.0.1:0`. ⚠️ **A asserção de bad-auth é um no-op** — está dentro de `try/except Exception: pass` (linhas 167-169), portanto um cliente que nem consiga ligar-se passa. **Esbarrado a 2026-10-01:** `test_resposta_de_auth_falhado_tem_error_auth_required` e `test_comando_antes_do_auth_nunca_parte` em `tests/test_remote_protocol_contract.py` afirmam o auth falhado sem `try/except`. |
| `test_generate_token_is_unique` | Não-vazio, `len >= 8`, distinto. **Não** afirma a força real de 64 bits. |
| `test_key_aliases_arrow_keys` | Único teste que toca pynput real. |
| `test_dispatch_move_click_scroll_press` | Despacho contra `FakeMouse`. |

**Continua por testar:** injecção de texto contra o teclado real, **caracteres
acentuados** de facto, replay, e clientes concorrentes. As duas excepções saíram
da lista a 2026-10-02: a simetria de arrasto quando o socket cai a meio
(achado #10) e as coordenadas multi-monitor (achado #2) têm agora
`tests/test_remote_drag_release.py` e `tests/test_multi_monitor_origin.py`. Nota: os
testes de contrato exercitam `_type_text`, `_combo`, `_tap_key`, media keys e a
tabela de gestos, mas contra um teclado **falso** — provam que o comando é aceite e
despachado, não que o evento chega ao Windows.

⚠️ **A CI não executa o caminho crítico.** `.github/workflows/ci.yml` corre
`QT_QPA_PLATFORM=offscreen xvfb-run -a pytest tests -q` em Linux. Como
`sendinput_available()` devolve `False` em Linux (`core/mouse_ctl.py:69-75`), **todo
o fast path `SendInput` do Windows nunca corre na CI** — só o fallback do pynput.
Isto continua aberto e é uma limitação de plataforma do runner, não um bug.

~~🔴 **Os testes do mobile não corriam na CI.**~~ **Corrigido a 2026-10-02**
(`2ef9045`): o job `mobile` fazia `typecheck` e `expo config`, e nada mais. O script
`test` existia no `package.json` e passava 21/21 localmente, mas **nenhum workflow o
invocava** — nem a `ci.yml` nem a `build-android.yml`, e não há husky. Isto tornava
enganosa a linha do achado #12 ("18 testes Jest"): os testes existiam e protegiam o
contrato de `auth`, mas nada os corria no GitHub, e portanto o `pro_required` não
tinha garantia automática nenhuma. Passou a haver um passo `Test (mobile)` com
`npm test -- --ci`.

Isto é distinto da limitação acima e mais grave: aqui não é o runner não exercitar um
caminho, era o próprio guard não correr. Corrigido sem depender de hardware — os testes
são unitários e só importam `remoteClient`.

## 1.11 Limitações conhecidas

Consolidadas e verificadas no repositório em 2026-09-28.

| # | Gravidade | Limitação | Evidência |
|---|---|---|---|
| 0 | 🔴 Crítico | **`cryptography` em falta nos manifestos** — importado por `core/licensing.py` ao nível do módulo, e `main.py:35` importa esse módulo. O `setup.bat` produzia um ambiente onde a aplicação **não arrancava**. Provado por resolução limpa (59 pacotes, `cryptography` ausente, nada o traz transitivamente). **Corrigido** 2026-09-28. | `requirements.txt`, `core/licensing.py:9-10`, `main.py:35` |
| 1 | ⚪ **Falso positivo** | ~~`websockets>=13.0` é um floor inválido; `websockets.asyncio.server` só existe a partir da 14.0.~~ **Falso.** O namespace `websockets.asyncio` foi introduzido na **13.0** (changelog 13.0: *"introduces a new asyncio implementation"*); a 14.0 foi apenas o que o tornou default. `websockets/asyncio/server.py` existe na tag `13.0` do upstream, com a API `serve` completa. O floor declarado está **correcto**. Ver §1.14.1. | `requirements.txt:5`, `core/remote.py:223` |
| 2 | 🟢 **Resolvido** | ~~**Multi-monitor sem origem** — cursor encurralado no monitor principal se algum ecrã estiver à esquerda/acima.~~ **Corrigido a 2026-10-02:** `_screen_size` lia a largura e a altura do desktop virtual mas descartava a origem (`SM_XVIRTUALSCREEN`/`SM_YVIRTUALSCREEN`, métricas 76/77), logo o clamp de `move_by` assumia que o ecrã começava em 0 e atirava metade do desktop para a origem; `move_to` convertia normalizado→píxeis sem a mesma origem. Passa a existir `MouseCtl.screen_bounds()`, usada pelos dois caminhos, com 17 testes em `tests/test_multi_monitor_origin.py` — 8 deles falham sem a correcção. Ver §1.5. | `core/mouse_ctl.py`, `core/remote.py`, `tests/test_multi_monitor_origin.py` |
| 3 | 🔴 Crítico | **Sem TLS**, e o cliente impede usar `wss://`. | `core/remote.py:227-231`, `remoteClient.ts:36` |
| 4 | 🔴 Crítico | **Sem rate limit / lockout / allowlist** numa porta aberta à Internet. | `core/remote.py:250` |
| 5 | 🟢 **Resolvido** | ~~**Bypass do gate Pro** — rato e teclado remotos são grátis.~~ **Corrigido a 2026-10-02:** o `auth` do `RemoteServer` exigia apenas o token de emparelhamento, que é o mesmo para toda a gente — qualquer telemóvel na mesma rede mexia no rato e no teclado sem comprar. O `token` foi mantido (é o segredo de emparelhamento) e passou a exigir-se também a `lease` que o license-server emite para o telemóvel: o PC valida a assinatura ES256 com a chave pública embebida (`core/licensing.py::verify_remote_entitlement`), aceita só os tiers pagos e recusa a ligação com `pro_required` se a lease faltar, estiver expirada ou for de tier inválido. 6 testes novos em `tests/test_remote_protocol_contract.py` (todos falham sem a correcção) e 3 no Jest do cliente remoto. | `core/remote.py`, `core/licensing.py`, `tests/test_remote_protocol_contract.py`, `mobile/maouse-mobile/src/services/remoteClient.ts` |
| 6 | 🟠 Alto | **Condição de corrida no `MouseCtl` partilhado** — thread asyncio remota e thread Qt/escala mutam `_frac_x/_frac_y` e `mouse.position` sem lock. | `main.py:310-313` |
| 7 | ⚪ **Sem impacto** | **`pyproject.toml` não declarava as dependências** — só `cryptography>=42`, e não empacotava `config.py`/`i18n.py`. Premissa errada: o projecto não é distribuído por pip (`git grep "pip install \."` vazio; o produto sai por PyInstaller e as dependências vêm do `setup.bat` → `requirements.txt`). As secções mortas foram apagadas a 2026-09-28. Ver [§1.14.3](#1143-o-pyprojecttoml-não-era-o-problema--e-a-primeira-correcção-estava-errada). | `pyproject.toml:1-44` (removido) |
| 8 | 🟠 Alto | **Bypass do toggle de pausa** — controlo total com a app "pausada". | ausência em `remote.py` |
| 9 | 🟠 Alto | **`_combo` bloqueia o event loop** 40 ms com `time.sleep`. | `core/remote.py:475` |
| 10 | 🟢 **Resolvido** | ~~**`press`/`release` sem estado de arrasto** — sem `finally` de limpeza, um socket que cai a meio de um arrasto deixa o botão logicamente premido.~~ **Corrigido a 2026-10-02:** `press` não guardava estado nenhum e o gesto `left_down` punha `_drag` a `True` sem nada a limpar — o `_combo` já fazia esta limpieza para as teclas, os botões é que ficaram de fora. Agora os dois caminhos passam por um registo único (`_held`, canonicalizado para `lmb` e `left` serem o mesmo botão) e o `finally` de `_on_connect` solta o que ficou premido. 14 testes em `tests/test_remote_drag_release.py`, 6 dos quais falham sem a correcção. | `core/remote.py`, `tests/test_remote_drag_release.py` |
| 11 | 🟠 Alto | **Sem auto-reconnect, sem AppState, sem fila.** Input perdido em silêncio. | `src/services/remoteClient.ts` |
| 12 | 🟢 **Resolvido** | ~~**Zero testes no mobile**; suite desktop não cobre auth nem texto.~~ **Corrigido a 2026-10-01:** 18 testes Jest em `mobile/maouse-mobile/src/__tests__/remoteClient.test.ts` e 28 testes de contrato em `tests/test_remote_protocol_contract.py`, que cobrem o handshake, a rejeição de auth, o texto e a simetria dos 11 comandos. Ver §1.10. | `src/__tests__/remoteClient.test.ts`, `tests/test_remote_protocol_contract.py` |
| 13 | 🟡 Médio | **Double-Enter** no teclado. | `RemoteScreen.tsx:95-96,113` |
| 14 | 🟡 Médio | **Corrupção em edições não-append** (diff por índice). | `RemoteScreen.tsx:91` |
| 15 | 🟡 Médio | **Sem filtro, aceleração ou escala no touchpad** — sensação dependente do telemóvel. | `remoteClient.ts:31` |
| 16 | 🟡 Médio | **Sem correcção de aspecto** ecrã do PC / touchpad. | `RemoteScreen.tsx:219-220` |
| 17 | 🟡 Médio | **Scroll só vertical**, sem zonas de margem. | `RemoteScreen.tsx:185-203` |
| 18 | 🟡 Médio | **`except Exception` largo** em `_type_text` pode duplicar texto. | `core/remote.py:489` |
| 19 | 🟡 Médio | **API mortas** `moveTo` e `combo` — o protocolo promete mais do que a app entrega. | `remoteClient.ts:116,144` |
| 20 | 🟡 Médio | **Um teste afirma o bug multi-monitor como correcto.** | `tests/test_move_gesture.py:176-201` |
| 21 | 🟡 Médio | **Caminho remoto = port forwarding manual**, não um túnel. | `RemoteScreen.tsx:406-409` |
| 22 | ⚪ Baixo | **Duplicação de mapa de teclas** entre `remote.py` e `hotkeys.py`. | `core/hotkeys.py:41-50` |
| 23 | ⚪ Baixo | **Sem macOS** — nenhum ramo `_IS_DARWIN`. | `core/mouse_ctl.py:20` |
| 24 | ⚪ Baixo | `requirements.txt` traz `uiautomation`/`comtypes` (só Windows) no manifesto partilhado. | `requirements.txt:12-13` |

## 1.12 Mapa de ficheiros

| Ficheiro | Papel |
|---|---|
| `core/remote.py` | Servidor asyncio, auth, dispatch, injecção de teclado/rato, token |
| `core/discovery.py` | Anúncio mDNS `_maouse._tcp` — **ver §1.15** |
| `core/mouse_ctl.py` | Escrita no rato, métricas de ecrã virtual, clamp, `SendInput` |
| `core/hotkeys.py` | Mapa de teclas **duplicado** (caminho câmara/voz) |
| `ui/settings_dlg.py` | Bind, porto, token na UI |
| `config.py` | `remote_enabled`, `remote_bind`, `remote_port`, `remote_token` |
| `main.py` | Cria o `MouseCtl` partilhado e arranca o `RemoteServer` |
| `tests/test_remote.py` | Protocolo (cobertura fina) |
| `tests/test_move_gesture.py` | `move_by` — **fixa o bug multi-monitor** |
| `mobile/…/remoteClient.ts` | Transporte, acumulador, ping, envio |
| `mobile/…/RemoteScreen.tsx` | Touchpad, scroll, toques, arrasto, teclado, UI |
| `mobile/…/store/remote.ts` | Estado React da ligação |
| `mobile/…/engine/filters.ts` | One-Euro + AccelCurve — **só caminho da câmara** |

## 1.13 Referência de configuração

| Chave | Default | Efeito |
|---|---|---|
| `remote_enabled` | — | liga/desliga o servidor |
| `remote_bind` | `0.0.0.0` | interface de escuta |
| `remote_port` | `8765` | porto TCP (1024–65535) |
| `remote_token` | gerado, 64 bits | auth de primeira frame |
| `remote_discovery` | `true` | anuncia o PC por mDNS (ver §1.15) |

| Constante (mobile) | Valor | Ficheiro |
|---|---|---|
| `MOVE_GAIN` | `1.8` | `remoteClient.ts:31` |
| `MOVE_INTERVAL_MS` | `24` | `remoteClient.ts:30` |
| `PING_INTERVAL_MS` | `15000` | `remoteClient.ts:29` |
| `DRAG_HOLD_MS` | `380` | `RemoteScreen.tsx:37` |
| limiar de toque | `260 ms` / `2 px` | `RemoteScreen.tsx` |

## 1.14 Verificação desta auditoria

Todas as afirmações **estruturais** deste documento foram confirmadas directamente
no repositório antes da redacção. Verificações explícitas:

| Afirmação | Verificação | Resultado |
|---|---|---|
| `websockets>=13.0` no manifesto | `requirements.txt` | ✅ a string está lá — **mas ver §1.14.1: o floor está correcto** |
| `pyproject.toml` incompleto | `pyproject.toml:10-12` | ⚪ **Sem impacto.** Dizia `cryptography>=42` e mais nada — mas o `setup.bat` instala o `requirements.txt`, que era o que estava errado. Ver §1.14.3 |
| `SM_XVIRTUALSCREEN` ausente | pesquisa 76/77 em `core/`, `ui/`, `main.py` | ✅ só 78/79 presentes |
| Sem TLS no servidor | pesquisa `ssl`/`wss` em `core/remote.py` | ✅ zero ocorrências |
| `serve()` sem `ssl=` | `core/remote.py:227-231` | ✅ confirmado |
| Bypass de pausa/licença | pesquisa `paused|licens|is_pro` em `core/remote.py` | ✅ zero ocorrências |
| `connected_count` não usado | pesquisa em `core/`, `ui/` | ✅ só a definição, `remote.py:192` |
| Acentos via `KEYEVENTF_UNICODE` | leitura de `pynput/keyboard/_win32.py:81-95` | ✅ fallback confirmado |
| `wss://` removido no cliente | `remoteClient.ts:33-41` | ✅ confirmado |
| Sem reconnect/AppState | pesquisa `reconnect|backoff|AppState|retry` em `src/`, `App.tsx` | ✅ zero ocorrências |
| Double-Enter | `RemoteScreen.tsx:283-284,113` | ✅ `onChangeText` + `onSubmitEditing` |
| Clamp multi-monitor | `core/mouse_ctl.py:177-189` | ✅ clamp a `[0, W−1]` |
| `except Exception` largo | `core/remote.py:484-491` | ✅ confirmado |
| `_combo` bloqueante | `core/remote.py:475` | ✅ `time.sleep(0.04)` |

⚠️ **O que não foi verificado:** comportamento em hardware. Nenhuma das afirmações
foi confirmada com um rato ou teclado físicos, e nenhuma foi medida em latência
real. As_secções [1.4](#14-rato--do-toque-ao-pixel-mobile) e
[1.6](#16-teclado--do-texto-à-tecla-mobile) descrevem a *lógica implementada*, que pode
divergir do comportamento percebido. A Onda 0 da Parte 3 existe precisamente para
fechar esta lacuna.

## 1.14.1 Correção: o item 1 era um falso positivo 🔴

A limitação **#1** desta auditoria foi retractada a 2026-09-28. Afirmava que
`websockets>=13.0` era um floor inválido porque `websockets.asyncio.server` "só
existe a partir da 14.0", e classificava-a 🔴 Crítico por "rebenta[r] instalações
limpas da EAS". **As duas afirmações são falsas.**

**Erro 1 — o namespace existe desde a 13.0, não desde a 14.0.**

| Fonte | O que diz |
|---|---|
| Changelog upstream, secção 13.0 (20/Ago/2024) | *"websockets 13.0 introduces a new `asyncio` implementation"* |
| Changelog upstream, secção 14.0 (9/Nov/2024) | *"The new `asyncio` implementation is now the **default**"* — mudou o default, não criou o namespace |
| `websockets/asyncio/server.py` na tag `13.0` do GitHub | existe, com `serve`, `Server`, `ServerConnection`, `broadcast` |

O que a 14.0 fez foi passar a ser o default — uma mudança de *aliases*, não de
disponibilidade. `core/remote.py:223` importa o caminho explícito
`websockets.asyncio.server`, que é precisamente a forma que **não** depende do
default. O floor declarado está correcto tal como está.

**Erro 2 — a EAS nunca instala este manifesto.**

`requirements.txt` é o manifesto do **desktop em Python**. Os seus únicos
consumidores no repositório são `.github/workflows/ci.yml:18` e `setup.bat:12`.
Verificado: `mobile/` não contém nenhuma referência a `requirements.txt`, `pip`,
`expo-build-hook` ou `buildHook`; o `eas.json` só define perfis de build, sem
hooks; e o `mobile/maouse-mobile/package.json` não tem dependências Python
nenhuma. A EAS compila React Native com npm — o `pip` do Python nunca entra.

**Como o erro entrou.** A linha 605 da tabela de verificação confirmava que a
string `websockets>=13.0` estava no ficheiro — e a limitação saltou daí para "logo,
este floor é inválido". Verificou-se o *token* e assumiu-se a *consequência*. É o
erro clássico de leitura de manifesto, e vale como regra para o resto do
documento: **ler a linha do ficheiro não é verificar a consequência.**

**O que a investigação encontrou a seguir.** Fui ver o item #7 (`pyproject.toml`
declara só `cryptography>=42`) e acabei por comparar os manifestos com os
imports do código — e encontrei um 🔴 que era **real** e pior do que o falso
positivo. Detalhe em [§1.14.2](#1142-encontrado-enquanto-se-verificava-o-falso-positivo-um-bug-real-mais-grave).

**Consequência para o registo de contribuição.** O `CONTRIBUICAO_SOCIOS.md`
atribuía ao domínio do sócio 2 bloqueadores 🔴 de build com base nesta premissa.
Reverificado: o número real de bloqueadores de build do *domínio* é **zero** —
o `cryptography` em falta é um bug de dependências, não um bug do Canal
remoto, e estava lá antes de o sócio tocar no projecto. Ver §4.6 desse documento.

## 1.14.2 Encontrado enquanto se verificava o falso positivo: um bug real, mais grave 🔴

Ao verificar o item #1, fui verificar o #7, e ao verificar o #7 comparei os três
manifestos com os imports reais do código. Aí apareceu isto, que é o **oposto**
do item #1: aqui a auditoria tinha razão quanto ao sintoma, e a gravidade
estava *sub*avaliada.

**O bug.** `cryptography` é importado por `core/licensing.py` — a verificação de
licença, ou seja, o gate Pro do produto — mas **não estava em `requirements.txt`
nem em `requirements-linux.txt`**. O `setup.bat` instala exactamente o
`requirements.txt`.

**Prova, não inferência.** Resolvi o manifesto antigo num fluxo limpo:

```
pip install --dry-run --ignore-installed --report ... -r <requirements.txt antigo>
-> 59 pacotes resolvidos
-> cryptography no fluxo? False
```

Nada o traz transitivamente. Confirmado o outro lado: `main.py:35` e
`core/engine.py:26` fazem `from core.licensing import ...` **ao nível do
módulo**, não dentro de uma função. Logo, numa instalação limpa feita pelo
`setup.bat`, a aplicação **não arrancava** — `ModuleNotFoundError` no primeiro
`import` do entry point. Não é o gate Pro a falhar; é o produto a não arrancar.

**Porque ninguém notou.** O `.venv` de desenvolvimento tem a dependência
instalada, e o CI também — mas **por outro caminho**: `ci.yml` instala
`license-server/requirements.txt`, que a declara. Um manifesto errado e um
pipeline verde ao mesmo tempo: a dependência chegava por uma porta das traseiras
que ninguém mapeou. Todo o mundo desenvolve e testa num ambiente onde o bug não
existe, que é a forma mais eficaz de um bug de instalação sobreviver.

**O outro achado, menor.** `comtypes>=1.4` estava em `requirements.txt` sem ser
importado por lado nenhum. É dependência transitiva do `uiautomation` — que
declara `requires_dist: ['comtypes>=1.2.1']` — e declará-la directamente é o que
transforma um floor legítimo num floor de gueto. Removida.

### 1.14.3 O `pyproject.toml` não era o problema — e a primeira correcção estava errada

Escrevi na primeira versão desta secção que o `pyproject.toml` era um problema
em aberto e que a correcção era "dar-lhe as 15 dependências". **Estava errado, e
a premissa estava errada antes da conclusão.**

O projecto **não é distribuído por pip**. Verificado:

- `git grep "pip install \."` não devolve nada em lado nenhum do repositório.
- O produto é entregue por **PyInstaller** (`build.bat` + `maouse.spec`, onedir).
- As dependências são instaladas pelo `setup.bat`, a partir de `requirements.txt`.
- Não existe `pytest.ini`, `setup.cfg` nem `tox.ini`: o `pyproject.toml`
  vive, mas por outro motivo — é a configuração do **pytest**, do **ruff** e do
  **mypy**. Apagá-lo partia a toolchain toda.

E o `name = "maouse"` mentia sobre o produto, que se chama Maouse. A string
estava no ficheiro desde o commit que o criou e nunca foi revista.

**Porque isto importa mais do que o `cryptography`.** Ao "corrigir" o
`pyproject.toml` criei a **segunda lista de dependências** do projecto — e foi
exactamente esse o mecanismo que escondeu o bug. Um teste que compara duas
listas entre si só prova que as duas estão iguais; não prova que *qualquer* uma
estéja certa. O `pyproject.toml` podia declarar `cryptography` durante meses
e o `requirements.txt` — o ficheiro que o `setup.bat` usa — dizer outra
coisa, com o produto a não arrancar e o CI verde.

**O que está feito.** As três secções mortas (`[build-system]`, `[project]`,
`[tool.setuptools]`) foram **apagadas**. O `pyproject.toml` ficou só com a
configuração de pytest/ruff/mypy, que é o trabalho real dele aqui.
`requirements.txt` e `requirements-linux.txt` são a **única** fonte de
verdade, e `tests/test_manifests.py` (7 testes) compara-os com os `import`
que o código faz de facto — `tools/check_deps.py` extrai-os com `ast` —
falhando nos dois sentidos: dependência em falta (teria apanhado o
`cryptography`) e dependência que nada usa (apanha o `comtypes`).

**Os 5 testes que a primeira versão tinha e que foram cortados** — 5 em 12 — não
mediam nada, porque mediam uma coisa que não existe: `pyproject` a declarar
dependências, `py-modules` a empacotar `config.py`/`i18n.py` num pacote
que ninguém constrói. Um teste que impõe uma ficção é pior do que nenhum teste:
faz a configuração morta parecer necessária, e a próxima pessoa que a apanhar
não tem como saber que é inerte. **Cortar foi a correcção, não a escrita.**

---

## 1.15 Descoberta automática do PC (mDNS)

`core/discovery.py` anuncia o PC na rede local como `_maouse._tcp`, com a porta
do `RemoteServer` num TXT próprio. O telefone passa a encontrar o PC **sem
escrever o IP à mão** — que era o passo onde a esmagadora maioria dos
utilizadores desistia, e o passo que nenhuma das ondas acima resolvia.

### O que é anunciado

| Chave | Valor | Porquê |
|---|---|---|
| TXT `v` | `1` | versão do esquema, para o cliente ignorar PCs a anunciar diferente |
| TXT `id` | id estável do PC | distinguir dois PCs com o mesmo nome de máquina |
| Porta | `remote_port` | onde ligar |

**O token não vai nos TXT.** A sessão continua a autenticar com
`remote_token` na primeira frame, como sempre. Um TXT é lido por *qualquer*
dispositivo na LAN, incluindo o guest Wi-Fi do café e a rede da empresa; a
única coisa que o torna aceitável é **não ser segredo nenhum**. Os TXT são uma
allowlist fechada — só `v` e `id` saem, o que evita o modo de falha de um
`ServiceInfo` onde o token acabava numa linha de log do sistema operativo.
`test_token_nunca_vai_nos_txt` existe para segurar essa porta.

### O `id` tem de ser estável entre arranques

`uuid.getnode()` **não serve**, e era o que se usava. Nesta máquina devolve
`5b:95:ac:79:2c:49`, que não é o MAC de nenhuma interface (`enp7s0` é
`70:5a:…`, `wlp13s0` é `30:f7:…`) e tem o bit multicast ligado — que por
RFC 4122 §4.5 é o sinal de "endereço pseudo-aleatório, não um IEEE address".
Só parece estável porque o módulo `uuid` o memoriza **no processo**.

Um `id` que muda a cada arranque faz o telefone tratar o mesmo PC como um PC
novo, todas as vezes. O id é hoje o `uuid.getnode()` **se e só se** o bit
multicast estiver desligado; caso contrário vai para
`%LOCALAPPDATA%\Maouse\device_id` e é relido daí. Ficheiro à parte, e não
dentro de `settings.json`, para sobreviver a um `settings.json` apagado.

### Três coisas que têm de estar certas fora do código

O anúncio **não funciona** sem cada uma destas, e nenhuma delas dá erro quando
falha — que é o que torna esta funcionalidade silenciosamente inútil quando o
`main.py` está certo:

1. **UDP 5353 aberta.** O `installer.iss` cria a regra de firewall na
   instalação; o `conectar.bat` também, para desenvolvimento. A regra é
   `dir=in` na 5353 porque o `zeroconf` **responde** de lá.
2. **O `zeroconf` no `.exe`.** O `maouse.spec` faz `collect_all("zeroconf")`:
   são módulos de extensão compilados (`_cache`, `_dns`, `_history`,
   `_listener`) que a análise estática não segue. Sem isto, `import zeroconf`
   funciona e é o anúncio que falha.
3. **O `zeroconf` presente no ambiente.** É uma dependência opcional a sério: o
   import é tardio, e sem ele a aplicação **arranca na mesma** e diz que não
   tem o que anunciar. Um `ImportError` no arranque seria repetir, ao
   contrário, o bug do `cryptography` (§1.14.2).

### O telefone descobre o PC — `MdnsDiscoveryModule.kt`

O `NsdManager` do Android é o `zeroconf` do telefone. Fica no mesmo plugin dos
outros módulos nativos, e não é um pacote de terceiros a resolver versões.

O `NsdManager` tem três comportamentos que só se descobrem a correr, e cada um
deles dá uma falha que não se parece com a causa:

1. **O `serviceName` chega a ser só o rótulo.** O PC publica
   `Maouse 1._maouse._tcp.local.` e o Android entrega `Maouse 1`. Ligar
   directamente dá `UnknownHostException`, por isso o nome é normalizado.
2. **A resolução é assíncrona e tem de ser pedida.** `onServiceFound` traz os
   metadados anunciados; o endereço só chega depois de `resolveService`. Pedir
   o IP no `onServiceFound` dá `null` — e um `null` que se parece com "o PC
   está noutra sub-rede".
3. **O `NsdManager` precisa do WiFi ligado, mesmo com o PC em Ethernet.**
   `CHANGE_WIFI_MULTICAST_STATE` sem a qual o Android não entra em multicast, e
   o multicast é o mDNS inteiro. Sem esta permissão funciona no emulador e
   falha num telefone. É por isso que o módulo avisa **antes** de arrancar se o
   WiFi do telefone está desligado: uma lista vazia sem explicação é
   indistinguível de um PC desligado.

### Não verificado

O `NsdManager` **não foi corrido num aparelho**: não há Android disponível
nesta máquina. O que está verificado é a lógica do PC
(`tests/test_discovery.py`, 38 testes, com `Zeroconf` trocado por um duplo), a
tipagem do lado do telemóvel (`npm run typecheck`) e o `AndroidManifest`
gerado (permissões correctas e sem duplicados em `prebuild` repetido). O
empacotamento Windows continua por verificar: o `installer.iss` e o
`maouse.spec` são lidos, não executados.

---

## 1.16 Controlo remoto por Bluetooth (BLE)

> **Só funciona em Linux.** O PC publica-se como peripheral GATT falando com o
> `bluetoothd` pela **D-Bus de sistema**, que é o que o BlueZ expõe. O Windows
> não tem BlueZ nem D-Bus de sistema, e o macOS tem um stack BLE próprio que
> esta secção não usa. Nas definições, a checkbox aparece desliga noutro
> sistema e diz porquê. Para o telefone encontrar o PC no Windows, use o
> mDNS (§1.15).

Um segundo transporte para o **mesmo rato**. O telefone controla o PC sem rede
nenhuma — a via que funciona numa rede de empresa onde o multicast está
bloqueado, ou com o telemóvel em dados móveis e o PC em Ethernet, que é
justamente onde o mDNS (§1.15) não funciona.

### Um peripheral, não um servidor

O PC é o **peripheral** GATT e o telefone é o **central**. É o inverso do
WebSocket: em vez de o PC abrir uma porta à espera de alguém, publica-se como
um serviço BLE que o telefone procura e a quem se liga.

| | | |
|---|---|---|
| Serviço | `D9905F51-F497-49A4-88DF-784D82249EFD` | o que o telefone filtra nos anúncios |
| RX | `4C7F582E-BD6F-40ED-B181-AE537DD154ED` | escrita: comandos do telefone |
| TX | `64DB3D43-0354-4142-8EBE-EDE62429DD8A` | notificação: `ok`/`err`/`pong` |

O `GattManager1` vive no **adaptador** (`/org/bluez/hci0`), não em
`/org/bluez` — e é a primeira coisa que se erra, porque `/org/bluez` é onde
`ObjectManager` responde.

**Um só caminho de comandos.** `RemoteBLE` não implementa um servidor de
comandos: entrega cada mensagem ao `RemoteServer._handle`, o mesmo que
trata o WebSocket. Uma segunda implementação seria duas listas de comandos a
divergirem, e o texto passava a funcionar e o `media` não.

### `Flags` é um array de strings, não uma bitfield

Este foi o bug que custou a sessão, e vale registá-lo porque **nenhum teste o
apanhou**.

`org.bluez.GattCharacteristic1.Flags` é declarado como `q` na documentação
encontrada online, e é isso que qualquer um escreve primeiro. O BlueZ real
espera um **array de strings** (`as`): `parse_flags()` faz

```c
if (dbus_message_iter_get_arg_type(&iter) != DBUS_TYPE_ARRAY)
    return false;
```

e o `chrc_create()` que a chama acaba em `app->failed = true`. O
`RegisterApplication` responde então:

```
org.bluez.Error.Failed: No valid service object found
```

que **fala do serviço** quando o problema é a **característica**. Três causas
distintas — nenhum proxy recebido, `Service` que não é um caminho de objecto,
`Flags` com o tipo errado — e a mesma mensagem.

Como achar a causa sem o log do daemon (que é root, e aqui não há): teste
diferencial contra o próprio `bluetoothd`, subindo cada vez mais fundo na
cascata.

| Exportado | Resultado |
|---|---|
| nada | `No object received` |
| só o serviço | **REGISTOU** |
| serviço + 1 característica | `No valid service object found` |

Só o serviço a registar isola a falha no `chrc_create()`. A partir daí é ler
`parse_flags()` e comparar com o que o `dbus-next` produz.

`TestContratoGattDbus` existe para isto não voltar: verifica a **assinatura
D-Bus** que o daemon lê, e não o objecto Python, que estava correcto.

### O resto das armadilhas, e o que cada uma custa

| Coisa | Se estiver errado | Como aparece |
|---|---|---|
| `RegisterApplication` não devolve nada | atribuir o retorno ao caminho da app | regista bem e `start()` devolve `False` |
| `Notifying` só de leitura | o BlueZ recebe `PropertyReadOnly` ao activar a CCC | telefone ligado, PC mudo |
| Fragmentos de 22 bytes (MTU+3) | o link layer recorta sem erro | o rato não obedece, sem diagnóstico |
| `Service` como `s` e não `o` | o daemon descarta a característica | `No valid service object found` |

O limite de MTU é o mais subtil: o valor de uma característica é `MTU - 3` = 20
bytes com a MTU por omissão, e o cabeçalho de 2 bytes do framing sai **desse
total**. Confundir "20" com o corpo produz fragmentos de 22 bytes, e o erro é
que o link layer recorta em silêncio — não há excepção, não há `status`, não há
nada. Daí `ATT_WRITE_MAX` e `CHUNK_BODY` serem duas constantes e não uma.

### O framing não garante entrega

O cabeçalho de 2 bytes com o total da mensagem é o suficiente para recuperar
de uma perda no **primeiro** fragmento (o total não bate certo e o receptor
recomeça), e **não** para uma perda a meio com o total igual. Comandos do rato
e o `auth` cabem num fragmento cada; o que precisa de fragmentar é texto longo,
onde o pior caso é texto trocado. Numerar os fragmentos (3 bytes em vez de 2,
corpo com 17) é a correcção se algum dia um comando multi-fragmento precisar de
entrega garantida. Está escrito no código, não escondido.

### O `move` vai em binário

O JSON de um `move` são ~30 bytes e o valor de uma característica são 20:
qualquer `move` partir-se-ia em dois fragmentos, e a 60 Hz isso são 120
escritas por segundo. O caminho binário é `0x01` e dois `int16` em décimos de
píxel — 7 bytes com cabeçalho, uma escrita. `OP_MOVE` e `MOVE_SCALE` têm de
bater certo dos dois lados; é a única constante do protocolo duplicada, e a
única que pode divergir em silêncio.

Os `move` continuam acumulados e enviados de 24 em 24 ms, como no WebSocket, e
pelo mesmo motivo: com `write-without-response` cada escrita ocupa a ligação.

### O que está verificado e o que não

**Verificado contra o `bluetoothd` real:** `RemoteBLE.start()` devolve `True`
nesta máquina (BlueZ 5.64, adaptador `hci0`), e o `RegisterApplication` é
aceito com as três características.

**Não verificado:** nada de Android. Não há aparelho, e sem ele não há scan,
nem MTU negociada, nem ACCC, nem auth, nem `move` a mexer o rato a sério. O
lado do telemóvel está por `npm run typecheck` e por leitura; o Kotlin não foi
compilado.

Isto é o limite honesto desta secção: o protocolo está provado contra o daemon
que vai estar do outro lado, e o cliente ainda não foi ao encontro de um
telefone.

---

# Parte 2 — Lacunas face ao mercado

## 2.1 Como o mercado faz

Referências de comparação: **Logitech Flow** (rato multiplataforma), **Splashtop
Solo**, **AnyDesk**, **Chrome Remote Desktop**, **Windows RDP**, e **Tailwind /
Mouse Without Borders** (transporte de rato/teclado entre máquinas na LAN).

Propriedades que definem o padrão de qualidade:

### Latência percebida
- **Transporte:** UDP com recuperação de perda, ou WebSocket sobre TLS com compressão.
- **Emissão:** taxa fixa e independente da taxa de eventos (60–125 Hz), com
  interpolação no cliente — **não** "um evento por mensagem quando acontece".
- **Medição e display:** o produto mostra a latência ao utilizador.

### Percepção de qualidade do rato
- **Escala por resolução**, não por píxeis do dispositivo de controlo.
- **Curva de aceleração** e deadzone, afinados por perfil de utilizador.
- **Correcção de aspecto** e suporta múltiplos ecrãs com origem virtual correcta.
- **Preservação dos modos de entrada**: scroll por roda, inércia, botões
  programáveis, gesto de dois dedos.

### Teclado
- **Mapa completo** + composição de dead-keys.
- **Modo de colar** (clipboard) para texto comprido e caracteres exóticos.
- **Layouts e atalhos de teclado** seleccionáveis.

### Segurança (o eixo mais óbvio)
- **TLS obrigatório**, sempre.
- **Autenticação de dois factores** ou desafio interactivo.
- **Rate limiting e lockout** explícitos.
- **Allowlist de rede** e aviso de sessão activa.
- **Zero-trust:** o acesso expira, o logout é fácil de ver.

### Robustez de sessão
- **Reconexão automática** com backoff exponencial e jitter.
- **Detecção de ligação morta** por pong com timeout.
- **Fila de input** com escolha explícita de política (descartar vs. sincronizar).
- **Sobrevivência a background/foreground** no telemóvel.

## 2.2 Tabela comparativa

| Dimensão | Mãouse Remote hoje | Padrão de mercado | Gap |
|---|---|---|---|
| **Transporte** | `ws://` plaintext | TLS obrigatório | 🔴 |
| **Exposição** | port forwarding manual | túnel com URL rotativa | 🔴 |
| **TLS** | impossível (cliente remove `wss://`) | sempre | 🔴 |
| **Auth** | token 64 bits + lease ES256 assinada, sem limite de tentativas | 2FA / desafio | 🟠 |
| **Rate limit / lockout** | nenhum | explícito | 🔴 |
| **Gate Pro** | lease ES256 verificada no PC | monetizado | 🟢 |
| **Pausa** | **ignorada** pelo canal remoto | respeitada | 🔴 |
| **Clientes simultâneos** | ilimitado, `connected_count` morto | 1 sessão ou lista visível | 🔴 |
| **Métrica de latência** | ausente | visível ao utilizador | 🟠 |
| **Emissão do rato** | flush por evento a 24 ms | taxa fixa 60–125 Hz + interpolação | 🟠 |
| **Escala do rato** | px do telemóvel × 1.8 | escala por resolução do PC | 🟠 |
| **Aceleração** | nenhuma no touchpad | curva + deadzone + perfis | 🟠 |
| **Multi-monitor** | **origem perdida** | desktop virtual correcto | 🔴 |
| **Aspecto** | não corrigido | corrigido | 🟡 |
| **Auto-reconnect** | **nenhum** | backoff exponencial | 🔴 |
| **AppState** | **nenhum** | gerido | 🟠 |
| **Fila de input** | **nenhuma** (descarte silencioso) | política explícita | 🟠 |
| **Verificação de pong** | **nunca verificada** | timeout → reconnect | 🟠 |
| **Scroll** | 2 dedos, só vertical | vertical + horizontal + inércia | 🟠 |
| **Teclas especiais** | 7 botões | conjunto completo | 🟠 |
| **Ctrl/Alt/combos** | API existe, **nunca chamada** | sim | 🟠 |
| **Dead-keys** | não | composição correcta | 🟡 |
| **Colar texto** | não (per-char) | clipboard + Ctrl+V | 🟡 |
| **Acentos** | ✅ **funcionam, independentes do layout** | ✅ | 🟢 |
| **Autocorrect** | ✅ desligado correctamente | ✅ | 🟢 |
| **Sem logging de teclas** | ✅ | ✅ | 🟢 |
| **Testes (mobile)** | **zero** | suite | 🔴 |
| **Testes (desktop)** | finos, auth não-op | suite | 🟠 |
| **CI executa caminho crítico** | ❌ (Xvfb ⇒ sem `SendInput`) | ✅ | 🟠 |
| **Plataformas** | 🟡 Windows · 🔴 sem macOS | multiplataforma | 🟠 |

🔴 Crítico · 🟠 alto · 🟡 médio · 🟢 conforme

## 2.3 As 7 lacunas estruturais

### 1. É um canal de input remoto sem segurança de transporte 🔴

**Esta é a lacuna raiz.** O sistema expõe controlo total de rato e teclado de um PC
através de WebSocket em claro, num porto que a documentação manda encaminhar
manualmente para a Internet.

Não é um risco teórico. Quem alcance a porta 8765 e obtenha o token — que é mostrado
num campo de texto legível no diálogo de definições (`ui/settings_dlg.py:392-395`) —
obtém **controlo total, não confirmado e sem indicação visual de que está a
acontecer**. Pode digitar texto arbitrário, executar combinações de teclas, enviar
media keys, fechar janelas com Alt+F4. Não há limite de tentativas, o que torna o
força bruta do token viável mesmo que o espaço seja grande.

Enquanto isto não for corrigido, o produto **não deve ser vendido como acesso remoto
à Internet** — nem recomendado para uso fora da LAN de confiança.

### 2. Um bug de coordenadas entra pelo caminho principal 🔴

O rato é a função nuclear. E o rato está partido em multi-monitor sempre que um ecrã
esteja à esquerda ou acima do principal (`core/mouse_ctl.py:127-143`).

O agravante não é o bug — é que **um teste o afirma como comportamento correcto**
(`tests/test_move_gesture.py:176-201`). Isto é pior que um bug sem teste: é um bug
com um teste a protegê-lo, o que significa que quem corrigir o código vai ver o
teste falhar e pode assumir que a correcção está errada.

### 3. Nada mede a qualidade da experiência 🔴

Tal como na componente de gestos ([`RECONHECIMENTO_MAOS.md`](RECONHECIMENTO_MAOS.md)
§2.3 #1), **não existe instrumentação**.

Consequência directa e grave: os parâmetros de sensação — ganho, filtro, deadzone,
intervalo de emissão — são constantes fixas escolhidas sem medição
(`MOVE_GAIN = 1.8`, `MOVE_INTERVAL_MS = 24`). Não há como saber se o touchpad se
sente bem, porque **não há nada que meça**. E o problema [1.4](#14-rato--do-toque-ao-pixel-mobile)
— sensibilidade função do hardware do telemóvel — é *invisível* sem um corpus de
dispositivos com métricas.

### 4. Robustez de sessão é zero 🟠

Auto-reconnect, tratamento de `AppState`, verificação de pong e fila de input: **as
quatro ausentes**. É a diferença entre "um produto que às vezes falha" e "um produto
em que se pode confiar". A combinação de *sem fila* + *sem reconnect* significa que
qualquer queda de rede produz perda silenciosa de input, e o utilizador não tem como
saber o que chegou ao PC.

### 5. A monetização não cobre o canal mais valioso 🟢 *(resolvido 2026-10-02)*

~~O engine de gestos por câmara está correctamente atrás do gate Pro. O rato e o
teclado remotos **não estão** — e são o que produz trabalho real (alguém a controlar
o PC de outro lado está a usar o produto, não a toy).~~

**Corrigido a 2026-10-02:** o rato e o teclado remotos passaram a exigir uma lease
ES256 de tier pago, verificada no PC com a chave pública embebida, para além do token
de emparelhamento. O engine de gestos por câmara continua atrás do gate do `App.tsx`;
os dois canais estão agora cobertos pelo mesmo critério de pagamento.

Isto era simultaneamente um problema de **segurança** e de **negócio**: o feature
mais perigoso era também o único que dava controlo total sem pagamento. O que
sobra como risco residual é o que a assinatura não resolve. O verificador do PC
checa **assinatura, tier e `exp`** — e nada mais: o lease traz `revocation_nonce` e
`use_seq`, mas o PC não consulta nenhum estado de revogação, logo uma lease já emitida
não pode ser revogada antes de expirar. E, como é um bearer token guardado em
`AsyncStorage`, pode ser copiada e reaplicada noutro dispositivo durante a validade.
A `ws://` em claro deixa ainda a assinatura e o token legíveis na rede. Ver os
achados #3 (TLS) e #4 (rate limit), ambos ainda abertos.

### 6. Convenções de coordenadas delegadas ao acaso 🟠

O mapeamento normalizado→pixel usa `int()` (truncamento, não arredondamento), e a
origem do desktop virtual é assumida como `(0,0)`. São decisões que *parecem* inofensivas
e são exactamente o tipo de detalhe que faz um rato remoto sentir-se "quase bom".
Nenhuma está documentada com a sua intenção; o teste existente fixa o resultado
truncado, o que converte um acidente em contrato.

### 7. Concorrência sem sincronização 🟠

Um único `MouseCtl` é partilhado entre a thread asyncio do servidor remoto e a thread
Qt do motor de câmara (`main.py:310-313`). Ambos mutam `_frac_x`/`_frac_y` e fazem
read-modify-write não sincronizado sobre `mouse.position`. Sob carga — por exemplo,
mouse a ser movido pela câmara enquanto um arrasto remoto está activo — os deltas
perdem-se e as posições divergem. Não há manifests de concorrência; é uma bomba
relógio de baixa frequência.

---

# Parte 3 — Plano para nível profissional

## 3.0 Princípio: segurança antes de conforto

Este plano **não** começa por melhorar a sensação do rato. Começa por um teste
de asserção que hoje está a dar um falso verde, e por um manifesto de
instalação que não declarava as dependências de que o produto depende.

A razão: o teste que fixa o bug multi-monitor (#2) é uma **corrupção activa do
nosso próprio sinal de qualidade** — não é um bug que o utilizador sente, é um bug
que nos impede de medir. E os manifestos de instalação estavam errados (#0): o
`setup.bat` instalava uma aplicação que não arrancava.

> ⚠️ **Correcção a este excerto (2026-09-28).** A versão anterior começava por
> `websockets>=14.0` e dizia que isso "rebenta[va] qualquer instalação limpa — que é
> exactamente o que a EAS faz no CI". **Ambas as afirmações eram falsas** (ver
> [§1.14.1](#1141-correção-o-item-1-era-um-falso-positivo-)): o floor do `websockets`
> já está correcto, e a EAS nunca instala este manifesto Python.
>
> E o inverso acabou por ser verdade por outra via: havia um manifest bugado a
> sério, a fazer a aplicação não arrancar numa instalação limpa — mas o culprit
> era o `cryptography` em falta, não o `websockets`
> ([§1.14.2](#1142-encontrado-enquanto-se-verificava-o-falso-positivo-um-bug-real-mais-grave-)).

## 3.1 Onda 0 — Instrumentação e correções de bloqueio

### 0.1 Correcções de dependência — ✅ entregue 2026-09-28

- 🔴 **`cryptography` acrescentado** a `requirements.txt` e
  `requirements-linux.txt`. Estava em falta e era fatal: `main.py:35` importa
  `core.licensing` ao nível do módulo, logo o `setup.bat` instalava uma aplicação
  que não arrancava.
  [§1.14.2](#1142-encontrado-enquanto-se-verificava-o-falso-positivo-um-bug-real-mais-grave-)
- ✅ **`pyproject.toml` limpo**: as secções `[build-system]`, `[project]` e
  `[tool.setuptools]` foram apagadas — eram mortas, e o nome mentia sobre o
  produto. O ficheiro fica só com a config de pytest/ruff/mypy, que é o seu
  trabalho real aqui. Ver **1.14.3** abaixo.
- ✅ **`comtypes` removido** de `requirements.txt`: é transitiva do
  `uiautomation` e não é importado por lado nenhum.
- ❌ ~~`websockets>=13.0` → `websockets>=14.0`~~ **Cancelado.** O floor já
  estava certo: `websockets.asyncio` existe desde a 13.0 (ver **1.14.1**).
- ✅ **Trancado contra recorrência:** `tests/test_manifests.py` (7 testes)
  compara `requirements.txt` e `requirements-linux.txt` com os imports
  reais do código e falha nos dois sentidos — dependência em falta *e*
  dependência que nada usa. E o CI passou a instalar
  `requirements-linux.txt`, que **ninguém instalava** e que por isso podia
  apodrecer em silêncio.

Fica de fora de propósito: um `requirements-windows.txt` próprio. O
`requirements-linux.txt` já é a variante sem `uiautomation`, e um teste garante
que a divergência entre os dois é exactamente essa — nada mais.

### 0.2 Teste de asserção para a origem virtual

Antes de corrigir o bug, **verificar que o teste o detecta**:

```python
# tests/test_remote.py — substituir o clamp actual
class FakeMouseOrigin:
    screen_w, screen_h = 3840, 1080
    # desktop virtual com origem negativa: monitor principal à direita
    origin_x, origin_y = -1920, 0

def test_move_to_respects_virtual_origin():
    srv._handle("move_to", {"x": 0.0, "y": 0.0})
    assert mouse.mouse.position == (-1920, 0)   # canto esquerdo do desktop virtual
```

*Critério de aceitação:* este teste **falha** antes da correcção. Se passar antes,
o modelo do problema está errado.

### 0.3 Corrigir a origem virtual

`core/mouse_ctl.py:127-143` passa a ler também 76/77 e a expor `origin_x/origin_y`.
`_move_to` (`core/remote.py:354-359`) e o clamp de `move_by`
(`core/mouse_ctl.py:186-189`) passam a mapear para `[origin, origin + size]`.

Corrigir também `int()` → `round()` em ambos, e documentar a decisão (o `-1` em
`W−1` deve ser mantido: normalizado `1.0` deve cair no último pixel, nunca fora).

### 0.4 Tornar a asserção de auth real

`tests/test_remote.py:167-169` está dentro de `try/except Exception: pass` — um
cliente que nem consiga ligar-se passa o teste. Reescrever com o servidor a correr
em `127.0.0.1:0`, assertando explicitamente o fecho por token inválido.

### 0.5 Instrumentar latência ponta-a-ponta

Sem isto, nenhuma Onda seguinte pode ser avaliada.

- Timestamp monotónico no `move` gerado no telemóvel; eco no `pong`; o desktop
  calcula o RTT e devolve-o. O cliente **mostra a latência no ecrã**.
- Contadores de comandos: enviados, recebidos, **descartados** (não prontos), duplicados.
- Registo de desligões com motivo (`close code`, `reason`).

*Critério de aceitação:* `python tools/eval_remote.py` produz um relatório com RTT
p50/p95/p99 e contagem de descartes, a partir de uma sessão real gravada.

## 3.2 Onda 1 — Rato com feel profissional

O objectivo é passar de "funciona" a "não quero deixar de usar".

### 1.1 Escala por resolução ⚠️ maior ganho isolado

Hoje: `px_telemóvel × 1.8`. O correcto é escalar pela **resolução do PC**, que já
chega ao cliente na resposta de `auth` (`w`, `h` — hoje apenas apresentados,
`RemoteScreen.tsx:270-274`).

```
ganho = (largura_pc / largura_pc_de_referencia) × ganho_base
```

Efecto imediato: o mesmo gesto físico produz o mesmo movimento **independentemente do
telemóvel**. Este é o problema [1.4](#14-rato--do-toque-ao-pixel-mobile) resolvido, e
é a razão pela qual a experiência actual não se pode descrever como profissional.

### 1.2 Ligar o filtro ao touchpad ⚠️ o filtro já existe

`OneEuroFilter` e `AccelCurve` estão testados (`src/engine/filters.ts`) e são usados
pelo caminho da câmara. O touchpad não os usa. Instanciá-los é trabalho de linkage,
não de escrita.

Cuidado: filtrar adiciona latência. O `beta` do One-Euro existe para cortar mais
quando é rápido. Começar com `min_cutoff` mais alto que o da palma e calibrar contra
a métrica de latência da Onda 0.

### 1.3 Curva de aceleração e deadzone

`AccelCurve` (`min_gain` 1.2 → `max_gain` 3.0, `ref_speed`, expoente 1.7) dá o
comportamento esperado: preciso quando lento, agressivo quando rápido. Deadzone de
1–2 px elimina o micro-tremor de dedos em repouso.

*Impacto esperado:* a diferença entre "sensível ao hardware do telemóvel" e
"consistente e previsível".

### 1.4 Correcção de aspecto

Mapear o touchpad (9:19.5) num PC 16:9 estica anisotropicamente. Normalizar pelo eixo
mais limitante, como o engine de gestos já faz (`core/engine.py:439-441`):
`s = min(largura_pc / largura_touchpad, altura_pc / altura_touchpad)`.

### 1.5 Emissão a taxa fixa

Hoje o rato emite um `move` por flush de 24 ms, com o delta acumulado. Funciona, mas
não interpola: entre dois flushes o cursor **para**. Uma `SmoothEmitter` dedicada
(mesmo padrão de `core/motion.py`, a ~120 Hz) com acumulador fraccionário dá
movimento contínuo.

*Critério:* com o telemóvel imóvel, o cursor não deve apresentar degraus visíveis.

## 3.3 Onda 2 — Robustez da ligação

### 2.1 Auto-reconnect com backoff

```
tentativa   atraso
1           0.5 s
2           1 s
3           2 s
4           4 s
5+          8 s (teto) + jitter exponencial
```

Reconectar automaticamente apenas se a queda foi **não intencional** (mudança de rede,
Wi-Fi a cair) — nunca após um `disconnect()` pedido pelo utilizador. Mostrar estado
de "a reconectar…" em vez do formulário de ligação.

### 2.2 Detecção de ligação morta

Verificar o `pong`. Se não chegar em `2 × PING_INTERVAL`, forçar close e entrar no
ciclo de reconnect. Isto converte a falha silenciosa de "parece ligado mas nada
funciona" numa falha visível e recuperável.

### 2.3 Política de fila explícita

Hoje `sendRaw` descarta em silêncio (`remoteClient.ts:173`). Duas opções, ambas
honestas:

- **Descartar e avisar** — mostrar "3 comandos perdidos" ao utilizador. Simples, e
  evita atrasar input antigo contra um PC que já mudou.
- **Reenviar comandos estruturais** (cliques, teclas) mas descartar movimento.

Recomenda-se a primeira, com o contador visível. Silêncio é o pior dos dois mundos.

### 2.4 `AppState`

- **Background** → parar timers, marcar a sessão como suspensa.
- **Foreground** → validar a ligação antes de darucceeded o controlo; reconectar se
  necessária.

### 2.5 Corrigir `_combo` e `press`/`release`

- `core/remote.py:475` — `time.sleep(0.04)` **dentro do event loop** bloqueia o
  servidor inteiro. `await asyncio.sleep(...)` com o handler tornado async, ou
  `asyncio.to_thread`.
- ~~`core/remote.py:379-397` — dar estado de arrasto a `press`/`release`, com
  `try/finally` para libertar o botão se a ligação cair a meio do gesto.~~
  **Feito a 2026-10-02:** `press` e o gesto `left_down` passam por um registo único
  (`_held`, com `lmb`/`left` canonicalizados no mesmo botão) e o `finally` de
  `_on_connect` solta o que ficou premido. 14 testes em
  `tests/test_remote_drag_release.py`.
- `core/remote.py:489` — estreitar o `except Exception` a `InvalidCharacterException`
  para tornar a duplicação de texto impossível.

### 2.6 Lock no `MouseCtl`

`threading.Lock` à volta das mutações de `_frac_x/_frac_y` e do read-modify-write de
`mouse.position` (`core/mouse_ctl.py:178-189`). Alternativa mais limpa: dar ao
`RemoteServer` o seu próprio controlador. Reavaliar contra a métrica de "comandos
descartados" da Onda 0.

## 3.4 Onda 3 — Teclado profissional

### 3.1 Matar a corrupção por diff

Substituir o diff por índice (`RemoteScreen.tsx:82-105`) por envio **directo** do
texto completo em cada alteração, com o desktop a substituir por `Ctrl+A` + colar
— ou, mais simples e sem latência perceptível, por um pequeno buffer de reconciliação
que detecta e reenvia a cauda divergente.

*Critério de aceitação:* inserir texto no meio de uma frase já escrita
aparece correctamente no PC.

### 3.2 Double-Enter

Escolher uma via: ou `onChangeText` trata `\n`, ou `onSubmitEditing`. Não ambas.
Manter `blurOnSubmit={false}`.

### 3.3 Completar os botões

Adicionar **Home · End · PageUp · PageDown** — a API do desktop (`core/remote.py:421-438`)
já os suporta, é só UI. Adicionar uma **barra de modificadores** (Ctrl/Alt/Shift/Win)
que fica premida enquanto o utilizador toca outra tecla: activa a API `combo()`, hoje
**implementada e nunca chamada**. É a forma de ter Ctrl+C, Ctrl+V, Alt+Tab, Win+D.

### 3.4 Scroll horizontal e zonas de margem

Scroll horizontal de 2 dedos (o desktop já suporta `scroll.dx` —
`core/remote.py:399-406` —, o telemóvel nunca envia). Opcionalmente zonas de scroll
nas margens, para quem segura o telemóvel como um rato traditional.

### 3.5 Testar os acentos ⚠️ a afirmação que protegemos

Escrever testes para `_type_text` com `"ã ç é í ó ú â ê õ"`, comparando com uma
referência. Este é o requisito de mercado número um e hoje **não tem um único teste**.

## 3.5 Onda 4 — Superfície de produto

### 4.1 Segurança de transporte

O item de maior impacto e maior custo. Por ordem de custo/benefício:

1. **Rate limiting + lockout** na auth — barato, fecha o força bruta. Exponential
   backoff por IP, com reset após janela de sucesso.
2. **Comparação em tempo constante** (`hmac.compare_digest`) — uma linha.
3. **Gerar e fazer rotate do token** por sessão, com expiração.
4. **Indicador de sessão activa** no desktop + confirmação em acções destrutivas
   (combos com Alt+F4, Cmd+Q).
5. **TLS** — certificado auto-gerado, ou `wss://` via túnel. Nota: `buildWsUrl`
   (`remoteClient.ts:33-41`) tem de deixar de remover `wss://`.
6. **Allowlist de sub-redes** (por omissão, só LAN privada).

### 4.2 Fechar os bypasses

- ~~**`press`/gate Pro:** decidir se o rato/teclado remoto é Pro ou Free, e **aplicar o
  gate em `core/remote.py`** — hoje não existe lá nenhum. Recomenda-se Pro: é o feature
  controlo real, e é simultaneamente o mais perigoso.~~ **Feito a 2026-10-02:**
  é Pro, e o gate está no `auth` do `core/remote.py` — a ligação só é aceite com o
  token de emparelhamento **e** uma lease ES256 válida (`mobile_pro`/`pro`, não
  expirada) que o PC verifica com a sua chave pública. `press` deixou de ser o caso
  especial: o gate está à entrada do canal, antes de qualquer comando ser despachado.
- **Respeitar `state["paused"]`** no canal remoto, com excepção para `left_up` (como
  já acontece no engine local) para o botão nunca ficar premido.

### 4.3 Túnel em vez de port forwarding

Substituir o `ws://IP:8765` público por um túnel (ngrok, Cloudflare Tunnel, Tailscale)
com URL temporária. Elimina de uma vez a necessidade de abrir a porta no router e dá
TLS sem certificados geridos à mão.

### 4.4 Limitar clientes e logout

Usar `connected_count` (`core/remote.py:192`, hoje morto) para **uma sessão activa**.
A UI mostra quem está ligado e como desligar.

## 3.6 Roadmap

```
Onda 0  Manifesto + asserções + origem virtual + instrumentação
        └─ o manifesto de instalação passa a declarar o que o código usa, apanha o
           bug multi-monitor, cria métricas
           Critério: setup.bat numa venv limpa arranca o produto (o cryptography
                    faltava e a aplicação não arrancava — §1.14.2);
                    requirements-linux.txt é instalado pelo CI;
                    teste de origem falha antes / passa depois;
                    eval_remote.py produz RTT p50/p95/p99

Onda 1  Escala + filtro + aceleração + aspecto + emissão fixa
        └─ o rato deixa de depender do telemóvel
           Critério: mesmo gesto em 3 dispositivos → mesmo deslocamento;
                    sem degraus visíveis a 120 Hz; p95 de clique < 80 ms

Onda 2  Reconnect + pong + AppState + fila explícita + _combo/_frac
        └─ a ligação sobrevive a uma queda de Wi-Fi
           Critério: queda de 30 s recupera sozinha; 0 comandos perdidos
                    silenciosamente

Onda 3  Teclado: diff correcto, double-enter, teclas + modificadores,
        scroll horizontal, testes de acentos
        └─ o teclado é tão fiável como o rato
           Critério: 20 minutos de escrita mista sem um carácter errado

Onda 4  TLS + rate limit + allowlist + gates Pro/pausa + túnel + sessões
        └─ o produto pode ser vendido como acesso remoto
           Critério: nenhum comando remoto sem auth válida;
                    forca bruta bloqueada em 10 tentativas
```

## 3.7 Métricas de aceitação

Definir em números **antes** de escrever código da Onda 1.

| Métrica | Como | Alvo |
|---|---|---|
| RTT cliente↔PC | eco no `pong` | p95 < 60 ms (LAN) |
| Latência de clique ponta-a-ponta | marca no toque, marca no inject | p95 < 80 ms |
| Degraus de movimento | captura da posição a 120 Hz | sem saltos > 2 px |
| Coerência de escala | mesmo gesto em 3 telemóveis | deslocamento dentro de ±5% |
| Comandos descartados | contador | **0 silenciosos** (sempre visíveis) |
| Recuperação de queda | desligar o Wi-Fi 30 s | reconecta sozinha < 10 s |
| Fidelidade de texto | 500 caracteres mistos incluindo acentos | 0 caracteres errados |
| Acentos | suite de teste com `ã ç é í ó ú â ê õ` | 100% |
| Tentativas de auth falhadas | mesmo IP | bloqueado em ≤ 10 |
| Latência de reconexão em 2.º plano | fundo → frente | < 2 s |
| Cobertura de testes mobile | `npm test` | ≥ 80% em `services/` e `engine/` |

## 3.8 Riscos e não-objetivos

**Riscos:**

| Risco | Mitigação |
|---|---|
| TLS exige certificados → complexidade operacional | Rate limit + allowlist primeiro; TLS depois, com auto-geração |
| Túnel exige conta num serviço externo | Avaliar Tailscale / Cloudflare Tunnel (sem cartão) |
| Corrigir o teste multi-monitor invalida a asserção actual | Onda 0.2 escreve o teste **antes** da correcção, propositadamente a falhar |
| Onda 1 pode *piorar* o feel actual se não medida | Onda 0.5 cria a métrica **antes** de mexer no ganho |
| Escalar o remote a Pro pode alienar utilizadores Free | Decisão de negócio, não técnica — registar em `BUSSINES/` |
| Um segundo manifesto de dependências divergir do `requirements.txt` em silêncio | **Resolvido** 2026-09-28: o `pyproject.toml` deixou de ter `[project].dependencies` (§1.14.3) e `tests/test_manifests.py` compara os manifestos com os **imports do código**, não uns com os outros. Um teste entre duas listas só prova que são iguais — não que *qualquer* uma esteja certa |
| `requirements-linux.txt` não é instalado por ninguém | **Resolvido** 2026-09-28: passo de CI que o instala. Era a causa de fundo do `cryptography` em falta — o manifesto Linux podia divergir sem ninguém dar por isso |

**Não-objetivos (por agora):**

- ❌ **Não** tentar substituir o desktop remoto com streaming de vídeo — é outro
  produto, com codecs, e não é o que está em falta.
- ❌ **Não** construir um teclado customizado completo no ecrã — o teclado do sistema
  resolve e já trata de acentos correctamente.
- ❌ **Não** suportar iOS antes de o Android estar sólido — a superfície de bugs é
  maior e o `expo-dev-client` já exige Android.
- ❌ **Não** prometer multi-utilizador — `connected_count` existe, uma sessão é
  suficiente.
- ❌ **Não** mexer no motor de gestos por câmara neste plano — ver
  [`RECONHECIMENTO_MAOS.md`](RECONHECIMENTO_MAOS.md).

---

*Documento técnico — Luar Studio Angola · 2026-09-28 · Domínio de responsabilidade:
Fortuna (mobile · remote · Linux · CI) · Produzido pelo pipeline de agentes de IA da
empresa, revisto no código. Confidencial.*
