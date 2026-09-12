# Redesign da Área de Subscrição (Etapa A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpawers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernizar o diálogo de licença/subscrição do Mãouse para um estilo premium minimalista (menos densidade, hierarquia clara, tipografia moderna, copy confiante) preservando todo o comportamento.

**Architecture:** Alterações confinadas a `i18n.py` (valores de copy), `ui/theme.py` (novos estilos no `MAIN_STYLESHEET`) e `ui/license_dlg.py` (reconstrução da UI de `LicenseDialog` em modo FREE e PRO). O `breathe_glow` permanece em `ui/theme.py` porque `ui/menu_panel.py` ainda o usa. A ativação/desativação/checkout/trial permanece intacta.

**Tech Stack:** Python 3.10+, PySide6 6.11, pytest (tests headless via `QT_QPA_PLATFORM=offscreen`).

**Ramo:** `feature/license-dialog-modernize` (criado a partir de `feature/libeleq-licence-server-fireproof`; verifica-se o estado em cada passo).

## Review

**Status: PASS** — Todos os problemas críticos e maiores da revisão anterior foram resolvidos. O plano está correto contra o codebase real e cobre todos os requisitos do spec.

### Re-verificação de issues anteriores

1. ✅ `FakeLicense.is_pro` / `FakeProLicense.is_pro` usam `@property` — alinhado com `core/licensing.py:293-295`.
2. ✅ Teste `test_plan_selection_updates_cta_price` deriva plan_id/price de `_PRODUCTS[1]` — sem referências a `subscription` ou `€4,99`.
3. ✅ Teste `test_free_dialog_has_one_plan_card_per_product` assertion é `len(cards) == len(ld._PRODUCTS)` — dinâmico e correto (4 produtos em `_PRODUCTS`).
4. ✅ `has_key` e `activate_key` mantêm-se inalterados; `license.key_hint` adicionada como nova chave com teste em `test_i18n.py`.
5. ✅ `QFrame#PlanCard[selected="true"]` usa seletor QSS válido com `setProperty("selected", ...)` + unpolish/polish.
6. ✅ `QColor` e `breathe_glow` removidos de `license_dlg.py`; `breathe_glow` mantido em `theme.py` (usado por `menu_panel.py`).
7. ✅ `SettingsButtonSecondary` adicionado à lista de tokens em `tests/test_theme.py` (Task 4, Step 1).

### Checklist completo

| Área | Resultado |
|---|---|
| Referências mortas (i18n, tokens, funções) | Todas as chaves existem ou são adicionadas; `breathe_glow` mantido em theme |
| Naming consistente | Object names alinhados entre CSS e Python |
| Metas claras | Cada tarefa com TDD (fail→pass) e asserts explícitos |
| Cobertura do spec | 6 secções do layout FREE + PRO + tipografia + `BlockDialog` intocada |
| Ordem estrutural | i18n → theme → FREE → PRO → verificação — dependências corretas |
| Placeholders | Nenhum resolvido |
| Correção vs codebase | `_PRODUCTS` (4), `_BENEFITS` (4), `_BenefitRow` signature, `Tier.PRO.value="pro"` — tudo validado |

### Conformidades confirmadas

- Remoção de `breathe_glow` do `license_dlg.py` ✓; `ui/theme.py` mantém a função ✓ (`ui/menu_panel.py:18` ainda a usa)
- `BlockDialog` não é alterado ✓
- Chaves i18n usadas (`license.hero`, `hero_sub`, `unlocks_title`, `cta`, `pro_active_sub`, `remove`, `free_badge`, `trial_remaining`, `key_hint`) existem em `i18n.py` ✓
- `_BenefitRow(name_key, desc_key)` com `_BENEFITS` — assinatura consistente ✓
- Approach offscreen (`QT_QPA_PLATFORM=offscreen`) consistente com PySide6 ✓
- `test_active_license_defaults_to_free` (Task 5) tratado corretamente como falhanço pré-existente ✓

---

### Task 1: Reescrita do copy em `i18n.py`

**Files:**
- Modify: `i18n.py:41-49`
- Test: `tests/test_i18n.py` (existente — verifica presença das chaves)

A suíte não verifica valores, apenas que as chaves existem. Mudamos os valores; chaves mantêm-se.

- [ ] **Step 1: Editar os valores** em `i18n.py:41-49` e adicionar `license.key_hint`

Mudam apenas as chaves abaixo (as restantes — incl. `has_key`, `activate_key` — mantêm-se):

```python
    "license.hero": {"pt": "Uma nova forma de trabalhar com a mão", "en": "A new way to work with your hand"},
    "license.hero_sub": {"pt": "Tudo o que já usa, agora com todo o potencial do Mãouse desbloqueado.", "en": "Everything you already use, now with Mãouse's full potential unlocked."},  # noqa: E501
    "license.unlocks_title": {"pt": "O QUE DESBLOQUEIA", "en": "WHAT YOU UNLOCK"},
    "license.cta": {"pt": "ATIVAR PRO", "en": "ACTIVATE PRO"},
    "license.pro_active_sub": {"pt": "Obrigado por apoiar o Mãouse. Está tudo desbloqueado.", "en": "Thank you for supporting Mãouse. Everything is unlocked."},  # noqa: E501
    "license.remove": {"pt": "Remover licença", "en": "Remove license"},
```

E adicionar, junto das chaves de ativação (após `license.activate_key`, i18n.py:46):

```python
    "license.key_hint": {"pt": "Cole a chave aqui", "en": "Paste the key here"},
```

- [ ] **Step 2: Cobrir a chave nova no teste de i18n**

Em `tests/test_i18n.py:10`, adicionar `"license.key_hint"` à tupla de chaves:

```python
    for key in ("license.trial_remaining", "license.trial_ended",
                "license.trial_ended_sub", "license.activate_now",
                "license.revalidate_failed", "license.ledge_blocked",
                "license.has_key", "license.activate_key", "license.key_hint",
                "license.enter_key", "license.activate_failed",
                "license.needs_connection"):
```

- [ ] **Step 3: Correr o teste de i18n**

Run: `.venv\Scripts\python.exe -m pytest tests\test_i18n.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add i18n.py tests/test_i18n.py
git commit -m "copy(license): copy confiante e conciso + placeholder de chave (Etapa A)"
```

---

### Task 2: Novos estilos em `ui/theme.py`

**Files:**
- Modify: `ui/theme.py` (`MAIN_STYLESHEET`)
- Create: `tests/test_theme.py`

- [ ] **Step 1: Escrever o teste (falhar primeiro)**

Criar `tests/test_theme.py`:

```python
from ui.theme import MAIN_STYLESHEET


def test_stylesheet_has_new_premium_tokens():
    for token in ("StatusChip", "HeroChip", "PlanCard", "PlanPrice",
                  "PlanExtra", "KeyCaption", "KeyField", "BenefitRow"):
        assert token in MAIN_STYLESHEET, f"falta {token} no stylesheet"


def test_stylesheet_removed_old_free_tokens():
    assert "FreeBanner" not in MAIN_STYLESHEET
    assert "FreeBadge" not in MAIN_STYLESHEET


def test_stylesheet_uses_modern_font_fallback_lists():
    assert "Segoe UI Variable Display" in MAIN_STYLESHEET
    assert "Cascadia Code" in MAIN_STYLESHEET
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests\test_theme.py -q`
Expected: FAIL (tokens novos não existem ainda).

- [ ] **Step 3: Implementar os estilos**

Em `ui/theme.py`, dentro de `MAIN_STYLESHEET`, substituir os blocos `QFrame#ProductCard`,
`QLabel#ProductName`, `QLabel#ProductBadge`, `QLabel#ProductPrice`, `QLabel#ProductExtra`,
`QFrame#FreeBanner`, `QLabel#FreeBadge`, `QLabel#FreeSub`, `QLabel#BenefitRow` por:

```css
QFrame#PlanCard {
    background-color: rgba(255,255,255,0.02);
    border: 1px solid #1A1A2E;
    border-radius: 12px;
}
QFrame#PlanCard:hover {
    border-color: #2A3B4A;
}
QFrame#PlanCard[selected="true"] {
    background-color: rgba(80,200,255,0.07);
    border: 1px solid #7DD4FF;
}
QLabel#PlanName {
    color: #F0F4F8;
    font-family: 'Segoe UI Variable Display', 'Segoe UI';
    font-size: 12px;
    font-weight: 600;
}
QLabel#PlanBadge {
    background-color: #FFD766;
    color: #0A0A12;
    border: none;
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'Segoe UI';
    font-size: 9px;
    font-weight: bold;
}
QLabel#PlanPrice {
    color: #FFFFFF;
    font-family: 'Cascadia Code', 'Consolas';
    font-size: 15px;
    font-weight: bold;
}
QLabel#PlanExtra {
    color: #8A9AA6;
    font-family: 'Segoe UI';
    font-size: 10px;
}
QLabel#BenefitRow {
    color: #EAF3F8;
    font-family: 'Segoe UI';
    font-size: 12px;
    background: transparent;
}
QLabel#StatusChip {
    background-color: rgba(255, 214, 102, 0.10);
    color: #FFD766;
    border: 1px solid rgba(255, 214, 102, 0.35);
    border-radius: 6px;
    padding: 3px 10px;
    font-family: 'Segoe UI';
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLabel#HeroChip {
    background-color: #FFD766;
    color: #0A0A12;
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    font-family: 'Segoe UI';
    font-size: 10px;
    font-weight: bold;
}
QLabel#KeyCaption {
    color: #969696;
    font-family: 'Segoe UI';
    font-size: 11px;
}
QLineEdit#KeyField {
    background-color: #12121E;
    color: #F0F4F8;
    border: 1px solid #1A1A2E;
    border-radius: 8px;
    padding: 6px 10px;
    font-family: 'Cascadia Code', 'Consolas';
}
QLineEdit#KeyField:focus {
    border-color: #50C8FF;
}
```

Além disso, editar as font-family de `HeroTitle` e `HeroSubtitle` para listas com fallback:

```css
QLabel#HeroTitle {
    color: #FFFFFF;
    font-family: 'Segoe UI Variable Display', 'Segoe UI';
    font-size: 20px;
    font-weight: bold;
}
QLabel#HeroSubtitle {
    color: #969696;
    font-family: 'Segoe UI Variable Display', 'Segoe UI';
    font-size: 12px;
}
```

- [ ] **Step 4: Correr para passar**

Run: `.venv\Scripts\python.exe -m pytest tests\test_theme.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Regression da i18n + compile**

Run: `.venv\Scripts\python.exe -m pytest tests\test_i18n.py -q` e `.venv\Scripts\python.exe -m py_compile ui\theme.py`
Expected: PASS / OK.

- [ ] **Step 6: Commit**

```bash
git add ui/theme.py tests/test_theme.py
git commit -m "style(license): tokens premium minimalistas no stylesheet (StatusChip/PlanCard/KeyCaption)"
```

---

### Task 3: Reconstrução da UI FREE de `LicenseDialog`

**Files:**
- Modify: `ui/license_dlg.py`
- Create: `tests/test_license_dialog_free_ui.py`

- [ ] **Step 1: Escrever os testes (falhar primeiro)**

Criar `tests/test_license_dialog_free_ui.py`:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QFrame, QGraphicsEffect, QLabel, QLineEdit

from ui import license_dlg as ld
from ui.license_dlg import LicenseDialog


class FakeLicense:
    @property
    def is_pro(self):
        return False

    def trial_remaining_seconds(self):
        return 9 * 60

    def open_checkout(self, product, vendor_id):
        return True

    def activate(self, key):
        return False

    def deactivate(self):
        pass


def _dialog(monkeypatch):
    app = QApplication.instance() or QApplication([])
    cfg = SimpleNamespace(license_tier="free")
    box = []
    monkeypatch.setattr(ld, "QMessageBox", SimpleNamespace(
        warning=lambda *a, **k: box.append("warning"),
        information=lambda *a, **k: box.append("information"),
    ))
    return LicenseDialog(cfg, FakeLicense())


def test_free_dialog_has_status_chip_without_pulse(monkeypatch):
    dlg = _dialog(monkeypatch)
    chips = [c for c in dlg.findChildren(QLabel) if c.objectName() == "StatusChip"]
    assert chips, "StatusChip em falta"
    assert not dlg.findChildren(QGraphicsEffect), "não pode haver efeitos gráficos (pulse) no diálogo FREE"


def test_free_dialog_has_one_plan_card_per_product(monkeypatch):
    dlg = _dialog(monkeypatch)
    cards = [c for c in dlg.findChildren(QFrame) if c.objectName() == "PlanCard"]
    assert len(cards) == len(ld._PRODUCTS)


def test_plan_selection_updates_cta_price(monkeypatch):
    from ui.license_dlg import _ProductCard

    dlg = _dialog(monkeypatch)
    plan_id, _name, price, _extra, _ = ld._PRODUCTS[1]
    card = next(c for c in dlg.findChildren(_ProductCard) if c._plan_id == plan_id)
    card.selected.emit(plan_id)
    assert price in dlg._cta.text()


def test_key_activation_calls_license_and_accepts(monkeypatch):
    dlg = _dialog(monkeypatch)
    dlg._lm.activate = lambda key: key == "ABC-123"
    dlg._key_edit.setText("ABC-123")
    dlg._activate_key()
    assert dlg.result() == dlg.Accepted
    assert dlg._cfg.license_tier == "pro"
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests\test_license_dialog_free_ui.py -q`
Expected: FAIL — `StatusChip`/`PlanCard`/`KeyField` ainda não existem (redesign não implementado).

- [ ] **Step 3: Implementar a UI FREE**

**3a. `_ProductCard`** — substituir a classe inteira (linhas 62-123) por:

```python
class _ProductCard(QFrame):
    """Cartão de plano selecionável."""

    selected = Signal(str)

    def __init__(self, plan_id, name, price, extra, highlight=False, parent=None):
        super().__init__(parent)
        self._plan_id = plan_id
        self._highlight = highlight
        self.setObjectName("PlanCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        top = QHBoxLayout()
        self._name_lbl = QLabel(name.upper())
        self._name_lbl.setObjectName("PlanName")
        top.addWidget(self._name_lbl)
        if highlight:
            badge = QLabel("POPULAR")
            badge.setObjectName("PlanBadge")
            top.addWidget(badge)
        else:
            top.addStretch()
        lay.addLayout(top)

        self._price_lbl = QLabel(price)
        self._price_lbl.setObjectName("PlanPrice")
        lay.addWidget(self._price_lbl)

        self._extra_lbl = QLabel(extra)
        self._extra_lbl.setObjectName("PlanExtra")
        lay.addWidget(self._extra_lbl)

        self._selected = False
        self._refresh_style()

    def set_selected(self, value: bool):
        self._selected = value
        self._refresh_style()

    def _refresh_style(self):
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._plan_id)
        super().mousePressEvent(event)
```

**3b. `_build_free_ui` + `_build_key_row`** — substituir (linhas 165-256) por:

```python
    def _build_free_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 24)
        lay.setSpacing(10)

        # Linha de status FREE — chip discreto, sem pulse/glow.
        status = QHBoxLayout()
        chip = QLabel(f"FREE · {tr('license.free_badge').split('— ')[-1]}")
        chip.setObjectName("StatusChip")
        status.addWidget(chip)
        remaining = self._lm.trial_remaining_seconds()
        if remaining > 0:
            rem = QLabel(tr("license.trial_remaining").format(m=max(1, math.ceil(remaining / 60))))
            rem.setObjectName("KeyCaption")
            status.addWidget(rem)
        status.addStretch()
        lay.addLayout(status)

        # Hero sóbrio.
        hero = QHBoxLayout()
        title = QLabel("Mãouse Pro")
        title.setObjectName("HeroTitle")
        hero.addWidget(title)
        hero.addSpacing(8)
        badge = QLabel("PRO")
        badge.setObjectName("HeroChip")
        hero.addWidget(badge)
        hero.addStretch()
        lay.addLayout(hero)
        sub = QLabel(tr("license.hero_sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # Benefícios compactos.
        lay.addSpacing(2)
        feat_title = QLabel(tr("license.unlocks_title"))
        feat_title.setObjectName("SectionTitle")
        feat_title.setAlignment(Qt.AlignLeft)
        lay.addWidget(feat_title)
        for nk, dk in _BENEFITS:
            lay.addWidget(_BenefitRow(nk, dk))

        # Planos (grelha de 2 colunas, um cartão por produto).
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(10)
        for i, plan in enumerate(_PRODUCTS):
            self._cards_grid.addWidget(self._make_card(plan), i // 2, i % 2)
        lay.addLayout(self._cards_grid)

        # CTA único, sem pulse.
        self._cta = QPushButton(f"{tr('license.cta')} · €39,90")
        self._cta.setObjectName("ProCta")
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.setFixedHeight(44)
        self._cta.clicked.connect(self._on_cta)
        lay.addWidget(self._cta)

        # Chave em modo secundário.
        self._build_key_row(lay)

    def _build_key_row(self, lay):
        divider = QFrame()
        divider.setObjectName("MenuDivider")
        divider.setFixedHeight(1)
        lay.addSpacing(4)
        lay.addWidget(divider)
        caption = QLabel(tr("license.has_key"))
        caption.setObjectName("KeyCaption")
        lay.addWidget(caption)
        key_row = QHBoxLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText(tr("license.key_hint"))
        self._key_edit.setObjectName("KeyField")
        key_row.addWidget(self._key_edit, 1)
        activate = QPushButton(tr("license.activate_key"))
        activate.setObjectName("SettingsButton")
        activate.clicked.connect(self._activate_key)
        key_row.addWidget(activate)
        lay.addLayout(key_row)
```

**3c. `__init__`** (linhas 137-143): trocar a largura FREE de 700 para 620:

```python
        if self._lm.is_pro:
            self.setFixedSize(560, 340)
            self._build_pro_ui()
        else:
            self.setFixedWidth(620)
            self._build_free_ui()
            self.adjustSize()
```

**3d. Imports** (linhas 10-27): `QColor` e `breathe_glow` deixam de ser usados neste ficheiro — remover:

```python
from PySide6.QtGui import QColor        # REMOVER
from ui.theme import MAIN_STYLESHEET, breathe_glow   # → from ui.theme import MAIN_STYLESHEET
```

- [ ] **Step 4: Correr os testes (e os do plano atual)**

Run: `.venv\Scripts\python.exe -m pytest tests\test_license_dialog_free_ui.py tests\test_theme.py tests\test_i18n.py -q`
Expected: PASS (4 + 3 + test_i18n).

- [ ] **Step 5: Commit**

```bash
git add ui/license_dlg.py tests/test_license_dialog_free_ui.py
git commit -m "ui(license): dialogo FREE premium minimalista, sem pulses, chave secundaria"
```

---

### Task 4: UI PRO ativa simplificada

**Files:**
- Modify: `ui/license_dlg.py` (`_build_pro_ui`)
- Create: `tests/test_license_dialog_pro_ui.py`

- [ ] **Step 1: Escrever o teste (falhar primeiro)**

Criar `tests/test_license_dialog_pro_ui.py`:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from i18n import tr
from ui.license_dlg import LicenseDialog


class FakeProLicense:
    @property
    def is_pro(self):
        return True

    def trial_remaining_seconds(self):
        return 0

    def activate(self, key):
        return False

    def deactivate(self):
        pass


def _pro_dialog():
    app = QApplication.instance() or QApplication([])
    cfg = SimpleNamespace(license_tier="pro")
    return LicenseDialog(cfg, FakeProLicense())


def test_pro_dialog_is_compact_with_secondary_remove():
    dlg = _pro_dialog()
    assert dlg.width() <= 560
    assert dlg.height() <= 340
    btns = dlg.findChildren(QPushButton)
    assert len(btns) == 1
    assert tr("license.remove") in btns[0].text()
    assert btns[0].objectName() == "SettingsButtonSecondary"


def test_pro_dialog_has_hero_chip():
    dlg = _pro_dialog()
    assert [c for c in dlg.findChildren(QLabel) if c.objectName() == "HeroChip"]
```

E em `tests/test_theme.py`, acrescentar `SettingsButtonSecondary` ao token listado na Task 2 (Step 1):

```python
    for token in ("StatusChip", "HeroChip", "PlanCard", "PlanPrice",
                  "PlanExtra", "KeyCaption", "KeyField", "BenefitRow",
                  "SettingsButtonSecondary"):
```

- [ ] **Step 2: Correr para ver falhar**

Run: `.venv\Scripts\python.exe -m pytest tests\test_license_dialog_pro_ui.py tests\test_theme.py -q`
Expected: FAIL — `SettingsButtonSecondary` e `HeroChip` ainda não existem (o botão atual é `SettingsButton` e o badge é `HeroBadge`), e o token `SettingsButtonSecondary` não está no stylesheet.

- [ ] **Step 3: Implementar**

Substituir `_build_pro_ui` em `ui/license_dlg.py` por:

```python
    def _build_pro_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 28, 30, 28)
        lay.setSpacing(12)

        hero = QHBoxLayout()
        title = QLabel("Mãouse Pro")
        title.setObjectName("HeroTitle")
        hero.addWidget(title)
        hero.addSpacing(8)
        badge = QLabel("PRO")
        badge.setObjectName("HeroChip")
        hero.addWidget(badge)
        hero.addStretch()
        lay.addLayout(hero)

        sub = QLabel(tr("license.pro_active_sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addStretch()
        remover = QPushButton(tr("license.remove"))
        remover.setObjectName("SettingsButtonSecondary")
        remover.setCursor(Qt.PointingHandCursor)
        remover.clicked.connect(self._deactivate)
        lay.addWidget(remover)
```

E adicionar em `ui/theme.py` (dentro do stylesheet):

```css
QPushButton#SettingsButtonSecondary {
    background-color: transparent;
    color: #969696;
    border: 1px solid #1A1A2E;
    border-radius: 6px;
    padding: 8px 20px;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QPushButton#SettingsButtonSecondary:hover {
    color: #FF8A80;
    border-color: #FF8A80;
}
```

- [ ] **Step 4: Correr os testes**

Run: `.venv\Scripts\python.exe -m pytest tests\test_license_dialog_pro_ui.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/license_dlg.py ui/theme.py tests/test_license_dialog_pro_ui.py
git commit -m "ui(license): dialogo PRO ativo compacto com remocao secundaria"
```

---

### Task 5: Verificação final

- [ ] **Step 1: Compile de todos os ficheiros tocados**

Run: `.venv\Scripts\python.exe -m py_compile ui\license_dlg.py ui\theme.py i18n.py`
Expected: OK.

- [ ] **Step 2: Suíte completa**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: todos PASS exceto `tests/test_licensing.py::test_active_license_defaults_to_free` (depende da licença PRO ativa na máquina — falha pré-existente, não introduzida por este trabalho).

- [ ] **Step 3: Verificação manual do projeto (se a câmara estiver disponível)**

Run: `.venv\Scripts\python.exe main.py`
Expected: app abre; o menu Upgrade abre o novo diálogo sem erros e sem animações de pulse. (Opcional — não bloqueia o commit.)

- [ ] **Step 4: Atualizar `PROGRESSO.md`**

Adicionar secção `### REDESIGN AREA DE SUBSCRICAO (2026-09-05)` descrevendo: estilo premium minimalista, remoção de pulses, chave em modo secundário, copy confiante, tipografia com fallback. Etapa C (fontes embedded) fica registada como follow-up.

- [ ] **Step 5: Commit**

```bash
git add PROGRESSO.md
git commit -m "docs: registo do redesign da area de subscricao em PROGRESSO"
```

---

## Reviewer Instructions

1. Verificar que nenhum `breathe_glow`/`apply_glow` fica a ser usado em `ui/license_dlg.py` mas que `ui/theme.py` mantém a função (usada em `ui/menu_panel.py`).
2. Verificar que as chaves i18n usadas no spec existem (`license.hero`, `license.hero_sub`, `license.unlocks_title`, `license.cta`, `license.has_key`, `license.activate_key`, `license.pro_active_sub`, `license.remove`).
3. Verificar que os testes novos correm offscreen (`QT_QPA_PLATFORM=offscreen`).
4. Confirmar que `_on_plan_selected` continua a atualizar o CTA (testado em Task 3).
5. Confirmar que a largura FREE é 620 e a PRO 560x340.