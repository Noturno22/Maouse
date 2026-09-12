"""Upgrade / License dialog for Mãouse.

Diálogo de upgrade orientado à venda: banner de modo FREE em destaque,
pitch de \"nova experiência tecnológica\", grelha de benefícios
revolucionários, planos selecionáveis, CTA dourado a pulsar e ativação
offline de chave Pro.
"""
import json
import math
import os
import re
import shutil
import time
import uuid
from urllib.parse import urlencode

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.licensing import Tier
from i18n import tr
from ui.theme import MAIN_STYLESHEET

SUPPORT_EMAIL = "suporte@maouse.app"

PADDLE_VENDOR_ID = 0  # TODO: preencher com o vendor_id real do Paddle (D2)

# (id, nome, preço curto, linha extra, destaque)
_PRODUCTS = [
    ("lifetime", "Lifetime", "€39,90", "uma vez · para sempre", True),
    ("family", "Família", "€59,90", "3 dispositivos", False),
    ("trading_master", "Trading Master", "€149,90", "multi-monitor", False),
    ("access", "Acessibilidade", "€19,95", "50% · sob validação", False),
]

# (chave nome, chave descrição) — só os mais fortes, para não poluir a tela.
_BENEFITS = [
    ("benefit.snap", "benefit.snap_short"),
    ("benefit.voice", "benefit.voice_short"),
    ("benefit.hands", "benefit.hands_short"),
    ("benefit.ai", "benefit.ai_short"),
]


class _BenefitRow(QLabel):
    """Uma linha de benefício: check verde + nome (bold) + mini descrição."""

    def __init__(self, name_key, desc_key, parent=None):
        super().__init__(parent)
        self.setObjectName("BenefitRow")
        self.setText(
            f'<span style="color:#7DDB8A; font-weight:bold;">✓</span>'
            f'&nbsp; <b>{tr(name_key)}</b>'
            f'<span style="color:#8A9AA6;"> — {tr(desc_key)}</span>'
        )
        self.setWordWrap(True)
        self.setToolTip(tr("license.unlocks_title"))


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
        lay.setContentsMargins(14, 12, 14, 12)
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

    def set_selected(self, value: bool):
        self._selected = value
        self.setProperty("selected", "true" if value else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._plan_id)
        super().mousePressEvent(event)


class LicenseDialog(QDialog):

    def __init__(self, cfg, license_mgr, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._lm = license_mgr
        self._selected_plan = "lifetime"
        self.setWindowTitle("Mãouse Pro — Licença")
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(MAIN_STYLESHEET)

        if self._lm.is_pro:
            self.setFixedSize(560, 340)
            self._build_pro_ui()
        else:
            self.setFixedWidth(620)
            self._build_free_ui()
            self.adjustSize()

    # ── Helpers ───────────────────────────────────────────────────────
    def _make_card(self, plan):
        plan_id, name, price, extra, highlight = plan
        card = _ProductCard(plan_id, name, price, extra, highlight)
        card.selected.connect(self._on_plan_selected)
        card.set_selected(plan_id == self._selected_plan)
        return card

    def _on_plan_selected(self, plan_id):
        self._selected_plan = plan_id
        for i in range(self._cards_grid.count()):
            w = self._cards_grid.itemAt(i).widget()
            if isinstance(w, _ProductCard):
                w.set_selected(w._plan_id == plan_id)
        for plan_id2, _name, price, _extra, _ in _PRODUCTS:
            if plan_id2 == plan_id:
                if plan_id2 == "access":
                    self._cta.setText(tr("license.cta_access"))
                else:
                    self._cta.setText(f"{tr('license.cta')} · {price}")
                break

    # ── Free / upgrade ────────────────────────────────────────────────
    def _build_free_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 24)
        lay.setSpacing(12)

        # Chip de estado FREE — discreto, sem pulsos. Ao lado, o tempo de
        # trial restante (só aparece enquanto há trial por gastar).
        status_row = QHBoxLayout()
        chip = QLabel(tr("license.free_badge").replace(" ", " · "))
        chip.setObjectName("StatusChip")
        chip.setAlignment(Qt.AlignLeft)
        status_row.addWidget(chip)
        status_row.addStretch()
        remaining = self._lm.trial_remaining_seconds()
        if remaining > 0:
            rem = QLabel(
                tr("license.trial_remaining").format(
                    m=max(1, math.ceil(remaining / 60))
                )
            )
            rem.setObjectName("StatusChip")
            rem.setAlignment(Qt.AlignRight)
            status_row.addWidget(rem)
        lay.addLayout(status_row)

        # Hero com o pitch de nova experiência tecnológica.
        hero = QHBoxLayout()
        badge = QLabel("PRO")
        badge.setObjectName("HeroChip")
        hero.addWidget(badge)
        hero.addSpacing(10)
        title = QLabel(tr("license.hero"))
        title.setObjectName("HeroTitle")
        hero.addWidget(title)
        hero.addStretch()
        lay.addLayout(hero)
        sub = QLabel(tr("license.hero_sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # Benefícios — uma coluna limpa com os principais, sem ruído.
        lay.addSpacing(4)
        feat_title = QLabel(tr("license.unlocks_title"))
        feat_title.setObjectName("SectionTitle")
        feat_title.setAlignment(Qt.AlignLeft)
        lay.addWidget(feat_title)
        for nk, dk in _BENEFITS:
            lay.addWidget(_BenefitRow(nk, dk))

        # Planos.
        lay.addSpacing(2)
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(10)
        for i, plan in enumerate(_PRODUCTS):
            self._cards_grid.addWidget(self._make_card(plan), i // 2, i % 2)
        lay.addLayout(self._cards_grid)

        # CTA principal — plano em destaque, sem pulso.
        self._cta = QPushButton(f"{tr('license.cta')} \u00b7 {_PRODUCTS[0][2]}")
        self._cta.setObjectName("ProCta")
        self._cta.setCursor(Qt.PointingHandCursor)
        self._cta.setFixedHeight(46)
        self._cta.clicked.connect(self._on_cta)
        lay.addWidget(self._cta)

        self._build_key_row(lay)

    def _build_key_row(self, lay):
        divider = QFrame()
        divider.setObjectName("MenuDivider")
        divider.setFixedHeight(1)
        lay.addWidget(divider)
        lay.addSpacing(6)
        caption = QLabel(tr("license.has_key"))
        caption.setObjectName("KeyCaption")
        caption.setAlignment(Qt.AlignLeft)
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

    def _on_cta(self):
        if self._selected_plan == "access":
            AccessibilityDialog(self).exec()
            return
        self._open_checkout(self._selected_plan)

    # ── Pro ativo ─────────────────────────────────────────────────────
    def _build_pro_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 28, 30, 28)
        lay.setSpacing(14)

        hero = QHBoxLayout()
        badge = QLabel("PRO")
        badge.setObjectName("HeroChip")
        hero.addWidget(badge)
        hero.addSpacing(10)
        title = QLabel(tr("license.pro_active_title"))
        title.setObjectName("HeroTitle")
        hero.addWidget(title)
        hero.addStretch()
        lay.addLayout(hero)

        sub = QLabel(tr("license.pro_active_sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addStretch()
        remover = QPushButton(tr("license.remove"))
        remover.setObjectName("SettingsButtonSecondary")
        remover.clicked.connect(self._deactivate)
        lay.addWidget(remover)

    # ── Ações ─────────────────────────────────────────────────────────
    def _open_checkout(self, product):
        if not self._lm.open_checkout(product, PADDLE_VENDOR_ID):
            QMessageBox.warning(self, "Checkout",
                                "Não foi possível abrir o checkout no browser.")
        else:
            QMessageBox.information(
                self, "Checkout",
                "O checkout Paddle abriu no seu browser.\n"
                "Após a compra, cole a chave que receber no campo abaixo e clique em "
                "\"Ativar Chave\".",
            )

    def _activate_key(self):
        key = self._key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Chave", "Cole a sua chave Pro primeiro.")
            return
        if self._lm.activate(key):
            self._cfg.license_tier = Tier.PRO.value
            QMessageBox.information(self, "Licença", "Licença Pro ativada com sucesso!")
            self.accept()
        else:
            QMessageBox.warning(self, "Chave", "Chave inválida. Verifique e tente novamente.")

    def _deactivate(self):
        self._lm.deactivate()
        self._cfg.license_tier = Tier.FREE.value
        QMessageBox.information(self, "Licença", "Licença removida. Modo Free ativo.")
        self.accept()


class AccessibilityDialog(QDialog):
    """Pedido de desconto de acessibilidade (50%) — D3.

    Formulário + comprovativo. A validação é manual: o pedido fica registado
    localmente (``%APPDATA%\\AirMouse\\accessibility_requests``), abre-se um
    email para o suporte com o comprovativo, e a equipa gera o cupão de 50%.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mãouse Pro")
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setModal(True)
        self.setFixedWidth(520)
        self._proof_path = ""
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel(tr("access.title"))
        title.setObjectName("HeroTitle")
        lay.addWidget(title)

        sub = QLabel(tr("access.sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("access.name"))
        self._name_edit.setObjectName("KeyEdit")
        lay.addWidget(self._name_edit)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText(tr("access.email"))
        self._email_edit.setObjectName("KeyEdit")
        lay.addWidget(self._email_edit)

        self._proof_combo = QComboBox()
        self._proof_combo.setObjectName("SettingsCombo")
        for key in (
            "access.proof_medical",
            "access.proof_disability_card",
            "access.proof_health_unit",
            "access.proof_association",
        ):
            self._proof_combo.addItem(tr(key))
        lay.addWidget(self._proof_combo)

        attach_row = QHBoxLayout()
        self._attach_btn = QPushButton(tr("access.attach"))
        self._attach_btn.setObjectName("SettingsButton")
        self._attach_btn.clicked.connect(self._pick_proof)
        attach_row.addWidget(self._attach_btn)
        self._proof_lbl = QLabel(tr("access.attach_hint"))
        self._proof_lbl.setObjectName("HeroSubtitle")
        self._proof_lbl.setWordWrap(True)
        attach_row.addWidget(self._proof_lbl, 1)
        lay.addLayout(attach_row)

        self._error_lbl = QLabel()
        self._error_lbl.setObjectName("ErrorLabel")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.hide()
        lay.addWidget(self._error_lbl)

        lay.addSpacing(4)
        submit = QPushButton(tr("access.submit"))
        submit.setObjectName("ProCta")
        submit.setCursor(Qt.PointingHandCursor)
        submit.setFixedHeight(44)
        submit.clicked.connect(self._submit)
        lay.addWidget(submit)

    def _pick_proof(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("access.attach"), "",
            "PDF (*.pdf);;Imagens (*.jpg *.jpeg *.png)",
        )
        if path:
            self._proof_path = path
            self._proof_lbl.setText(os.path.basename(path))
            self._proof_lbl.setStyleSheet("color:#7DD4FF;")
            self._error_lbl.hide()

    def _submit(self):
        name = self._name_edit.text().strip()
        email = self._email_edit.text().strip()
        if not name or not self._valid_email(email) or not self._proof_path:
            self._error_lbl.setText(tr("access.missing"))
            self._error_lbl.show()
            return
        ref = "ACC-" + uuid.uuid4().hex[:8].upper()
        try:
            saved = self._save_request(ref, name, email)
        except OSError as e:
            self._error_lbl.setText(f"Erro ao registar o pedido: {e}")
            self._error_lbl.show()
            return
        QMessageBox.information(
            self, "Mãouse Pro",
            tr("access.submitted").format(ref=ref),
        )
        self._open_email_draft(ref, name, email, saved)
        self.accept()

    def _valid_email(self, email):
        return re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

    def _save_request(self, ref, name, email):
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "AirMouse", "accessibility_requests")
        os.makedirs(folder, exist_ok=True)
        _, ext = os.path.splitext(self._proof_path)
        dest = os.path.join(folder, ref + (ext.lower() or ".bin"))
        shutil.copy2(self._proof_path, dest)
        meta = {
            "ref": ref,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "email": email,
            "proof_type": self._proof_combo.currentText(),
            "proof_file": os.path.basename(dest),
        }
        meta_path = os.path.join(folder, ref + ".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return meta_path

    def _open_email_draft(self, ref, name, email, meta_path):
        body = (
            f"Referência: {ref}\n"
            f"Nome: {name}\n"
            f"Email: {email}\n"
            f"Comprovativo: {self._proof_combo.currentText()}\n"
            f"Anexar ficheiro (cópia): {meta_path}\n"
        )
        params = urlencode({
            "subject": f"Mãouse Pro — Pedido de Acessibilidade {ref}",
            "body": body,
        })
        QDesktopServices.openUrl(QUrl(f"mailto:{SUPPORT_EMAIL}?{params}"))


class BlockDialog(QDialog):
    """Pop-up urgente de bloqueio total.

    Aparece UMA vez por sessão quando o trial/lease esgotou (o gate de
    ``process_frame`` já impediu o movimento). Sem âncora: título + subtítulo
    sóbrios, CTA claro \"ATIVAR PRO AGORA\" (checkout) e ativação por chave.
    """

    def __init__(self, cfg, license_mgr, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._lm = license_mgr
        self.setWindowTitle("Mãouse Pro")
        self.setObjectName("SettingsDialog")
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setModal(True)
        self.setFixedWidth(460)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel(tr("license.trial_ended"))
        title.setObjectName("HeroTitle")
        title.setWordWrap(True)
        lay.addWidget(title)

        sub = QLabel(tr("license.trial_ended_sub"))
        sub.setObjectName("HeroSubtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # CTA principal — abre o checkout Paddle (lifetime por omissão).
        cta = QPushButton(f"{tr('license.activate_now')}")
        cta.setObjectName("ProCta")
        cta.setCursor(Qt.PointingHandCursor)
        cta.setFixedHeight(44)
        cta.clicked.connect(lambda: self._open_checkout("lifetime"))
        lay.addWidget(cta)

        divider = QFrame()
        divider.setObjectName("MenuDivider")
        divider.setFixedHeight(1)
        lay.addSpacing(4)
        lay.addWidget(divider)

        # Ativação por chave (quem já comprou).
        key_row = QHBoxLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText(tr("license.has_key"))
        self._key_edit.setObjectName("KeyEdit")
        self._key_edit.returnPressed.connect(self._activate_key)
        key_row.addWidget(self._key_edit, 1)
        activate = QPushButton(tr("license.activate_key"))
        activate.setObjectName("SettingsButton")
        activate.clicked.connect(self._activate_key)
        key_row.addWidget(activate)
        lay.addLayout(key_row)

        self._error_lbl = QLabel()
        self._error_lbl.setObjectName("ErrorLabel")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.hide()
        lay.addWidget(self._error_lbl)

        lay.addStretch()

    def _open_checkout(self, product):
        if not self._lm.open_checkout(product, PADDLE_VENDOR_ID):
            self._error_lbl.setText(tr("license.needs_connection"))
            self._error_lbl.show()

    def _activate_key(self):
        key = self._key_edit.text().strip()
        if not key:
            self._error_lbl.setText(tr("license.enter_key"))
            self._error_lbl.show()
            return
        if self._lm.activate(key):
            self._cfg.license_tier = Tier.PRO.value
            self.accept()
        else:
            self._error_lbl.setText(tr("license.activate_failed"))
            self._error_lbl.show()
