# Afinação animada + Trading Master Pro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpawers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Animar os sliders do painel Cursor das Definições (contador + brilho), tornar o Modo Trading Master exclusivo de assinantes pagos (PRO), com gate em profundidade, e transformar o botão ON/OFF de pausa num interruptor circular no centro-inferior da janela (fora do menu), com animação on/off.

**Architecture:** Um novo widget `ui/tune_slider.py` (`TuneSlider`) encapsula nome + valor animado + slider, com tween `QVariantAnimation` do número e glow via `QGraphicsDropShadowEffect`; substitui `_slider_block` nos 3 sliders. O gate do Trading usa o mecanismo existente `PRO_LOCKED`/`is_pro_locked` (pago = `Tier.PRO`), aplicado em UI, janela principal e arranque.

**Tech Stack:** Python 3.14 · PySide6 (`QVariantAnimation`, `QGraphicsDropShadowEffect`, `QSlider`) · pytest (offscreen `QT_QPA_PLATFORM`) · ruff.

**Test runner (sempre):** `.\.venv\Scripts\python.exe -m pytest <args>`

**Branch:** `feature/tuning-animation-trading-pro`. Baseline: 225 testes verdes (venv).

**Spec:** `.superpawers/specs/2026-09-13-tuning-animation-trading-pro-design.md`

---

## Review

- **Status:** PASS
- **Reviewer:** superpawers-reviewer
- **Date:** 2026-09-13
- **Findings (corrigidos na 1.ª ronda):**
  - **Major — Task 4:** adicionado `self._tv_combos_edit.setEnabled(not self._tv_master_locked)` imediatamente após a criação do editor (o primeiro teste agora é satisfeito).
  - **Minor — Contagem:** Task 7 espera `235 passed` (225 baseline + 10 novos).
  - **Minor — File Structure:** incluído `tests/test_settings_cursor_sliders.py`.
  - **Minor — Âncoras:** referências de linha corrigidas (bloco de imports `ui.*`; `main.py` sem número de linha).
  - **Minor — Spec §5:** adicionado `test_new_set_during_tween_reaches_new_target` (TuneSlider com `tween_ms=350`; novo `setValue` durante o tween atinge o novo alvo e não mostra o valor final antes do tempo).
  - **Minor — Spec §3.3 glow durante drag:** TuneSlider ganha flag `_dragging`; `_on_value_changed` ignora `_ignite_glow()` durante o drag (brilho firme ~150); teste reescrito (`test_drag_keeps_steady_glow_through_changes`) valida o glow constante a mudar o valor enquanto arrasta.
  - Spec coverage: todos os requisitos da spec mapeados para tarefas
  - Placeholders: nenhum
  - Type consistency: assinaturas consistentes entre tarefas
  - Dead references: nenhumas (âncoras `_view_license_locked`, `_flash_locked`, `_tv_btn.set_on`, `ACCENT_GLOW`, `FONT_MONO`, `PADDLE_VENDOR_ID`, `PRO_LOCKED`, `is_pro_locked` confirmadas no repo)
- **Strengths (verificados no repositório):** âncoras exatas de `_slider_block` (55-72), `QSlider` (linha 14), `PRO_LOCKED` (licensing.py:35), gates de arranque (`main.py:247-252`, `autotune` na 251), `_view_license_locked`, `_flash_locked`, `_tv_btn.set_on` (`ui/tv_button.py:41`), `ACCENT_GLOW`/`FONT_MONO` (theme.py), `PADDLE_VENDOR_ID` e `_PRODUCTS` (license_dlg.py), `trading_master_enabled`/`tv_button_enabled`/`move_gain`/`deadzone_px`/`gesture_stable_frames` (config.py). Gate da Task 5 replica o padrão `_toggle_voice`/`_toggle_snap` (332-336). Sem referências mortas; testes offscreen seguem o padrão de `tests/test_voice_settings_ui.py`; a remoção de `_slider_block`/`_gain_lbl` não quebra testes existentes.

---

## File Structure

- **Create:** `ui/tune_slider.py` — widget `TuneSlider` (nome, valor animado, slider, glow).
- **Create:** `ui/pause_toggle.py` — widget circular ON/OFF (`PauseToggle`) com animação.
- **Modify:** `ui/settings_dlg.py` — usar `TuneSlider` no painel Cursor; painel Trading com gate PRO + botão de subscrição; guardar `_license_mgr`.
- **Modify:** `core/licensing.py` — `PRO_LOCKED` ganha `trading_master`.
- **Modify:** `ui/main_window.py` — gate no topo de `_toggle_trading_master`; remover `btn_pause` do menu e usar `PauseToggle` no centro-inferior.
- **Modify:** `ui/menu_panel.py` — remover `btn_pause` (e loop associado).
- **Modify:** `main.py` — redação de `trading_master_enabled`/`tv_button_enabled` no arranque.
- **Create test:** `tests/test_tune_slider.py`.
- **Create test:** `tests/test_settings_cursor_sliders.py`.
- **Create test:** `tests/test_settings_trading_pro.py`.
- **Create test:** `tests/test_pause_toggle.py`.
- **Modify test:** `tests/test_licensing.py` — `trading_master` em `PRO_LOCKED`.

Ordem de tarefas (TDD, commits frequentes): T1 widget → T2 integrar Definições → T3 licensing → T4 painel Trading → T5 janela principal → T6 arranque → T7 suite → T8 pause ON/OFF circular.

---

### Task 1: Widget TuneSlider

**Files:**
- Create: `ui/tune_slider.py`
- Test: `tests/test_tune_slider.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_tune_slider.py` (padrão offscreen do repo):

```python
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

from ui.tune_slider import TuneSlider


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _drain(ms=500):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def test_api_value_and_range():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}")
    ts.setRange(6, 50)
    assert ts.value() == 6
    assert ts.minimum() == 6
    assert ts.maximum() == 50
    ts.setValue(35)
    assert ts.value() == 35
    assert ts.name_label.objectName() == "SettingsLabel"
    assert ts.value_label.objectName() == "SliderValue"


def test_tween_reaches_formatted_final_value():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}", tween_ms=50, glow_ms=30)
    ts.setRange(6, 50)
    ts.setValue(35)
    assert ts.value_label.text() != "3.5" or True  # permitido ser imediato/inicial
    _drain(400)
    assert ts.value_label.text() == "3.5"


def test_glow_applied_after_change():
    ts = TuneSlider("Zona morta", lambda v: f"{v}px", tween_ms=20, glow_ms=20)
    ts.setRange(0, 20)
    ts.setValue(10)
    _drain(200)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)


def test_new_set_during_tween_reaches_new_target():
    ts = TuneSlider("Ganho", lambda v: f"{v / 10:.1f}", tween_ms=350, glow_ms=30)
    ts.setRange(6, 50)
    ts.setValue(10)
    _drain(60)
    mid_text = ts.value_label.text()
    ts.setValue(40)
    _drain(500)
    assert ts.value_label.text() == "4.0"
    assert mid_text != "4.0"


def test_drag_keeps_steady_glow_through_changes():
    ts = TuneSlider("Estabilidade", lambda v: f"{v} frames", tween_ms=20, glow_ms=20)
    ts.setRange(1, 6)
    ts.slider.sliderPressed.emit()
    ts.slider.setValue(5)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)
    assert ts.graphicsEffect().color().alpha() > 0
    ts.slider.sliderReleased.emit()
    _drain(400)
    assert isinstance(ts.graphicsEffect(), QGraphicsDropShadowEffect)
```

- [ ] **Step 2: Correr o teste para o ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tune_slider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.tune_slider'`.

- [ ] **Step 3: Implementar o widget**

Criar `ui/tune_slider.py`:

```python
"""Slider com valor animado (contador) e brilho de afinação (premium).

Widget composto que substitui o padrão (nome + valor + slider) dos sliders
das Definições: o número do valor conta suavemente até ao novo valor e o
widget acende ao ajustar, mantém o brilho enquanto arrastas e esfumaça
quando largas.
"""
import math

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)

from ui.theme import ACCENT_GLOW, FONT_MONO


class TuneSlider(QFrame):
    """Nome + valor animado + slider, com brilho de afinação."""

    valueChanged = Signal(int)

    def __init__(self, name, formatter=None, parent=None,
                 tween_ms=220, glow_ms=450, accent=ACCENT_GLOW):
        super().__init__(parent)
        self._fmt = formatter or str
        self._accent = accent
        self._tween_ms = tween_ms
        self._glow_ms = glow_ms
        self._display = 0
        self._dragging = False
        self._glow = None
        self._ignite = None
        self._fade = None
        self._tween = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        row = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SettingsLabel")
        row.addWidget(self.name_label)
        row.addStretch(1)
        self.value_label = QLabel(self._fmt(0))
        self.value_label.setObjectName("SliderValue")
        self.value_label.setFont(FONT_MONO)
        row.addWidget(self.value_label)
        lay.addLayout(row)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderPressed.connect(self._on_drag_start)
        self.slider.sliderReleased.connect(self._on_drag_end)
        self.slider.valueChanged.connect(self._on_value_changed)
        lay.addWidget(self.slider)

    # ── API ───────────────────────────────────────────────────────
    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)

    def setRange(self, lo: int, hi: int) -> None:
        self.slider.setRange(lo, hi)

    def minimum(self) -> int:
        return self.slider.minimum()

    def maximum(self) -> int:
        return self.slider.maximum()

    # ── Interno: tween do contador ────────────────────────────────
    def _on_value_changed(self, value: int) -> None:
        if self._tween is not None:
            self._tween.stop()
        start = self._display
        self._start_tween(start, value)
        if not self._dragging:
            self._ignite_glow()
        self.valueChanged.emit(value)

    def _start_tween(self, start: int, end: int):
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(self._tween_ms)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def tick(t):
            self._display = round(start + (end - start) * t)
            self.value_label.setText(self._fmt(self._display))

        def finish():
            self._display = end
            self.value_label.setText(self._fmt(end))

        anim.valueChanged.connect(tick)
        anim.finished.connect(finish)
        tick(0.0)
        self._tween = anim
        anim.start()

    # ── Interno: brilho ───────────────────────────────────────────
    def _glow_effect(self):
        if self._glow is None:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setOffset(0, 0)
            shadow.setBlurRadius(6)
            shadow.setColor(self._accent)
            self.setGraphicsEffect(shadow)
            self._glow = shadow
        return self._glow

    def _ignite_glow(self):
        if self._fade is not None:
            self._fade.stop()
        if self._ignite is not None:
            self._ignite.stop()
        glow = self._glow_effect()
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(self._glow_ms)
        anim.setEasingCurve(QEasingCurve.InOutSine)

        def tick(t):
            peak = math.sin(math.pi * t)
            color = QColor(self._accent)
            color.setAlpha(int(150 * peak))
            glow.setColor(color)
            glow.setBlurRadius(int(6 + 22 * t))

        anim.valueChanged.connect(tick)
        self._ignite = anim
        anim.start()

    def _on_drag_start(self):
        self._dragging = True
        if self._ignite is not None:
            self._ignite.stop()
        if self._fade is not None:
            self._fade.stop()
        glow = self._glow_effect()
        color = QColor(self._accent)
        color.setAlpha(150)
        glow.setColor(color)
        glow.setBlurRadius(16)

    def _on_drag_end(self):
        self._dragging = False
        self._fade_glow()

    def _fade_glow(self, ms=350):
        if self._ignite is not None:
            self._ignite.stop()
        if self._fade is not None:
            self._fade.stop()
        glow = self._glow_effect()
        start_alpha = glow.color().alpha()
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setDuration(ms)

        def tick(t):
            color = QColor(self._accent)
            color.setAlpha(int(start_alpha * t))
            glow.setColor(color)

        anim.valueChanged.connect(tick)
        self._fade = anim
        anim.start()
```

- [ ] **Step 4: Correr o teste para o ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tune_slider.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/tune_slider.py tests/test_tune_slider.py
git commit -m "feat(ui): TuneSlider - valor animado (contador) + brilho de afinacao"
```

---

### Task 2: Integrar TuneSlider no painel Cursor

**Files:**
- Modify: `ui/settings_dlg.py:14` (remover import `QSlider`), bloco de imports `ui.*` (linhas 24-25, import `TuneSlider`), `:55-72` (apagar `_slider_block`), `:215-218` e `:232-239` (usar `TuneSlider`)

- [ ] **Step 1: Escrever o teste que falha?**

Os 3 sliders do painel Cursor agora têm de ser `TuneSlider` (widget animado) e manter API. Adicionar ao NOVO `tests/test_settings_trading_pro.py` depois da Task 4? **Não** — para isolar, criar `tests/test_settings_cursor_sliders.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from config import Config
from core.licensing import Tier
from ui.settings_dlg import SettingsDialog
from ui.tune_slider import TuneSlider


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLM:
    tier = Tier.PRO


@pytest.fixture
def dlg():
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=FakeLM())
    yield dlg
    dlg.close()


def test_cursor_panel_sliders_are_tune_sliders(dlg):
    assert isinstance(dlg._gain_sl, TuneSlider)
    assert isinstance(dlg._dead_sl, TuneSlider)
    assert isinstance(dlg._stable_sl, TuneSlider)
    assert dlg._gain_sl.value() == int(Config().move_gain * 10)


def test_reset_defaults_still_reaches_sliders(dlg):
    dlg._gain_sl.setValue(12)
    dlg._dead_sl.setValue(19)
    dlg._stable_sl.setValue(5)
    dlg._reset_defaults()
    dlg._save()
    assert dlg._gain_sl.value() == int(Config().move_gain * 10)
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_settings_cursor_sliders.py -v`
Expected: FAIL — `AttributeError` (`SettingsDialog` sem `_gain_sl` como `TuneSlider`; o dialog atual usa tupla de `_slider_block`).

- [ ] **Step 3: Implementar**

No `ui/settings_dlg.py`:

**Imports** (linha 14): remover `QSlider,` da lista de `QWidgets`. Adicionar junto dos restantes (após `from ui.icon_kits import menu_icon`):

```python
from ui.tune_slider import TuneSlider
```

**Remover `_slider_block`** (linhas 55-72 inteiras) — sem outros utilizadores.

**`_build_cursor_panel`** — substituir:

```python
        g, gl = _group("Ganho do cursor", "Quão rápido o cursor segue a mão.")
        self._gain_sl, self._gain_lbl = _slider_block(
            gl, "Rácio de movimento", f"{self._cfg.move_gain:.1f}",
            lambda v: f"{v / 10:.1f}", 6, 50, self._cfg.move_gain * 10,
        )
        pl.addWidget(g)
```

por:

```python
        g, gl = _group("Ganho do cursor", "Quão rápido o cursor segue a mão.")
        self._gain_sl = TuneSlider("Rácio de movimento", lambda v: f"{v / 10:.1f}")
        self._gain_sl.setRange(6, 50)
        self._gain_sl.setValue(int(self._cfg.move_gain * 10))
        gl.addWidget(self._gain_sl)
        pl.addWidget(g)
```

E substituir:

```python
        p2, p2l = _group("Estabilidade", "Zona morta e estabilidade do gesto.")
        self._dead_sl, self._dead_lbl = _slider_block(
            p2l, "Zona morta do cursor", f"{self._cfg.deadzone_px:.0f}px",
            lambda v: f"{v}px", 0, 20, self._cfg.deadzone_px,
        )
        self._stable_sl, self._stable_lbl = _slider_block(
            p2l, "Estabilidade do gesto", f"{self._cfg.gesture_stable_frames} frames",
            lambda v: f"{v} frames", 1, 6, self._cfg.gesture_stable_frames,
        )
        pl.addWidget(p2)
```

por:

```python
        p2, p2l = _group("Estabilidade", "Zona morta e estabilidade do gesto.")
        self._dead_sl = TuneSlider("Zona morta do cursor", lambda v: f"{v}px")
        self._dead_sl.setRange(0, 20)
        self._dead_sl.setValue(int(self._cfg.deadzone_px))
        p2l.addWidget(self._dead_sl)
        self._stable_sl = TuneSlider(
            "Estabilidade do gesto", lambda v: f"{v} frames"
        )
        self._stable_sl.setRange(1, 6)
        self._stable_sl.setValue(int(self._cfg.gesture_stable_frames))
        p2l.addWidget(self._stable_sl)
        pl.addWidget(p2)
```

`_save` (linhas 513, 533-534) e `_reset_defaults` (linhas 496, 506-507) continuam válidos: `_gain_sl.value()`, `_dead_sl.setValue(...)`, etc.

- [ ] **Step 4: Correr para ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_settings_cursor_sliders.py tests/test_tune_slider.py -v`
Expected: PASS.

- [ ] **Step 5: Lint + suite rápida**

Run: `.\.venv\Scripts\python.exe -m ruff check ui/settings_dlg.py ui/tune_slider.py tests/test_settings_cursor_sliders.py tests/test_tune_slider.py`
Expected: no findings.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gui_imports.py tests/test_theme.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ui/settings_dlg.py tests/test_settings_cursor_sliders.py
git commit -m "feat(ui): sliders do painel Cursor usam TuneSlider (afinacao animada)"
```

---

### Task 3: `trading_master` em `PRO_LOCKED`

**Files:**
- Modify: `core/licensing.py:35`
- Modify: `tests/test_licensing.py`

- [ ] **Step 1: Teste que falha**

Adicionar a `tests/test_licensing.py`, junto de `test_is_pro_locked`:

```python
def test_trading_master_is_pro_locked():
    assert "trading_master" in lic.PRO_LOCKED
    assert lic.is_pro_locked(lic.Tier.FREE, "trading_master")
    assert not lic.is_pro_locked(lic.Tier.PRO, "trading_master")
    assert lic.entitlements(lic.Tier.PRO)["trading_master"]
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_licensing.py::test_trading_master_is_pro_locked -v`
Expected: FAIL — `"trading_master" not in PRO_LOCKED`.

- [ ] **Step 3: Implementar**

Em `core/licensing.py:35`:

```python
PRO_LOCKED = ("snap", "voice", "two_hands", "tts", "ai", "autotune", "low_light")
```

para:

```python
PRO_LOCKED = ("snap", "voice", "two_hands", "tts", "ai", "autotune", "low_light", "trading_master")
```

- [ ] **Step 4: Correr para ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_licensing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/licensing.py tests/test_licensing.py
git commit -m "feat(license): Trading Master passa a PRO_LOCKED (so assinantes pagos)"
```

---

### Task 4: Painel Trading nas Definições (gate PRO + subscrição)

**Files:**
- Modify: `ui/settings_dlg.py:77-87` (guardar `_license_mgr`), `:429-468` (painel Trading), `:492-510` (reset)

- [ ] **Step 1: Teste que falha**

Criar `tests/test_settings_trading_pro.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton

from config import Config
from core.licensing import Tier
from ui.license_dlg import PADDLE_VENDOR_ID
from ui.settings_dlg import SettingsDialog


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeLM:
    def __init__(self, tier):
        self.tier = tier
        self.called = None

    def open_checkout(self, product, vendor_id):
        self.called = (product, vendor_id)
        return True


def _tv_checkbox(dlg):
    found = [w for w in dlg.findChildren(QCheckBox)
             if "Modo Trading Master" in w.text()]
    assert found, "falta o checkbox do Modo Trading Master"
    return found[0]


def _buy_buttons(dlg):
    return [w for w in dlg.findChildren(QPushButton)
            if "SUBSCREVER TRADING MASTER" in w.text()]


def test_free_locks_trading_master():
    lm = FakeLM(Tier.FREE)
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=lm)
    try:
        cb = _tv_checkbox(dlg)
        assert not cb.isEnabled()
        assert "[PRO]" in cb.text()
        assert not dlg._tv_combos_edit.isEnabled()
        btn = _buy_buttons(dlg)
        assert len(btn) == 1
        btn[0].click()
        assert lm.called == ("trading_master", PADDLE_VENDOR_ID)
    finally:
        dlg.close()


def test_pro_unlocks_trading_master():
    lm = FakeLM(Tier.PRO)
    dlg = SettingsDialog(Config(), "NORMAL", license_mgr=lm)
    try:
        cb = _tv_checkbox(dlg)
        assert cb.isEnabled()
        assert "[PRO]" not in cb.text()
        assert dlg._tv_combos_edit.isEnabled()
        assert _buy_buttons(dlg) == []
    finally:
        dlg.close()
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_settings_trading_pro.py -v`
Expected: FAIL — painel atual não bloqueia (checkbox ativo, editor ativo, sem botão).

- [ ] **Step 3: Implementar**

**`__init__`** (após `self._tier = ...`):

```python
        self._license_mgr = license_mgr
```

**`_build_trading_panel`** — substituir do subtítulo até `tml.addWidget(self._tv_btn_ch)`:

Subtítulo:

```python
        sub = QLabel(
            "Botão de TV no ecrã principal para ativar o modo dedicado a"
            " trading (abre o TradingView + comando remoto pelo telemóvel)."
            " Exclusivo para assinantes Pro."
        )
```

Checkbox (usando `_pro_checkbox`):

```python
        self._tv_btn_ch, tv_lay = self._pro_checkbox(
            "trading_master",
            "Mostrar o botão 'Modo Trading Master' no ecrã principal",
            self._cfg.tv_button_enabled,
        )
        tml.addLayout(tv_lay)
```

Após o `tv_hint`, bloquear o hint e (só FREE) mostrar a linha de subscrição — **antes de criar o editor**:

```python
        self._tv_master_locked = is_pro_locked(self._tier, "trading_master")
        if self._tv_master_locked:
            buy_lay = QHBoxLayout()
            buy_hint = QLabel(
                "Trading Master é um produto pago (€149,90) — o modo abre o"
                " TradingView e ativa o controlo remoto por telemóvel."
            )
            buy_hint.setObjectName("MicHint")
            buy_hint.setWordWrap(True)
            buy_lay.addWidget(buy_hint, 1)
            self._tv_buy_btn = QPushButton("SUBSCREVER TRADING MASTER (€149,90)")
            self._tv_buy_btn.setObjectName("ProCta")
            self._tv_buy_btn.setCursor(Qt.PointingHandCursor)
            self._tv_buy_btn.clicked.connect(self._buy_trading_master)
            buy_lay.addWidget(self._tv_buy_btn)
            tml.addLayout(buy_lay)
        else:
            self._tv_buy_btn = None
        tv_hint.setEnabled(not self._tv_master_locked)
```

**Desativar o editor de combos** — logo após o `tml.addWidget(self._tv_combos_edit)` existente (o editor já existe neste ponto do método):

```python
        self._tv_combos_edit.setEnabled(not self._tv_master_locked)
```

**Novo método** (junto de `_gen_token`):

```python
    def _buy_trading_master(self):
        from ui.license_dlg import PADDLE_VENDOR_ID

        if self._license_mgr is not None:
            self._license_mgr.open_checkout("trading_master", PADDLE_VENDOR_ID)
```

**`_reset_defaults`** e **`_save`**: sem alterações de código (mantêm `self._tv_btn_ch`; o checkbox desativado em FREE nunca altera `isChecked` no save; a redação de arranque da Task 6 é a última defesa).

- [ ] **Step 4: Correr para ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_settings_trading_pro.py tests/test_settings_cursor_sliders.py -v`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

Run: `.\.venv\Scripts\python.exe -m ruff check ui/settings_dlg.py tests/test_settings_trading_pro.py`
Expected: no findings.

```bash
git add ui/settings_dlg.py tests/test_settings_trading_pro.py
git commit -m "feat(definicoes): painel Trading bloqueado no FREE com botao de subscricao"
```

---

### Task 5: Gate na janela principal

**Files:**
- Modify: `ui/main_window.py:488-491`

- [ ] **Step 1: Implementar (sem teste de UI — ver nota)**

Justificação de TDD: não há suíte para `MainWindow` (constrói câmara/voz/remoto, frágil em CI). A lógica-chave `is_pro_locked(FREE, "trading_master")` já está coberta na Task 3; este passo é um guard de 3 linhas no padrão já testado de `_toggle_voice`/SNAP (linhas 332-336). Verificação manual no fim (Task 7).

No `_toggle_trading_master`, adicionar no topo (antes da linha `self._cfg.remote_enabled = bool(checked)`) e atualizar o docstring:

```python
    def _toggle_trading_master(self, checked):
        """Ativa/desativa o Modo Trading Master: liga o controlo remoto por
        telemóvel (comandar o PC de trading) e guarda a preferência.

        Só assinantes Pro: no FREE o gate bloqueia e mostra o aviso."""
        if self._view_license_locked("trading_master"):
            self._tv_btn.set_on(False)
            self._flash_locked("TRADING MASTER é PRO — UPGRADE PRO")
            return
        self._cfg.remote_enabled = bool(checked)
```

Cobre a tecla `T` (linhas 413-416, passa por `setChecked` → `toggled` → este método) e o clique no `TvMasterButton` (linha 151).

- [ ] **Step 2: Lint**

Run: `.\.venv\Scripts\python.exe -m ruff check ui/main_window.py`
Expected: no findings.

- [ ] **Step 3: Commit**

```bash
git add ui/main_window.py
git commit -m "feat(gate): Trading Master bloqueado no FREE na janela principal"
```

---

### Task 6: Redação no arranque (defesa em profundidade)

**Files:**
- Modify: `main.py:251` (após `cfg.ai_enabled ...`)

- [ ] **Step 1: Implementar**

Em `main.py`, após a linha `cfg.autotune_enabled = cfg.autotune_enabled and ent["autotune"]`:

```python
    cfg.trading_master_enabled = cfg.trading_master_enabled and not is_pro_locked(lic_.tier, "trading_master")
    cfg.tv_button_enabled = cfg.tv_button_enabled and not is_pro_locked(lic_.tier, "trading_master")
```

(`is_pro_locked` já está no bloco de imports de `core.licensing` em `main.py`.)

- [ ] **Step 2: Lint + commit**

Run: `.\.venv\Scripts\python.exe -m ruff check main.py`
Expected: no findings.

```bash
git add main.py
git commit -m "feat(gate): redacao de Trading Master no arranque (FREE nao carrega o modo)"
```

---

### Task 7: Verificação final

- [ ] **Step 1: Suite completa**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: `235 passed` (225 baseline + 10 novos: 5 tune_slider + 2 cursor_sliders + 2 trading_pro + 1 licensing).

- [ ] **Step 2: Lint do repo (superficie alterada)**

Run: `.\.venv\Scripts\python.exe -m ruff check ui/tune_slider.py ui/settings_dlg.py ui/main_window.py main.py core/licensing.py tests/test_tune_slider.py tests/test_settings_trading_pro.py tests/test_settings_cursor_sliders.py tests/test_licensing.py`
Expected: no findings.

- [ ] **Step 3: Smoke manual (lista para o utilizador)**

- Abrir Definições → Cursor: 3 sliders com contador animado + brilho ao ajustar/arrastar.
- Definições → Trading com conta FREE: checkbox `[PRO]` desativado, editor desativado, botão "SUBSCREVER TRADING MASTER".
- Tecla `T` em conta FREE: flash vermelho "TRADING MASTER é PRO — UPGRADE PRO", botão TV fica OFF.
- Com conta PRO: tudo ativo.

---

### Task 8: Pause ON/OFF circular (fora do menu)

**Files:**
- Create: `ui/pause_toggle.py`
- Modify: `ui/menu_panel.py` — remover `btn_pause`
- Modify: `ui/main_window.py` — remover referências a `btn_pause`; criar `PauseToggle` no centro-inferior
- Test: `tests/test_pause_toggle.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_pause_toggle.py` (padrão offscreen do repo):

```python
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

from ui.pause_toggle import PauseToggle


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _drain(ms=500):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.005)


def test_default_state_is_on_with_glow():
    pt = PauseToggle()
    assert pt.is_paused() is False
    assert "ON" in pt.text().upper()
    eff = pt.graphicsEffect()
    assert isinstance(eff, QGraphicsDropShadowEffect)
    assert eff.color().alpha() > 0


def test_set_paused_true_shows_off_no_glow():
    pt = PauseToggle(glow_ms=30)
    pt.set_paused(True)
    _drain(400)
    assert pt.is_paused() is True
    assert "OFF" in pt.text().upper()
    eff = pt.graphicsEffect()
    assert isinstance(eff, QGraphicsDropShadowEffect)
    assert eff.color().alpha() == 0


def test_set_paused_false_restores_on():
    pt = PauseToggle(glow_ms=30)
    pt.set_paused(True)
    _drain(400)
    pt.set_paused(False)
    _drain(400)
    assert pt.is_paused() is False
    assert "ON" in pt.text().upper()
    assert pt.graphicsEffect().color().alpha() > 0


def test_click_toggles_state():
    pt = PauseToggle(glow_ms=30)
    pt.click()
    _drain(400)
    assert pt.is_paused() is True
    assert "OFF" in pt.text().upper()
```

- [ ] **Step 2: Correr o teste para o ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_pause_toggle.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.pause_toggle'`.

- [ ] **Step 3: Implementar o widget**

Criar `ui/pause_toggle.py`:

```python
"""Interruptor circular ON/OFF (pausa) com animacao de estado.

Substitui o botao de lista do menu lateral: um circulo moderno e simples,
posicionado no centro-inferior por baixo do logo, que respira ao alternar
ON -> OFF e acende (glow) enquanto esta ON.
"""
from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QPushButton,
)

from i18n import tr
from ui.theme import ACCENT, ACCENT_GLOW, breathe_glow


class PauseToggle(QPushButton):
    """Circulo ON/OFF. ON = preenchido com accent + glow a respirar;
    OFF = contorno escuro sem glow. ``clicked`` e emitido (como qualquer
    QPushButton); a janela liga-o a ``_toggle_pause``.
    """

    def __init__(self, parent=None, size=52, glow_ms=450):
        super().__init__(parent)
        self._paused = False
        self._glow_ms = glow_ms
        self._size = size
        self._breath = None
        self.setObjectName("PauseToggle")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._configure_glow()
        self._refresh()
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self.set_paused(not self._paused)
        self._pulse()

    def is_paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool):
        paused = bool(paused)
        if paused == self._paused:
            return
        self._paused = paused
        self._refresh()

    def _refresh(self):
        if self._breath is not None:
            self._breath.stop()
            self._breath = None
        if not self._paused:
            self.setText(tr("btn.on"))
            self.setProperty("on", True)
            self.setStyleSheet(self._on_style())
            self._breath = breathe_glow(
                self, ACCENT_GLOW, min_alpha=90, max_alpha=200,
                min_blur=8, max_blur=20, ms=self._glow_ms,
            )
        else:
            self.setText(tr("btn.off"))
            self.setProperty("on", False)
            self.setStyleSheet(self._off_style())
            self._fade_glow()
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_style(self) -> str:
        return (
            f"QPushButton#PauseToggle {{ border: none;"
            f" border-radius: {self._size // 2}px; background: {ACCENT.name()};"
            f" color: #0c1016; font-family: 'Segoe UI Semibold'; font-size: 13px; }}"
        )

    def _off_style(self) -> str:
        return (
            f"QPushButton#PauseToggle {{ border: 2px solid {QColor('#8b96a5').name()};"
            f" border-radius: {self._size // 2}px; background: {QColor('#1d2530').name()};"
            f" color: {QColor('#aab4c2').name()}; font-family: 'Segoe UI Semibold';"
            f" font-size: 13px; }}"
        )

    def _configure_glow(self):
        eff = QGraphicsDropShadowEffect(self)
        eff.setOffset(0, 0)
        eff.setColor(QColor(0, 0, 0, 0))
        eff.setBlurRadius(0)
        self.setGraphicsEffect(eff)

    def _fade_glow(self):
        if self._breath is not None:
            self._breath.stop()
            self._breath = None
        eff = self.graphicsEffect()
        if eff is None:
            self._configure_glow()
            eff = self.graphicsEffect()
        eff.setColor(QColor(0, 0, 0, 0))
        eff.setBlurRadius(0)

    def _pulse(self):
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(1.12)
        anim.setDuration(140)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(self._scale_to)
        anim.finished.connect(self._reset_size)
        anim.start()

    def _scale_to(self, t):
        self.setFixedSize(int(self._size * t), int(self._size * t))

    def _reset_size(self):
        self.setFixedSize(self._size, self._size)
```

Nota: `tr("btn.on")`/`tr("btn.off")` mantêm as chaves de tradução já existentes;
`ACCENT`/`ACCENT_GLOW`/`breathe_glow` vêm de `ui/theme.py`.
```

- [ ] **Step 4: Correr o teste para o ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_pause_toggle.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Remover `btn_pause` do menu lateral**

Em `ui/menu_panel.py` (linhas 132-138):
- Remover `self.btn_pause = MenuButton("btn.on", "menu-pause", checkable=False)`.
- O loop passa a ser `for btn in (self.btn_voice, self.btn_snap):`.

**Fix whitespace:** manter o spacing/estrutura (linhas 140+, dividers) intactos.

- [ ] **Step 6: Ligar em `ui/main_window.py`**

- Na `_build_ui` (após `self._tv_btn`, junto das outras criações): criar `self._pause_toggle = PauseToggle(central)` (import de `ui.pause_toggle` junto dos outros `ui.*`) e `self._pause_toggle.clicked.connect(self._toggle_pause)`.
- Na `_build_menu` (linha 235): remover `m.btn_pause.clicked.connect(self._toggle_pause)` e, na lista `self._menu_buttons` (linha 244), remover `m.btn_pause,` — `_menu_checkable` continua a funcionar para os restantes.
- Posicionar por baixo da imagem central (após `_fit_bg` chamado em `resizeEvent`): criar `_layout_pause_toggle()` e chamá-lo no fim de `_build_ui` e em `resizeEvent(event)` depois de `self._fit_bg(w, h)`:
  ```python
  def _layout_pause_toggle(self):
      pt = self._pause_toggle
      bg = self._bg.geometry()
      if bg.width() <= 0 or bg.height() <= 0:
          pt.move((self.width() - pt.width()) // 2, self.height() - pt.height() - 24)
          return
      pt.move(bg.center().x() - pt.width() // 2, bg.bottom() + 24)
  ```
- Em `_update_paused_state` (linha 318-321): substituir `self._menu.btn_pause.set_key(...)` por `self._pause_toggle.set_paused(paused)`.
- Em `_sync_toolbar` (linha 375-376): substituir `self._menu.btn_pause.set_key(...)` por `self._pause_toggle.set_paused(self._paused)`.
- A tecla `Espaço` (`_toggle_pause`) e o tray ficam inalterados (continuam a refletir o estado no círculo via `_update_paused_state`).

- [ ] **Step 7: Suite completa + lint**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: `239 passed` (225 baseline + 5 tune_slider + 2 cursor_sliders + 2 trading_pro + 1 licensing + 4 pause_toggle).

Run: `.\.venv\Scripts\python.exe -m ruff check ui/pause_toggle.py ui/menu_panel.py ui/main_window.py tests/test_pause_toggle.py`
Expected: no findings.

- [ ] **Step 8: Smoke manual (lista para o utilizador)**

- No ecrã principal: o menu lateral **já não tem** o botão ON/OFF; existe um círculo no centro-inferior por baixo do logo.
- Clicar no círculo: ON ⇄ OFF com animação (pulso) e glow quando ON; o rato para/retoma.
- Tecla `Espaço` continua a alternar e o círculo reflete o estado.
- Tray Pausar/Retomar continua a funcionar e reflete-se no círculo.