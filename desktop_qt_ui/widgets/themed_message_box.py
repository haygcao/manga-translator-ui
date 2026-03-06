from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from main_view_parts.theme import get_current_theme, get_current_theme_colors

_INSTALLED = False


def _tokens() -> dict[str, str]:
    colors = get_current_theme_colors()
    is_light = get_current_theme() == "light"
    return {
        **colors,
        "fg": colors["text_primary"],
        "fg_dim": colors["text_muted"],
        "fg_bright": colors["text_page_title"],
        "bg_dialog": colors["bg_panel"],
        "bg_card": colors["bg_surface_raised"],
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
        "danger_bg": colors["danger_bg"],
        "danger_border": colors["danger_border"],
        "danger_text": colors["danger_text"],
        "shadow_color": "rgba(0, 0, 0, 0.10)" if is_light else "rgba(0, 0, 0, 0.24)",
    }


def message_box_stylesheet() -> str:
    t = _tokens()
    return f"""
        QMessageBox {{
            background: {t["bg_dialog"]};
            border: 1px solid {t["border"]};
            border-radius: 14px;
        }}
        QMessageBox QWidget {{
            background: transparent;
            color: {t["fg"]};
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            font-size: 12px;
        }}
        QMessageBox QLabel {{
            background: transparent;
        }}
        QMessageBox QLabel#qt_msgbox_label {{
            color: {t["fg_bright"]};
            font-size: 13px;
            font-weight: 700;
            min-width: 320px;
        }}
        QMessageBox QLabel#qt_msgboxex_icon_label {{
            background: transparent;
        }}
        QMessageBox QLabel#qt_msgbox_informativelabel {{
            color: {t["fg_dim"]};
            font-size: 12px;
            min-width: 320px;
        }}
        QMessageBox QPushButton {{
            min-width: 88px;
            min-height: 34px;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            background: {t["soft_bg"]};
            border: 1px solid {t["soft_border"]};
            color: {t["soft_text"]};
        }}
        QMessageBox QPushButton:hover {{
            background: {t["soft_hover"]};
            border-color: {t["border_focus"]};
        }}
        QMessageBox QPushButton:pressed {{
            background: {t["soft_pressed"]};
        }}
        QMessageBox QPushButton[dialogDefault=\"true\"] {{
            background: {t["primary_bg"]};
            border: 1px solid {t["primary_border"]};
            color: {t["primary_text"]};
        }}
        QMessageBox QPushButton[dialogDefault=\"true\"]:hover {{
            background: {t["primary_hover"]};
        }}
        QMessageBox QPushButton[dialogDefault=\"true\"]:pressed {{
            background: {t["primary_pressed"]};
        }}
    """


def _refresh_button_state(box: QMessageBox) -> None:
    buttons = box.buttons()
    default_button = box.defaultButton()
    if default_button is None and len(buttons) == 1:
        default_button = buttons[0]

    for button in buttons:
        button.setProperty("dialogDefault", button is default_button)
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()


def apply_message_box_style(box: QMessageBox) -> QMessageBox:
    box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    box.setStyleSheet(message_box_stylesheet())
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    _refresh_button_state(box)
    return box


def _show_message_box(
    parent,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default_button != QMessageBox.StandardButton.NoButton:
        box.setDefaultButton(default_button)
    apply_message_box_style(box)
    return QMessageBox.StandardButton(box.exec())


def themed_information(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
):
    return _show_message_box(parent, QMessageBox.Icon.Information, title, text, buttons, default_button)


def themed_warning(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
):
    return _show_message_box(parent, QMessageBox.Icon.Warning, title, text, buttons, default_button)


def themed_critical(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
):
    return _show_message_box(parent, QMessageBox.Icon.Critical, title, text, buttons, default_button)


def themed_question(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
):
    return _show_message_box(parent, QMessageBox.Icon.Question, title, text, buttons, default_button)


def install_themed_message_boxes() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    QMessageBox.information = staticmethod(themed_information)
    QMessageBox.warning = staticmethod(themed_warning)
    QMessageBox.critical = staticmethod(themed_critical)
    QMessageBox.question = staticmethod(themed_question)
    _INSTALLED = True
