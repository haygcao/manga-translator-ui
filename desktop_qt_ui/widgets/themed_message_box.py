from __future__ import annotations

import textwrap

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from main_view_parts.theme import apply_widget_stylesheet, get_current_theme_colors

_INSTALLED = False


def _dialog_tokens() -> dict[str, str]:
    colors = get_current_theme_colors()
    return {
        **colors,
        "bg_dialog": colors["bg_panel"],
        "border": colors["border_input"],
        "fg": colors["text_primary"],
        "fg_muted": colors["text_muted"],
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


def _error_dialog_stylesheet() -> str:
    t = _dialog_tokens()
    return f"""
        QDialog#errorDialog {{
            background: {t["bg_dialog"]};
            border: 1px solid {t["border"]};
            border-radius: 14px;
        }}
        QDialog#errorDialog QLabel {{
            background: transparent;
            color: {t["fg"]};
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            font-size: 12px;
        }}
        QDialog#errorDialog QLabel#errorDialogTitle {{
            color: {t["fg"]};
            font-size: 13px;
            font-weight: 700;
        }}
        QDialog#errorDialog QWidget#dialogHeader {{
            background: transparent;
        }}
        QDialog#errorDialog QLabel#dialogWindowTitle {{
            color: {t["fg"]};
            font-size: 12px;
            font-weight: 600;
        }}
        QDialog#errorDialog QLabel#dialogIcon {{
            background: transparent;
        }}
        QDialog#errorDialog QToolButton#dialogCloseButton {{
            background: transparent;
            border: none;
            border-radius: 8px;
            color: {t["fg_muted"]};
            font-size: 16px;
            font-weight: 600;
            min-width: 28px;
            min-height: 28px;
            padding: 0;
        }}
        QDialog#errorDialog QToolButton#dialogCloseButton:hover {{
            background: {t["soft_bg"]};
            color: {t["fg"]};
        }}
        QDialog#errorDialog QToolButton#dialogCloseButton:pressed {{
            background: {t["soft_pressed"]};
        }}
        QDialog#errorDialog QScrollArea#errorDialogScroll {{
            background: transparent;
            border: none;
        }}
        QDialog#errorDialog QWidget#qt_scrollarea_viewport,
        QDialog#errorDialog QScrollArea#errorDialogScroll > QWidget > QWidget {{
            background: transparent;
        }}
        QDialog#errorDialog QLabel#errorDialogDetails {{
            background: transparent;
            color: {t["fg"]};
            border: none;
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            font-size: 12px;
            padding: 0;
        }}
        QDialog#errorDialog QDialogButtonBox QPushButton {{
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
        QDialog#errorDialog QDialogButtonBox QPushButton:hover {{
            background: {t["soft_hover"]};
            border-color: {t["border"]};
        }}
        QDialog#errorDialog QDialogButtonBox QPushButton:pressed {{
            background: {t["soft_pressed"]};
        }}
        QDialog#errorDialog QDialogButtonBox QPushButton[dialogDefault="true"] {{
            background: {t["primary_bg"]};
            border: 1px solid {t["primary_border"]};
            color: {t["primary_text"]};
        }}
        QDialog#errorDialog QDialogButtonBox QPushButton[dialogDefault="true"]:hover {{
            background: {t["primary_hover"]};
        }}
        QDialog#errorDialog QDialogButtonBox QPushButton[dialogDefault="true"]:pressed {{
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


def _wrap_dialog_text(text: str, width: int = 88) -> str:
    wrapped_lines: list[str] = []
    for line in str(text or "").splitlines():
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=width,
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )
    return "\n".join(wrapped_lines)


def apply_message_box_style(box: QMessageBox) -> QMessageBox:
    box.setObjectName("themedMessageBox")
    box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    _refresh_button_state(box)
    style = box.style()
    style.unpolish(box)
    style.polish(box)
    box.update()
    for label in box.findChildren(QLabel):
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return box


def apply_error_dialog_style(dialog: QDialog) -> QDialog:
    dialog.setObjectName("errorDialog")
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    apply_widget_stylesheet(dialog, _error_dialog_stylesheet())
    style = dialog.style()
    style.unpolish(dialog)
    style.polish(dialog)
    dialog.update()
    for label in dialog.findChildren(QLabel):
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if label.objectName() == "errorDialogDetails":
            label.setTextFormat(Qt.TextFormat.PlainText)
    for text_edit in dialog.findChildren(QTextEdit):
        if not text_edit.objectName():
            text_edit.setObjectName("errorDialogDetails")
    for scroll_area in dialog.findChildren(QScrollArea):
        if not scroll_area.objectName():
            scroll_area.setObjectName("errorDialogScroll")
    for widget in dialog.findChildren(QWidget):
        if widget.objectName() == "qt_scrollarea_viewport":
            widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    for button_box in dialog.findChildren(QDialogButtonBox):
        for button in button_box.buttons():
            style = button.style()
            style.unpolish(button)
            style.polish(button)
            button.update()
    return dialog


def _icon_pixmap(parent, icon: QMessageBox.Icon):
    if icon == QMessageBox.Icon.Warning:
        standard_icon = QStyle.StandardPixmap.SP_MessageBoxWarning
    elif icon == QMessageBox.Icon.Critical:
        standard_icon = QStyle.StandardPixmap.SP_MessageBoxCritical
    elif icon == QMessageBox.Icon.Information:
        standard_icon = QStyle.StandardPixmap.SP_MessageBoxInformation
    elif icon == QMessageBox.Icon.Question:
        standard_icon = QStyle.StandardPixmap.SP_MessageBoxQuestion
    else:
        return None
    return parent.style().standardIcon(standard_icon).pixmap(36, 36)


_STANDARD_BUTTON_MAP = (
    (QMessageBox.StandardButton.Ok, QDialogButtonBox.StandardButton.Ok),
    (QMessageBox.StandardButton.Yes, QDialogButtonBox.StandardButton.Yes),
    (QMessageBox.StandardButton.No, QDialogButtonBox.StandardButton.No),
    (QMessageBox.StandardButton.Cancel, QDialogButtonBox.StandardButton.Cancel),
    (QMessageBox.StandardButton.Close, QDialogButtonBox.StandardButton.Close),
)


def _to_dialog_standard_button(button: QMessageBox.StandardButton):
    for message_button, dialog_button in _STANDARD_BUTTON_MAP:
        if button == message_button:
            return dialog_button
    return None


def _to_message_standard_button(button) -> QMessageBox.StandardButton:
    for message_button, dialog_button in _STANDARD_BUTTON_MAP:
        if button == dialog_button:
            return message_button
    return QMessageBox.StandardButton.NoButton


def show_error_dialog(
    parent,
    window_title: str,
    heading: str,
    details: str,
    icon: QMessageBox.Icon = QMessageBox.Icon.NoIcon,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    dialog_parent = parent or QApplication.activeWindow()
    dialog = QDialog(dialog_parent)
    dialog.setWindowTitle(window_title)
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
    dialog.setModal(True)
    dialog.setSizeGripEnabled(True)
    dialog.setMinimumSize(620, 260)
    dialog.setWindowModality(
        Qt.WindowModality.WindowModal if dialog_parent is not None else Qt.WindowModality.ApplicationModal
    )

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    header = QWidget(dialog)
    header.setObjectName("dialogHeader")
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(8)

    title_label = QLabel(window_title, header)
    title_label.setObjectName("dialogWindowTitle")
    title_label.setTextFormat(Qt.TextFormat.PlainText)
    header_layout.addWidget(title_label, 1)

    close_button = QToolButton(header)
    close_button.setObjectName("dialogCloseButton")
    close_button.setText("×")
    close_button.setAutoRaise(True)
    close_button.clicked.connect(dialog.reject)
    header_layout.addWidget(close_button)
    layout.addWidget(header)

    body_layout = QHBoxLayout()
    body_layout.setContentsMargins(0, 0, 0, 0)
    body_layout.setSpacing(14)

    icon_pixmap = _icon_pixmap(dialog, icon)
    if icon_pixmap is not None:
        icon_label = QLabel(dialog)
        icon_label.setObjectName("dialogIcon")
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        body_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)

    normalized_heading = str(heading or "").strip()
    if normalized_heading:
        summary_label = QLabel(normalized_heading, dialog)
        summary_label.setObjectName("errorDialogTitle")
        summary_label.setTextFormat(Qt.TextFormat.PlainText)
        summary_label.setWordWrap(True)
        summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_layout.addWidget(summary_label)

    scroll_area = QScrollArea(dialog)
    scroll_area.setObjectName("errorDialogScroll")
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    details_container = QWidget(scroll_area)
    details_layout = QVBoxLayout(details_container)
    details_layout.setContentsMargins(0, 0, 0, 0)

    details_label = QLabel(details_container)
    details_label.setObjectName("errorDialogDetails")
    details_label.setTextFormat(Qt.TextFormat.PlainText)
    details_label.setWordWrap(True)
    details_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    details_label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
    )
    details_label.setText(str(details or ""))
    details_layout.addWidget(details_label)

    scroll_area.setWidget(details_container)
    content_layout.addWidget(scroll_area)
    body_layout.addLayout(content_layout, 1)
    layout.addLayout(body_layout)

    if buttons == QMessageBox.StandardButton.NoButton:
        buttons = QMessageBox.StandardButton.Ok

    button_box = QDialogButtonBox(parent=dialog)
    added_buttons = 0
    for message_button, dialog_button in _STANDARD_BUTTON_MAP:
        if buttons & message_button:
            button_box.addButton(dialog_button)
            added_buttons += 1
    if added_buttons == 0:
        button_box.addButton(QDialogButtonBox.StandardButton.Ok)

    def _handle_button_clicked(button):
        standard_button = _to_message_standard_button(button_box.standardButton(button))
        dialog.done(int(standard_button))

    button_box.clicked.connect(_handle_button_clicked)

    effective_default = default_button
    if effective_default == QMessageBox.StandardButton.NoButton:
        box_buttons = button_box.buttons()
        if len(box_buttons) == 1:
            effective_default = _to_message_standard_button(button_box.standardButton(box_buttons[0]))
    if effective_default != QMessageBox.StandardButton.NoButton:
        dialog_default = _to_dialog_standard_button(effective_default)
        if dialog_default is not None:
            default_qbutton = button_box.button(dialog_default)
            if default_qbutton is not None:
                default_qbutton.setProperty("dialogDefault", True)
                default_qbutton.setDefault(True)
    layout.addWidget(button_box)

    apply_error_dialog_style(dialog)
    content_width = 760
    content_height = max(140, details_label.heightForWidth(content_width))
    scroll_area.setMinimumHeight(min(content_height + 8, 420))
    target_size = dialog.sizeHint().expandedTo(QSize(680, 280))
    dialog.resize(min(target_size.width(), 920), min(target_size.height(), 560))
    result = dialog.exec()
    if result in (QDialog.DialogCode.Accepted, QDialog.DialogCode.Rejected):
        return QMessageBox.StandardButton.NoButton
    return QMessageBox.StandardButton(result)


def _show_message_box(
    parent,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    return show_error_dialog(
        parent,
        title,
        "",
        _wrap_dialog_text(text, width=72),
        icon=icon,
        buttons=buttons,
        default_button=default_button,
    )


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
