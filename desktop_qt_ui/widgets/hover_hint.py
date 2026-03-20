from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QWidget

from main_view_parts.theme import get_current_theme_colors


class _HoverHintPopup(QLabel):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWordWrap(False)
        self.setMargin(0)
        self._apply_style()

    def _apply_style(self):
        colors = get_current_theme_colors()
        self.setStyleSheet(
            f"""
            QLabel {{
                background: {colors["bg_dropdown"]};
                color: {colors["text_accent"]};
                border: 1px solid {colors["border_input"]};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )

    def show_for(self, anchor: QWidget, text: str):
        self._apply_style()
        self.setText(text)
        self.adjustSize()

        global_pos = anchor.mapToGlobal(QPoint((anchor.width() - self.width()) // 2, anchor.height() + 8))
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = max(rect.left() + 8, min(global_pos.x(), rect.right() - self.width() - 8))
            y = max(rect.top() + 8, min(global_pos.y(), rect.bottom() - self.height() - 8))
            global_pos = QPoint(x, y)

        self.move(global_pos)
        self.show()


class _HoverHintController(QObject):
    def __init__(self, widget: QWidget, text: str, delay_ms: int = 450):
        super().__init__(widget)
        self._widget = widget
        self._text = str(text or "")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self._show_hint)
        self._popup = _HoverHintPopup()
        widget.setToolTip("")
        widget.installEventFilter(self)
        widget.destroyed.connect(self._cleanup)

    def _show_hint(self):
        if self._widget is None:
            return
        if not self._text:
            return
        if not self._widget.isVisible() or not self._widget.underMouse():
            return
        self._popup.show_for(self._widget, self._text)

    def _hide_hint(self):
        self._timer.stop()
        self._popup.hide()

    def _cleanup(self, *_args):
        self._hide_hint()
        self._widget = None
        self._popup.deleteLater()

    def set_text(self, text: str, delay_ms: int | None = None):
        self._text = str(text or "")
        if delay_ms is not None and delay_ms > 0:
            self._timer.setInterval(delay_ms)
        self._hide_hint()
        if self._widget is not None:
            self._widget.setToolTip("")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        event_type = event.type()
        if event_type in (QEvent.Type.Enter, QEvent.Type.ToolTip):
            if event_type == QEvent.Type.Enter:
                self._timer.start()
            return event_type == QEvent.Type.ToolTip
        if event_type in (
            QEvent.Type.Leave,
            QEvent.Type.Hide,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.FocusOut,
        ):
            self._hide_hint()
        return super().eventFilter(watched, event)


def set_hover_hint(widget: QWidget, text: str, delay_ms: int = 450):
    controller = getattr(widget, "_hover_hint_controller", None)
    if isinstance(controller, _HoverHintController):
        controller.set_text(text, delay_ms=delay_ms)
        return controller

    controller = _HoverHintController(widget, text, delay_ms=delay_ms)
    setattr(widget, "_hover_hint_controller", controller)
    return controller


def install_hover_hint(widget: QWidget, text: str, delay_ms: int = 450):
    return set_hover_hint(widget, text, delay_ms=delay_ms)
