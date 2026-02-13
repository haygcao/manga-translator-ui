
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon, QAction
from PyQt6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QMenu,
    QWidget,
)

import logging

logger = logging.getLogger('manga_translator')


class ColorPickerWidget(QWidget):
    """可复用的颜色选择器组件，包含颜色按钮、RGB标签、复制/粘贴、常用颜色菜单。"""

    color_changed = pyqtSignal(str)  # 颜色变化时发出 hex 颜色值

    # 类级别的颜色剪贴板，所有实例共享
    _color_clipboard = None

    def __init__(self, dialog_title="Select color", default_color="#000000",
                 config_key="saved_colors", config_service=None, i18n_func=None,
                 parent=None):
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._default_color = default_color
        self._current_color = default_color
        self._config_key = config_key
        self._config_service = config_service
        self._t = i18n_func or (lambda s, **kw: s)

        self._saved_colors = []
        self._load_saved_colors()
        self._init_ui()
        self._connect_signals()

    # ── UI ────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 主颜色按钮
        self.color_button = QPushButton()
        self.color_button.setMinimumWidth(60)
        self.color_button.setToolTip(self._t("Click to select color"))
        self.color_button.setStyleSheet(f"background-color: {self._current_color};")
        layout.addWidget(self.color_button, 2)

        # RGB 显示标签
        self.rgb_label = QLabel("RGB: -")
        self.rgb_label.setStyleSheet("font-size: 10px;")
        self.rgb_label.setMinimumWidth(80)
        layout.addWidget(self.rgb_label, 1)

        # 复制按钮
        self.copy_button = QPushButton(self._t("Copy"))
        self.copy_button.setToolTip(self._t("Copy current color"))
        self.copy_button.setMaximumWidth(50)
        layout.addWidget(self.copy_button)

        # 粘贴按钮
        self.paste_button = QPushButton(self._t("Paste"))
        self.paste_button.setToolTip(self._t("Paste copied color"))
        self.paste_button.setMaximumWidth(50)
        self.paste_button.setEnabled(ColorPickerWidget._color_clipboard is not None)
        layout.addWidget(self.paste_button)

        # ★ 常用颜色按钮
        self.saved_colors_button = QToolButton()
        self.saved_colors_button.setText("★")
        self.saved_colors_button.setToolTip(self._t("Saved colors menu"))
        self.saved_colors_button.setMaximumWidth(30)
        self.saved_colors_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(self.saved_colors_button)

        self._rebuild_saved_colors_menu()

    def _connect_signals(self):
        self.color_button.clicked.connect(self._on_color_clicked)
        self.copy_button.clicked.connect(self._on_copy)
        self.paste_button.clicked.connect(self._on_paste)

    # ── Public API ────────────────────────────────────────────────

    def set_color(self, hex_color: str):
        """设置当前颜色（更新按钮样式和 RGB 标签），不发射信号。"""
        self._current_color = hex_color
        self.color_button.setStyleSheet(f"background-color: {hex_color};")
        self._update_rgb_label(hex_color)

    def get_color(self) -> str:
        """获取当前颜色 hex 值。"""
        return self._current_color

    def reset(self, default_color: str | None = None):
        """重置为默认颜色，不发射信号。"""
        color = default_color or self._default_color
        self.set_color(color)

    def refresh_ui_texts(self):
        """语言切换时刷新按钮文本。"""
        self.color_button.setToolTip(self._t("Click to select color"))
        self.copy_button.setText(self._t("Copy"))
        self.copy_button.setToolTip(self._t("Copy current color"))
        self.paste_button.setText(self._t("Paste"))
        self.paste_button.setToolTip(self._t("Paste copied color"))
        self.saved_colors_button.setToolTip(self._t("Saved colors menu"))
        self._rebuild_saved_colors_menu()

    # ── 颜色对话框 ───────────────────────────────────────────────

    def _on_color_clicked(self):
        current = QColor(self._current_color) if self._current_color else QColor("black")

        dialog = QColorDialog(current, self)
        dialog.setWindowTitle(self._t(self._dialog_title))
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)

        # 将保存的常用颜色加载到对话框的自定义颜色槽
        for i, color_hex in enumerate(self._saved_colors[:16]):
            dialog.setCustomColor(i, QColor(color_hex))

        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            hex_color = dialog.currentColor().name()
            self._apply_color(hex_color)

            # 自动保存到常用颜色
            if hex_color not in self._saved_colors:
                self._saved_colors.insert(0, hex_color)
                if len(self._saved_colors) > 20:
                    self._saved_colors = self._saved_colors[:20]
                self._persist_saved_colors()
                self._rebuild_saved_colors_menu()

    def _apply_color(self, hex_color: str):
        """应用颜色并发射信号。"""
        self.set_color(hex_color)
        self.color_changed.emit(hex_color)

    # ── 复制 / 粘贴 ──────────────────────────────────────────────

    def _on_copy(self):
        if self._current_color:
            ColorPickerWidget._color_clipboard = self._current_color
            # 启用所有实例的粘贴按钮
            for widget in self._all_instances():
                widget.paste_button.setEnabled(True)
            # 视觉反馈
            self.copy_button.setStyleSheet("background-color: #90EE90;")
            QTimer.singleShot(200, lambda: self.copy_button.setStyleSheet(""))

    def _on_paste(self):
        if ColorPickerWidget._color_clipboard:
            self._apply_color(ColorPickerWidget._color_clipboard)

    def _all_instances(self):
        """获取同一父层级中所有 ColorPickerWidget 实例。"""
        top = self.window()
        if top:
            return top.findChildren(ColorPickerWidget)
        return [self]

    # ── RGB 标签 ──────────────────────────────────────────────────

    def _update_rgb_label(self, hex_color: str):
        try:
            c = QColor(hex_color)
            self.rgb_label.setText(f"RGB: {c.red()},{c.green()},{c.blue()}")
        except Exception:
            self.rgb_label.setText("RGB: -")

    # ── 常用颜色菜单 ─────────────────────────────────────────────

    def _rebuild_saved_colors_menu(self):
        menu = QMenu(self)

        if self._saved_colors:
            for color_hex in self._saved_colors:
                action = QAction(self)
                action.setIcon(self._create_color_icon(color_hex))
                c = QColor(color_hex)
                action.setText(f"{color_hex}  (R:{c.red()} G:{c.green()} B:{c.blue()})")
                action.triggered.connect(lambda checked, ch=color_hex: self._apply_color(ch))
                menu.addAction(action)
            menu.addSeparator()

        save_action = QAction(self._t("Save current color"), self)
        save_action.triggered.connect(self._save_current_color)
        menu.addAction(save_action)

        if self._saved_colors:
            clear_action = QAction(self._t("Clear saved colors"), self)
            clear_action.triggered.connect(self._clear_saved_colors)
            menu.addAction(clear_action)

        self.saved_colors_button.setMenu(menu)

    def _save_current_color(self):
        if self._current_color and self._current_color not in self._saved_colors:
            self._saved_colors.insert(0, self._current_color)
            if len(self._saved_colors) > 20:
                self._saved_colors = self._saved_colors[:20]
            self._persist_saved_colors()
            self._rebuild_saved_colors_menu()

    def _clear_saved_colors(self):
        self._saved_colors = []
        self._persist_saved_colors()
        self._rebuild_saved_colors_menu()

    # ── 持久化 ────────────────────────────────────────────────────

    def _load_saved_colors(self):
        if not self._config_service:
            return
        try:
            config = self._config_service.get_config()
            colors = getattr(config.app, self._config_key, None)
            if colors:
                self._saved_colors = list(colors)
            else:
                self._saved_colors = []
        except Exception as e:
            logger.warning(f"加载保存的颜色失败 ({self._config_key}): {e}")
            self._saved_colors = []

    def _persist_saved_colors(self):
        if not self._config_service:
            return
        try:
            self._config_service.update_config({
                'app': {
                    self._config_key: self._saved_colors
                }
            })
            self._config_service.save_config_file()
        except Exception as e:
            logger.error(f"保存颜色失败 ({self._config_key}): {e}")

    # ── 工具方法 ──────────────────────────────────────────────────

    @staticmethod
    def _create_color_icon(hex_color: str) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(hex_color))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#888888"))
        painter.drawRect(0, 0, 15, 15)
        painter.end()
        return QIcon(pixmap)
