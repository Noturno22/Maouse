# Afinação com animação + Trading Master Pro — Design

**Data:** 2026-09-13
**Branch:** `feature/tuning-animation-trading-pro`
**Tipo:** Feature (UI + licenciamento)
**Estado:** Design aprovado pelo utilizador (2026-09-13, revisão com Task 8).
**Rev. 2 (2026-09-13):** Pause ON/OFF deixa o menu lateral → botão circular no
centro-inferior (por baixo do logo), com animação on/off (Task 8).

## 1. Contexto e problema

### 1.1 Sliders das Definições
Os sliders do painel Cursor (`ui/settings_dlg.py::_slider_block`) atualizam o valor
instantaneamente e sem qualquer feedback: mudar o ganho, a zona morta ou a
estabilidade não transmite a sensação de "estar a afinar". Não há animação nem
feedback visual premium.

### 1.2 Trading Master sem gate
O Modo Trading Master **não está protegido por licença**: o `PRO_LOCKED` de
`core/licensing.py` não contém `trading_master`, o `_toggle_trading_master` de
`ui/main_window.py` ativa o modo sem verificar o plano, e a tecla `T` liga-o
livremente. O painel Trading em `ui/settings_dlg.py` não mostra badge/limite
nem dá caminho de compra. O produto existe na grelha (`_PRODUCTS`, €149,90) e no
checkout (`open_checkout("trading_master")`), mas é **só para assinantes pagos**.

### 1.3 Pause no menu lateral
O botão ON/OFF de pausa vive no `MenuPanel` (`ui/menu_panel.py::btn_pause`) como
mais um botão de lista, sem destaque. Entregou-se "botão" mas não a sensação de
interruptor principal: o comando central (parar/retomar o rato) está escondido
numa lista lateral. Deve passar a interruptor circular no centro da janela,
**por baixo da imagem de fundo central**. A tecla `Espaço` continua a alternar.

## 2. Objetivo

1. **Animar os sliders atuais** (só painel Cursor; sem painel novo) com:
   - **contador** — o número do valor desliza/cresce do valor antigo ao novo;
   - **brilho** — acende ao ajustar, mantém-se vivo enquanto arrastas e esfumaça ao largar.
2. **Gating Trading Master para pagos**, em profundidade: core, UI de Definições,
   janela principal e arranque, mais testes.
3. **Pause ON/OFF como interruptor principal**: sair do menu lateral e passar a
   botão circular moderno por baixo do logo central, com animação on/off.

Sem alterar comportamento dos outros painéis nem a API de `_save`/`_reset_defaults`.

## 3. Parte 1 — TuneSlider (widget novo)

Novo módulo `ui/tune_slider.py`, auto-contido e testável.

### 3.1 API
```python
class TuneSlider(QFrame):
    # sinais
    valueChanged = Signal(int)
    def __init__(self, name, formatter=None, parent=None,
                 tween_ms=220, glow_ms=450, accent=ACCENT_GLOW): ...
    def value(self) -> int
    def setValue(self, value: int)
    def setRange(self, lo: int, hi: int)
    # atributos
    slider: QSlider
    value_label: QLabel      # objectName "SliderValue"
    name_label: QLabel       # objectName "SettingsLabel"
```

- `formatter(value:int) -> str` — mesmo papel dos `on_change` atuais dos sliders
  (ex.: `lambda v: f"{v / 10:.1f}"`, `lambda v: f"{v}px"`). Default `str`.
- `tween_ms`/`glow_ms` são injetáveis nos testes (determinismo e velocidade).

### 3.2 Contador (tween)
- Cada `setValue` que muda o valor dispara um `QVariantAnimation` (~`tween_ms`,
  easing `OutCubic`) que gera o número exibido do valor antigo ao novo, chamando
  `formatter` em cada frame e atualizando `value_label`.
- Se um novo `setValue` chegar durante uma animação, a animação reinicia a partir
  do valor atual exibido (sem saltos).
- Clamp do tween ao inteiro mais próximo antes de formatar (os valores são ints
  no slider; o formatador re-scale para float).

### 3.3 Brilho (glow)
- Efeito `QGraphicsDropShadowEffect` (offsets 0,0, cor `accent`) aplicado ao
  TuneSlider.
- **Ajuste (`valueChanged` por qualquer causa):** glow "ignite → fade" — alpha
  sobe até ~150 e desce a 0 ao longo de `glow_ms`.
- **Arrastar (`sliderPressed` / `sliderReleased`):** durante o drag mantém brilho
  forte (~150, blur médio); ao largar, esfumaça em ~350 ms.

### 3.4 Integração em `ui/settings_dlg.py`
- Substituir `_slider_block` pelos TuneSlider no painel Cursor:
  - Ganho: `formatter=lambda v: f"{v / 10:.1f}"`, range 6–50.
  - Zona morta: `formatter=lambda v: f"{v}px"`, range 0–20.
  - Estabilidade: `formatter=lambda v: f"{v} frames"`, range 1–6.
- `_save` mantém `self._gain_sl.value()` etc. (API compatível).
- `_reset_defaults` mantém `self._gain_sl.setValue(...)`.
- `_slider_block` é removido (sem outros utilizadores).

## 4. Parte 2 — Trading Master só para pagos

### 4.1 Core — `core/licensing.py`
- Adicionar `"trading_master"` a `PRO_LOCKED`. `is_pro_locked(Tier.FREE, "trading_master")`
  passa a `True`; `entitlements(Tier.PRO)` inclui `trading_master=True`.
- Sem criar tier novo: **pago = `Tier.PRO` (`is_pro`)**. Consistente com o modelo
  atual do `LicenseManager`.

### 4.2 Definições — `ui/settings_dlg.py` (painel 6 Trading)
- Guardar referência `self._license_mgr` no `__init__` (igual ao `license_mgr` já recebido).
- Checkbox "Mostrar o botão 'Modo Trading Master'…" passa a usar `_pro_checkbox("trading_master", …)`:
  em FREE fica desativada, com sufixo `[PRO]` e tooltip de upgrade (padrão existente).
- Editor de combos TV (`_tv_combos_edit`) e respetivo hint: **desativados** em FREE.
- Estado FREE mostra linha de venda com botão **"SUBSCREVER TRADING MASTER (€149,90)"**
  que chama `self._license_mgr.open_checkout("trading_master", vendor_id)` com o
  mesmo `vendor_id` usado em `ui/license_dlg.py` (`PADDLE_VENDOR_ID`); se falhar,
  toast/info "consulta o separador UPGRADE".
- Em PRO: sem badge de bloqueio, editor ativo, sem botão de venda.
- Strings seguem o padrão atual do painel (PT direto, como os restantes painéis).

### 4.3 Janela principal — `ui/main_window.py`
- No topo de `_toggle_trading_master(checked)`:
  ```python
  if self._view_license_locked("trading_master"):
      self._tv_btn.set_on(False)
      self._flash_locked("TRADING MASTER é PRO — UPGRADE PRO")
      return
  ```
  - Cobre a tecla `T` e o clique no botão TV (ambos passam por `_toggle_trading_master`).
  - Sem `save_settings` e sem `_open_tradingview` em FREE.
- `Key_T` mantém `setChecked` → `toggled` → gate (o `setChecked(False)` do gate
  repõe o estado visual).

### 4.4 Arranque — `main.py` (defesa em profundidade)
- Junto dos gates já existentes (`snap`, `voice`, `tts`):
  ```python
  cfg.trading_master_enabled = cfg.trading_master_enabled and not is_pro_locked(lic_.tier, "trading_master")
  cfg.tv_button_enabled      = cfg.tv_button_enabled and not is_pro_locked(lic_.tier, "trading_master")
  ```
- Redação só em runtime (não reescreve `settings.json`), padrão já usado.

## 5. Parte 3 — Pause ON/OFF circular (Task 8)

Novo módulo `ui/pause_toggle.py`, auto-contido e testável.

### 5.1 API
```python
class PauseToggle(QPushButton):
    def __init__(self, parent=None, size=52): ...
    def set_paused(self, paused: bool)   # ON quando not paused
```

### 5.2 Aspeto e animação
- Círculo moderno e simples (~52 px) com dois estados visuais:
  - **ON** (a correr): preenchido com `ACCENT`, texto `ON` (reusa `tr("btn.on")`),
    glow a respirar (`breathe_glow` com `ACCENT_GLOW`), fontes/arredondado do tema.
  - **OFF** (pausado): contorno escuro do tema, texto `OFF` (reusa `tr("btn.off")`),
    sem glow.
- Ao trocar de estado (clique ou `set_paused`): animação curta de escala/pulso
  (~150 ms, `OutCubic`) — o círculo respira no momento do toggle.
- `set_paused(paused)`: atualiza texto/estilo/glow; pode ser chamado em qualquer
  altura (sincronização do motor, tecla `Espaço`, tray).

### 5.3 Integração em `ui/main_window.py`
- Remover `btn_pause` do `MenuPanel` (`ui/menu_panel.py:132`, `:135-138`) e todas
  as referências em `main_window.py`: connect (`:235`), lista `_menu_checkable`
  (`:244`) e `set_key` (`:321` e `:376`).
- Criar `self._pause_toggle = PauseToggle(central)`; `clicked` → `_toggle_pause`.
- Posição: **centro-inferior** (centrado em X, afastado ~24 px do fundo) sobre o
  central, abaixo do logo/background; recalculada em `resizeEvent`.
- `_update_paused_state` e `_sync_toolbar` passam a atualizar
  `self._pause_toggle.set_paused(paused)`.
- A tecla `Espaço` e o tray mantêm `_toggle_pause` (inalterados).

## 6. Testes

| Ficheiro | O quê |
|---|---|
| `tests/test_tune_slider.py` (novo) | API (`value`/`setValue`/`setRange`); tween termina no valor formatado correto (com `tween_ms` pequeno + loop `app.processEvents`); novo `setValue` durante tween não salta; glow aplicado após `setValue` (tem `QGraphicsDropShadowEffect`); press→release aplica/faz fade (efeito presente). |
| `tests/test_settings_trading_pro.py` (novo) | Dialogs FREE vs PRO: FREE → checkbox desativado com `[PRO]` no texto e botão de subscrição presente; PRO → checkbox ativo, editor ativo, sem botão de venda. |
| `tests/test_licensing.py` | Novo assert: `PRO_LOCKED` contém `trading_master`; `is_pro_locked(FREE, trading_master)` verdadeiro. |
| `tests/test_pause_toggle.py` (novo) | `set_paused(False)` mostra texto "ON" e tem `QGraphicsDropShadowEffect` ativo (glow); `set_paused(True)` mostra "OFF" e efeito sem glow; clique alterna (toggle chama `_toggle_pause` via sinal). |

Fixture das UI: `QApplication` offscreen (padrão de `tests/test_license_dialog_free_ui.py`);
cfg de teste com tier do licenciamento falso. Não tocar em `settings.json`/store reais.
Verificação local obrigatória: suite completa com venv, 0 falhas.

## 7. Fora de âmbito / notas

- Não se altera a grelha de produtos nem o flow de checkout existente
  (vendor real continua `TODO(producao)` — mantém o `PADDLE_VENDOR_ID`/URL atual).
- Não se cria painel/slider novo para autotune nem preview de vídeo.
- `_slider_block` removido; `temp_baseline_ref.py` (untracked, baseline) fica fora
  dos commits.
- O botão ON/OFF abandonado no menu (recurso antigo `btn.on`/`btn.off` mantém-se
  nas traduções; sem limpeza das chaves neste trabalho).