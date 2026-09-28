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
| **Âmbito** | `mobile/airmouse-mobile/` (cliente) + `core/remote.py`, `core/mouse_ctl.py` (servidor) |
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

### 🔴 Bug crítico: multi-monitor sem origem

`core/mouse_ctl.py:127-143` lê o **tamanho** do desktop virtual mas **nunca a origem**:

```python
# core/mouse_ctl.py:130-131
w = int(user32.GetSystemMetrics(78))  # SM_CXVIRTUALSCREEN
h = int(user32.GetSystemMetrics(79))  # SM_CYVIRTUALSCREEN
```

`SM_XVIRTUALSCREEN` (76) e `SM_YVIRTUALSCREEN` (77) **não aparecem em lado nenhum do
código** (verificado em `core/`, `ui/`, `main.py`). Entretanto o pynput posiciona via
`SetCursorPos`, que usa coordenadas de desktop virtual e **aceita valores negativos**.

| Configuração | Origem virtual | Resultado |
|---|---|---|
| 2 monitores lado a lado, principal à esquerda | `(0, 0)` | ✅ correcto |
| Qualquer monitor **à esquerda ou acima** do principal | `(−W₂, 0)` | 🔴 faixa inalcançável; `move_by` encurrala o cursor no monitor principal |

É o bug clássico desta classe, e é exactamente o cenário de quem faz *trading* com
vários ecrãs.

⚠️ **Pior: um teste afirma o bug como correcto.**
`tests/test_move_gesture.py:176-201` fixa o clamp `[0, screen_w−1]` num ecrã
sintético 2000×1200, sem qualquer noção de origem. O bug fica **enterrado pela
mesma suite que o deveria apanhar**.

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
3. **Zero testes.** A afirmação mais importante para o mercado **não tem um único
   teste** que a proteja.

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

Verificado por pesquisa em `core/remote.py`: **zero ocorrências** de `paused`,
`licens`, `is_pro`. `state["paused"]` é verificado por todos os caminhos de comando
locais (`core/commands.py:115,125,133`), mas **um telemóvel ligado mantém controlo
total enquanto a app está "pausada"**. E `cfg.remote_enabled` não é subjecto a
`is_pro_locked` (`main.py:247-259`).

🔴 **Bypass de monetização:** o touchpad e o teclado remotos **não** estão atrás do
gate Pro. Só o encaminhamento por gestos de câmara está (`App.tsx:153`). Um utilizador
Free obtém rato + teclado remotos completos, grátis.

### Dois pontos positivos

- ✅ **Sem logging de teclas.** Só se regista o endereço de ligação
  (`core/remote.py:258`), um prefixo de 4 caracteres do token no arranque
  (`core/remote.py:238`), e o *nome* do comando em falha (`core/remote.py:277`).
  `_type_text` não regista nada. **Nenhum `Listener` de teclado do pynput é
  instanciado** (verificado: zero `on_press` / `Listener(` em `core/` e `main.py`).
- ✅ **Token de entropia adequada** — 64 bits de `secrets`.

## 1.10 Cobertura de testes

### Mobile: **zero**

Sem ficheiros `*.test.*` / `*.spec.*`, sem directório `__tests__/`, sem `jest` ou
`vitest` configurado, e **sem `test` script** no `package.json`.

Consequência: a matemática de coordenadas, os filtros, o diff do teclado e todo o
caminho de mensagens do `RemoteClient` estão **completamente por cobrir** — apesar de
serem funções puras e trivialmente testáveis.

### Desktop: `tests/test_remote.py` existe, mas é fino

| Teste | O que realmente afirma |
|---|---|
| `test_dispatch_move_to_clamps` | Aritmética contra `FakeMouse` (`screen_w=1920`). **Não modela origem** — estruturalmente incapaz de detectar o bug multi-monitor. Fixa o truncamento como se fosse intenção. |
| `test_auth_and_commands_over_websocket` | Servidor real em `127.0.0.1:0`. ⚠️ **A asserção de bad-auth é um no-op** — está dentro de `try/except Exception: pass` (linhas 167-169), portanto um cliente que nem consiga ligar-se passa. |
| `test_generate_token_is_unique` | Não-vazio, `len >= 8`, distinto. **Não** afirma a força real de 64 bits. |
| `test_key_aliases_arrow_keys` | Único teste que toca pynput real. |
| `test_dispatch_move_click_scroll_press` | Despacho contra `FakeMouse`. |

**Não testado de todo:** injecção de texto, `_type_text`, `_combo`, `_tap_key,
**caracteres acentuados**, media keys, a tabela de gestos, simetria de arrasto,
coordenadas multi-monitor, rejeição de auth ou replay, clientes concorrentes.

⚠️ **A CI não executa o caminho crítico.** `.github/workflows/ci.yml` corre
`QT_QPA_PLATFORM=offscreen xvfb-run -a pytest tests -q` em Linux. Como
`sendinput_available()` devolve `False` em Linux (`core/mouse_ctl.py:69-75`), **todo
o fast path `SendInput` do Windows nunca corre na CI** — só o fallback do pynput.

## 1.11 Limitações conhecidas

Consolidadas e verificadas no repositório em 2026-09-28.

| # | Gravidade | Limitação | Evidência |
|---|---|---|---|
| 1 | 🔴 Crítico | **`websockets>=13.0` é um floor inválido.** O código importa `websockets.asyncio.server`, que só existe a partir da 14.0. Instalações limpas rebentam com `ImportError`. | `requirements.txt:5`, `core/remote.py:223` |
| 2 | 🔴 Crítico | **Multi-monitor sem origem** — cursor encurralado no monitor principal se algum ecrã estiver à esquerda/acima. | `core/mouse_ctl.py:127-143,186-189` |
| 3 | 🔴 Crítico | **Sem TLS**, e o cliente impede usar `wss://`. | `core/remote.py:227-231`, `remoteClient.ts:36` |
| 4 | 🔴 Crítico | **Sem rate limit / lockout / allowlist** numa porta aberta à Internet. | `core/remote.py:250` |
| 5 | 🔴 Crítico | **Bypass do gate Pro** — rato e teclado remotos são grátis. | `App.tsx:153` vs ausência em `remote.py` |
| 6 | 🟠 Alto | **Condição de corrida no `MouseCtl` partilhado** — thread asyncio remota e thread Qt/escala mutam `_frac_x/_frac_y` e `mouse.position` sem lock. | `main.py:310-313` |
| 7 | 🟠 Alto | **`pyproject.toml` não declara as dependências** — só `cryptography>=42`. `pip install .` não instala pynput nem websockets. | `pyproject.toml:10-12` |
| 8 | 🟠 Alto | **Bypass do toggle de pausa** — controlo total com a app "pausada". | ausência em `remote.py` |
| 9 | 🟠 Alto | **`_combo` bloqueia o event loop** 40 ms com `time.sleep`. | `core/remote.py:475` |
| 10 | 🟠 Alto | **`press`/`release` sem estado de arrasto** — sem `finally` de limpeza, um socket que cai a meio de um arrasto deixa o botão logicamente premido. | `core/remote.py:379-397` |
| 11 | 🟠 Alto | **Sem auto-reconnect, sem AppState, sem fila.** Input perdido em silêncio. | `src/services/remoteClient.ts` |
| 12 | 🟡 Médio | **Zero testes no mobile**; suite desktop não cobre auth nem texto. | `tests/test_remote.py` |
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
| `websockets>=13.0` no manifesto | `requirements.txt` | ✅ `websockets>=13.0` |
| `pyproject.toml` incompleto | `pyproject.toml:10-12` | ✅ só `cryptography>=42` |
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
| **Auth** | token 64 bits, sem limite de tentativas | 2FA / desafio | 🔴 |
| **Rate limit / lockout** | nenhum | explícito | 🔴 |
| **Gate Pro** | **ausente** — remoto é grátis | monetizado | 🔴 |
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

### 5. A monetização não cobre o canal mais valioso 🔴

O engine de gestos por câmara está correctamente atrás do gate Pro. O rato e o
teclado remotos **não estão** — e são o que produz trabalho real (alguém a controlar
o PC de outro lado está a usar o produto, não a toy).

Isto é simultaneamente um problema de **segurança** e de **negócio**: o feature
mais perigoso é também o único que dá controlo total sem pagamento.

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

Este plano **não** começa por melhorar a sensação do rato. Começa por
`websockets>=14.0` e por um verificador de asserções nos testes existentes.

A razão: os itens 1 e 2 das limitações são **bugs que já estão a custar
instalações**. `websockets>=13.0` rebenta qualquer instalação limpa — que é
exactamente o que a EAS faz no CI. E o teste que fixa o bug multi-monitor é uma
corrupção activa do nosso próprio sinal de qualidade.

Correcção de 10 minutos antes de 100 linhas de código novo.

## 3.1 Onda 0 — Instrumentação e correções de bloqueio

### 0.1 Correcções de dependência ⚠️ desbloqueia a EAS

- `requirements.txt:5` — `websockets>=13.0` → **`websockets>=14.0`**. O código importa
  `websockets.asyncio.server` (`core/remote.py:223`), que só existe a partir da 14.0.
- `pyproject.toml:10-12` — alinhar com `requirements.txt`. Enquanto `pip install .`
  não instalar pynput e websockets, o manifesto mente sobre o produto.
- Mover `uiautomation` e `comtypes` para `requirements-windows.txt` (já existe
  `requirements-linux.txt` a fazer isto parcialmente).

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
- `core/remote.py:379-397` — dar estado de arrasto a `press`/`release`, com
  `try/finally` para libertar o botão se a ligação cair a meio do gesto.
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

- **`press`/gate Pro:** decidir se o rato/teclado remoto é Pro ou Free, e **aplicar o
  gate em `core/remote.py`** — hoje não existe lá nenhum. Recomenda-se Pro: é o feature
  controlo real, e é simultaneamente o mais perigoso.
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
Onda 0  Dependências + asserções + origem virtual + instrumentação
        └─ desbloqueia EAS, apanha o bug multi-monitor, cria métricas
           Critério: npm ci passa; teste de origem falha antes / passa depois;
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
| `websockets>=14.0` pode revelar incompatibilidades | Testar em venv limpo antes de fazer o merge |

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
