from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressBar, QProgressDialog

from main_view_parts.theme import get_current_theme_colors


def _tokens() -> dict[str, str]:
    colors = get_current_theme_colors()
    return {
        **colors,
        "fg": colors["text_primary"],
        "fg_bright": colors["text_page_title"],
        "fg_dim": colors["text_muted"],
        "bg_dialog": colors["bg_panel"],
        "bg_card": colors["bg_surface_raised"],
        "bg_soft": colors["bg_surface_soft"],
        "border": colors["border_card"],
        "border_input": colors["border_input"],
        "border_hover": colors["border_input_hover"],
        "soft_bg": colors["btn_soft_bg"],
        "soft_hover": colors["btn_soft_hover"],
        "soft_pressed": colors["btn_soft_pressed"],
        "soft_border": colors["btn_soft_border"],
        "soft_text": colors["btn_soft_text"],
        "primary_bg": colors["btn_primary_bg"],
        "primary_hover": colors["btn_primary_hover"],
    }


def progress_dialog_stylesheet() -> str:
    t = _tokens()
    return f"""
        QProgressDialog {{
            background: {t["bg_dialog"]};
            border: 1px solid {t["border"]};
            border-radius: 14px;
        }}
        QProgressDialog QWidget {{
            background: transparent;
            color: {t["fg"]};
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            font-size: 12px;
        }}
        QProgressDialog QLabel {{
            background: transparent;
            color: {t["fg_bright"]};
            font-size: 13px;
            font-weight: 700;
        }}
        QProgressDialog QProgressBar {{
            background: {t["bg_soft"]};
            border: 1px solid {t["border_input"]};
            border-radius: 8px;
            min-height: 12px;
            text-align: center;
            color: {t["fg_dim"]};
        }}
        QProgressDialog QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 {t["primary_bg"]}, stop:1 {t["primary_hover"]});
            border-radius: 7px;
        }}
        QProgressDialog QPushButton {{
            min-width: 88px;
            min-height: 32px;
            border-radius: 10px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 700;
            background: {t["soft_bg"]};
            border: 1px solid {t["soft_border"]};
            color: {t["soft_text"]};
        }}
        QProgressDialog QPushButton:hover {{
            background: {t["soft_hover"]};
            border-color: {t["border_hover"]};
        }}
        QProgressDialog QPushButton:pressed {{
            background: {t["soft_pressed"]};
        }}
    """


def apply_progress_dialog_style(dialog: QProgressDialog) -> QProgressDialog:
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumWidth(360)
    dialog.setStyleSheet(progress_dialog_stylesheet())

    progress_bar = dialog.findChild(QProgressBar)
    if progress_bar is not None:
        progress_bar.setTextVisible(False)

    return dialog


def create_progress_dialog(parent, title: str, label_text: str, cancel_button_text: str | None = None) -> QProgressDialog:
    dialog = QProgressDialog(label_text, cancel_button_text, 0, 0, parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumDuration(0)
    if cancel_button_text is None:
        dialog.setCancelButton(None)
    return apply_progress_dialog_style(dialog)
