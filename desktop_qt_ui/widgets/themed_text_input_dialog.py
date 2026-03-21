from __future__ import annotations

from main_view_parts.theme import get_current_theme_colors
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _tokens() -> dict[str, str]:
    colors = get_current_theme_colors()
    return {
        **colors,
        "fg": colors["text_primary"],
        "fg_dim": colors["text_muted"],
        "fg_bright": colors["text_page_title"],
        "bg_dialog": colors["bg_panel"],
        "bg_card": colors["bg_surface_raised"],
        "bg_input": colors["bg_input"],
        "border": colors["border_input"],
        "border_focus": colors["border_input_focus"],
        "soft_bg": colors["btn_soft_bg"],
        "soft_hover": colors["btn_soft_hover"],
        "soft_pressed": colors["btn_soft_pressed"],
        "soft_border": colors["btn_soft_border"],
        "soft_text": colors["btn_soft_text"],
        "primary_bg": colors["btn_primary_bg"],
        "primary_hover": colors["btn_primary_hover"],
        "primary_pressed": colors["btn_primary_pressed"],
        "primary_border": colors["btn_primary_border"],
        "primary_text": colors["btn_primary_text"],
    }


def _dialog_stylesheet() -> str:
    t = _tokens()
    return f"""
        QDialog {{
            background: {t["bg_dialog"]};
        }}
        QLabel {{
            color: {t["fg"]};
            background: transparent;
        }}
        QLabel#dialog_title {{
            color: {t["fg_bright"]};
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#dialog_prompt {{
            color: {t["fg_dim"]};
            font-size: 12px;
        }}
        QWidget#dialog_card {{
            background: {t["bg_card"]};
            border: 1px solid {t["border"]};
            border-radius: 12px;
        }}
        QLineEdit {{
            background: {t["bg_input"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
            color: {t["fg"]};
            padding: 8px 10px;
            min-height: 24px;
        }}
        QLineEdit:focus {{
            border-color: {t["border_focus"]};
        }}
        QPushButton {{
            min-width: 88px;
            min-height: 34px;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton[role="soft"] {{
            background: {t["soft_bg"]};
            border: 1px solid {t["soft_border"]};
            color: {t["soft_text"]};
        }}
        QPushButton[role="soft"]:hover {{
            background: {t["soft_hover"]};
        }}
        QPushButton[role="soft"]:pressed {{
            background: {t["soft_pressed"]};
        }}
        QPushButton[role="primary"] {{
            background: {t["primary_bg"]};
            border: 1px solid {t["primary_border"]};
            color: {t["primary_text"]};
        }}
        QPushButton[role="primary"]:hover {{
            background: {t["primary_hover"]};
        }}
        QPushButton[role="primary"]:pressed {{
            background: {t["primary_pressed"]};
        }}
    """


class ThemedTextInputDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        title: str,
        label: str,
        text: str = "",
        ok_text: str = "OK",
        cancel_text: str = "Cancel",
        placeholder: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("dialog_title")
        root.addWidget(title_label)

        card = QWidget()
        card.setObjectName("dialog_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(8)

        prompt_label = QLabel(label)
        prompt_label.setObjectName("dialog_prompt")
        prompt_label.setWordWrap(True)
        card_layout.addWidget(prompt_label)

        self.line_edit = QLineEdit()
        self.line_edit.setText(text)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.returnPressed.connect(self.accept)
        card_layout.addWidget(self.line_edit)

        root.addWidget(card)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addStretch(1)

        cancel_button = QPushButton(cancel_text)
        cancel_button.setProperty("role", "soft")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(cancel_button)

        ok_button = QPushButton(ok_text)
        ok_button.setProperty("role", "primary")
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
        ok_button.clicked.connect(self.accept)
        button_row.addWidget(ok_button)

        root.addLayout(button_row)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    def text_value(self) -> str:
        return self.line_edit.text()


def themed_get_text(
    parent,
    title: str,
    label: str,
    text: str = "",
    ok_text: str = "OK",
    cancel_text: str = "Cancel",
    placeholder: str = "",
) -> tuple[str, bool]:
    dialog = ThemedTextInputDialog(
        parent,
        title=title,
        label=label,
        text=text,
        ok_text=ok_text,
        cancel_text=cancel_text,
        placeholder=placeholder,
    )
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return dialog.text_value(), accepted
