from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from main_view_parts.theme import apply_widget_stylesheet, get_current_theme_colors


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
        "border_hover": colors["border_input_hover"],
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
        "list_hover": colors["tab_hover"],
        "list_selected": colors["dropdown_selection"],
        "list_selected_text": colors["list_item_selected_text"],
    }


def _dialog_stylesheet() -> str:
    t = _tokens()
    return f"""
        QDialog#modelSelectorDialog {{
            background: {t["bg_dialog"]};
        }}
        QLabel {{
            background: transparent;
            color: {t["fg"]};
        }}
        QLabel#promptLabel {{
            color: {t["fg_bright"]};
            font-size: 13px;
            font-weight: 700;
        }}
        QLineEdit#searchInput {{
            min-height: 34px;
            background: {t["bg_input"]};
            border: 1px solid {t["border"]};
            border-radius: 10px;
            color: {t["fg"]};
            padding: 7px 12px;
        }}
        QLineEdit#searchInput:hover {{
            border-color: {t["border_hover"]};
        }}
        QLineEdit#searchInput:focus {{
            border-color: {t["border_focus"]};
        }}
        QListWidget#modelList {{
            background: {t["bg_card"]};
            border: 1px solid {t["border"]};
            border-radius: 12px;
            color: {t["fg"]};
            outline: 0;
            padding: 6px;
        }}
        QListWidget#modelList::item {{
            min-height: 30px;
            padding: 6px 10px;
            border-radius: 8px;
            background: transparent;
            color: {t["fg"]};
        }}
        QListWidget#modelList::item:hover {{
            background: {t["list_hover"]};
            color: {t["fg_bright"]};
        }}
        QListWidget#modelList::item:selected {{
            background: {t["list_selected"]};
            color: {t["list_selected_text"]};
        }}
        QPushButton {{
            min-width: 0;
            min-height: 30px;
            border-radius: 10px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton#secondaryButton {{
            background: {t["soft_bg"]};
            border: 1px solid {t["soft_border"]};
            color: {t["soft_text"]};
        }}
        QPushButton#secondaryButton:hover {{
            background: {t["soft_hover"]};
        }}
        QPushButton#secondaryButton:pressed {{
            background: {t["soft_pressed"]};
        }}
        QPushButton#primaryButton {{
            background: {t["primary_bg"]};
            border: 1px solid {t["primary_border"]};
            color: {t["primary_text"]};
        }}
        QPushButton#primaryButton:hover {{
            background: {t["primary_hover"]};
        }}
        QPushButton#primaryButton:pressed {{
            background: {t["primary_pressed"]};
        }}
        QPushButton#primaryButton:disabled {{
            background: {t["btn_disabled_bg"]};
            border: 1px solid {t["btn_disabled_border"]};
            color: {t["text_disabled"]};
        }}
    """


def _default_t(text: str, **kwargs) -> str:
    if kwargs:
        return text.format(**kwargs)
    return text


class ModelSelectorDialog(QDialog):
    """带搜索功能的模型选择对话框"""

    model_selected = pyqtSignal(str)

    def __init__(
        self,
        models: list[str],
        title: str = "选择模型",
        prompt: str = "可用模型：",
        parent=None,
        t_func: Callable[..., str] | None = None,
    ):
        super().__init__(parent)
        self.models = models
        self.selected_model = None
        self._t = t_func or _default_t

        self.setObjectName("modelSelectorDialog")
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self.setModal(True)

        self._setup_ui(prompt)
        self._populate_list()
        apply_widget_stylesheet(self, _dialog_stylesheet())

    def _setup_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        prompt_label = QLabel(prompt)
        prompt_label.setObjectName("promptLabel")
        layout.addWidget(prompt_label)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText(self._t("Search models..."))
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)

        self.model_list = QListWidget()
        self.model_list.setObjectName("modelList")
        self.model_list.setAlternatingRowColors(False)
        self.model_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.model_list, 1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        self.ok_button = QPushButton(self._t("OK"))
        self.ok_button.setObjectName("primaryButton")
        self.ok_button.setFixedSize(112, 38)
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)

        cancel_button = QPushButton(self._t("Cancel"))
        cancel_button.setObjectName("secondaryButton")
        cancel_button.setFixedSize(112, 38)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)

        self.model_list.itemSelectionChanged.connect(self._on_selection_changed)

    def _populate_list(self, filter_text: str = ""):
        self.model_list.clear()

        filter_text = filter_text.lower()
        for model in self.models:
            if not filter_text or filter_text in model.lower():
                self.model_list.addItem(QListWidgetItem(model))

        if self.model_list.count() == 1:
            self.model_list.setCurrentRow(0)

    def _on_search_text_changed(self, text: str):
        self._populate_list(text)

    def _on_selection_changed(self):
        self.ok_button.setEnabled(bool(self.model_list.selectedItems()))

    def _on_item_double_clicked(self, item: QListWidgetItem):
        self.selected_model = item.text()
        self.accept()

    def _on_ok_clicked(self):
        selected_items = self.model_list.selectedItems()
        if selected_items:
            self.selected_model = selected_items[0].text()
            self.accept()

    def get_selected_model(self) -> str | None:
        return self.selected_model

    @staticmethod
    def get_model(
        models: list[str],
        title: str = "选择模型",
        prompt: str = "可用模型：",
        parent=None,
        t_func: Callable[..., str] | None = None,
    ) -> tuple[str | None, bool]:
        dialog = ModelSelectorDialog(models, title, prompt, parent=parent, t_func=t_func)
        result = dialog.exec()
        return dialog.get_selected_model(), result == QDialog.DialogCode.Accepted
