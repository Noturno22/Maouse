"""Modern message box component following Mãouse Visual Identity."""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import (
    ACCENT,
    ERROR,
    FONT_PRIMARY,
    FONT_PRIMARY_BOLD,
    SUCCESS,
    TEXT_PRIMARY,
    WARNING,
)


class ModernMessageBox(QDialog):
    """Modern message box replacement for QMessageBox."""

    def __init__(self, parent=None, title="", message="", msg_type="info"):
        """
        Initialize the modern message box.

        Args:
            parent: Parent widget
            title: Title of the message box
            message: Message to display
            msg_type: Type of message ("info", "warning", "error", "success")
        """
        super().__init__(parent)
        self._msg_type = msg_type
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(420)
        self.setObjectName("ModernMessageBox")

        # Remove window frame for custom design
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Setup UI
        self._setup_ui(title, message, msg_type)

        # Setup animations
        self._setup_animations()

    def _setup_ui(self, title, message, msg_type):
        """Setup the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Background widget with rounded corners and shadow
        self._background = QWidget()
        self._background.setObjectName("MsgBoxBackground")
        self._background.setStyleSheet("""
            QWidget#MsgBoxBackground {
                background-color: rgba(10, 10, 18, 0.95);
                border-radius: 16px;
                border: 1px solid rgba(80, 200, 255, 0.2);
            }
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self._background)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self._background.setGraphicsEffect(shadow)

        # Layout for background
        bg_layout = QVBoxLayout(self._background)
        bg_layout.setContentsMargins(28, 24, 28, 24)
        bg_layout.setSpacing(16)

        # Icon and title section
        if title:
            title_layout = QHBoxLayout()
            title_layout.setSpacing(12)

            # Icon based on message type
            icon_label = QLabel()
            icon_label.setFixedSize(24, 24)
            icon_color = self._get_msg_color(msg_type)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    color: {icon_color.name()};
                    font-size: 20px;
                    font-weight: bold;
                }}
            """)

            # Set icon based on type
            if msg_type == "error":
                icon_label.setText("✕")
            elif msg_type == "warning":
                icon_label.setText("⚠")
            elif msg_type == "success":
                icon_label.setText("✓")
            else:  # info
                icon_label.setText("ℹ")

            title_layout.addWidget(icon_label)

            # Title text
            title_label = QLabel(title)
            title_label.setObjectName("MsgBoxTitle")
            title_label.setFont(FONT_PRIMARY_BOLD)
            title_label.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            bg_layout.addLayout(title_layout)

        # Message text
        msg_label = QLabel(message)
        msg_label.setObjectName("MsgBoxMessage")
        msg_label.setFont(FONT_PRIMARY)
        msg_label.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        msg_label.setWordWrap(True)
        bg_layout.addWidget(msg_label)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 12, 0, 0)
        button_layout.setSpacing(12)

        # OK button
        ok_button = QPushButton("OK")
        ok_button.setObjectName("MsgBoxOkButton")
        ok_button.setFixedHeight(36)
        ok_button.setFixedWidth(80)
        ok_button.setFont(FONT_PRIMARY_BOLD)
        ok_button.setCursor(Qt.PointingHandCursor)

        # Style the OK button based on message type
        bg_color = self._get_msg_color(msg_type)
        ok_button.setStyleSheet(f"""
            QPushButton#MsgBoxOkButton {{
                background-color: {bg_color.name()};
                color: #0A0A12;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton#MsgBoxOkButton:hover {{
                background-color: {bg_color.lighter(120).name()};
            }}
            QPushButton#MsgBoxOkButton:pressed {{
                background-color: {bg_color.darker(120).name()};
            }}
        """)

        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()

        bg_layout.addLayout(button_layout)

        # Add background to main layout
        main_layout.addWidget(self._background)

        # Apply main stylesheet
        self.setStyleSheet("""
            QDialog#ModernMessageBox {
                background-color: transparent;
            }
        """)

    def _get_msg_color(self, msg_type):
        """Get color based on message type."""
        colors = {
            "error": ERROR,
            "warning": WARNING,
            "success": SUCCESS,
            "info": ACCENT
        }
        return colors.get(msg_type.lower(), ACCENT)

    def _setup_animations(self):
        """Set up the entrance animation.

        A entrada e decoracao; a janela **nao** depende dela para ser
        visivel. Ha aqui um bug medido que vale a pena nao repetir: esta
        classe chegou a ter *duas* `QPropertyAnimation` na mesma property
        (`windowOpacity`) dentro de um `QParallelAnimationGroup`, e o grupo
        deixava o valor no `startValue` — a caixa ficava a 0.0 de opacidade
        para sempre, ou seja invisivel. Medido: animacao solitaria 1.0,
        grupo com duas 0.0, grupo com uma 1.0. Ha agora uma animacao, e o
        `finished` reforca o 1.0 para que a janela fique visivel mesmo que a
        animacao seja interrompida a meio.
        """
        self.setWindowOpacity(0.0)

        # O primeiro argumento do QPropertyAnimation e o *alvo* da property, nao
        # o pai: `QPropertyAnimation(target, propertyName, parent=None)`. A
        # animacao vivia so pelo atributo Python, sem pai de QObject, e por isso
        # nenhum `findChildren` a via — o que tornava impossivel verificar que
        # havia uma so a escrever em `windowOpacity`.
        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(250)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.finished.connect(self._settle_visible)

    def _settle_visible(self):
        """Garante a opacidade final, mesmo se a animacao foi interrompida."""
        self.setWindowOpacity(1.0)

    def showEvent(self, event):
        """Fade in when the dialog is shown."""
        super().showEvent(event)
        self._fade_in.start()

    # Static methods to mimic QMessageBox interface
    @staticmethod
    def information(parent, title, text):
        """Show information message box."""
        msgbox = ModernMessageBox(parent, title, text, "info")
        msgbox.exec()

    @staticmethod
    def warning(parent, title, text):
        """Show warning message box."""
        msgbox = ModernMessageBox(parent, title, text, "warning")
        msgbox.exec()

    @staticmethod
    def critical(parent, title, text):
        """Show critical/error message box."""
        msgbox = ModernMessageBox(parent, title, text, "error")
        msgbox.exec()

    @staticmethod
    def question(parent, title, text):
        """Show question message box."""
        msgbox = ModernMessageBox(parent, title, text, "info")  # Could extend for Yes/No later
        msgbox.exec()


# Convenience functions for easy replacement
def show_information(parent, title, text):
    """Show an information message."""
    ModernMessageBox.information(parent, title, text)

def show_warning(parent, title, text):
    """Show a warning message."""
    ModernMessageBox.warning(parent, title, text)

def show_error(parent, title, text):
    """Show an error message."""
    ModernMessageBox.critical(parent, title, text)

def show_question(parent, title, text):
    """Show a question message."""
    ModernMessageBox.question(parent, title, text)
