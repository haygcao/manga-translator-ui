from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QProgressBar, QProgressDialog

from main_view_parts.theme import (
    apply_native_title_bar_theme,
    apply_widget_stylesheet,
    generate_application_stylesheet,
    get_current_theme,
)


def _global_progress_stylesheet() -> str:
    app = QApplication.instance()
    return app.styleSheet() if app is not None else generate_application_stylesheet(get_current_theme())

def apply_progress_dialog_style(dialog: QProgressDialog) -> QProgressDialog:
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumWidth(360)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    apply_widget_stylesheet(dialog, _global_progress_stylesheet())
    QTimer.singleShot(0, lambda: apply_native_title_bar_theme(dialog, get_current_theme()))

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
