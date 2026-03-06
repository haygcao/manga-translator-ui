import json
from typing import Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from main_view_parts.theme import get_current_theme, get_current_theme_colors


def _tokens() -> dict[str, str]:
    colors = get_current_theme_colors()
    return {
        **colors,
        "fg": colors["text_primary"],
        "fg_dim": colors["text_muted"],
        "fg_bright": colors["text_page_title"],
        "bg_dialog": colors["bg_panel"],
        "bg_card": colors["bg_surface_raised"],
        "bg_soft": colors["bg_surface_soft"],
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
        "status_success": "#2E9D57" if get_current_theme() == "light" else "#6BCB77",
        "status_error": "#D94C4C" if get_current_theme() == "light" else "#FF7B7B",
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
        QLabel#dialog_subtitle {{
            color: {t["fg_dim"]};
            font-size: 12px;
        }}
        QLabel#section_label {{
            color: {t["fg_bright"]};
            font-size: 12px;
            font-weight: 600;
        }}
        QLabel#hint_label {{
            color: {t["fg_dim"]};
            font-size: 12px;
            padding: 2px 0;
        }}
        QLabel#null_value_label {{
            color: {t["fg_dim"]};
            background: {t["bg_soft"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
            padding: 7px 10px;
        }}
        QFrame#divider {{
            background: {t["border"]};
            max-height: 1px;
            border: none;
        }}
        QWidget#params_card,
        QWidget#path_card {{
            background: {t["bg_card"]};
            border: 1px solid {t["border"]};
            border-radius: 12px;
        }}
        QWidget#param_row {{
            background: {t["bg_soft"]};
            border: 1px solid {t["border"]};
            border-radius: 12px;
        }}
        QLineEdit,
        QComboBox,
        QPlainTextEdit {{
            background: {t["bg_input"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
            color: {t["fg"]};
            padding: 7px 10px;
        }}
        QLineEdit:focus,
        QComboBox:focus,
        QPlainTextEdit:focus {{
            border-color: {t["border_focus"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 18px;
        }}
        QComboBox::down-arrow {{
            width: 10px;
            height: 10px;
        }}
        QComboBoxPrivateContainer {{
            background: {t["bg_card"]};
            background-color: {t["bg_card"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {t["bg_card"]};
            background-color: {t["bg_card"]};
            alternate-background-color: {t["bg_card"]};
            color: {t["fg"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
            padding: 4px;
            outline: 0;
            selection-background-color: {t["primary_bg"]};
            selection-color: {t["primary_text"]};
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 26px;
            padding: 4px 8px;
            border-radius: 6px;
            background: transparent;
            background-color: transparent;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: {t["primary_bg"]};
            background-color: {t["primary_bg"]};
            color: {t["primary_text"]};
        }}
        QPlainTextEdit {{
            padding: 10px;
        }}
        QTabWidget::pane {{
            border: 1px solid {t["border"]};
            border-radius: 10px;
            background: {t["bg_card"]};
            padding: 6px;
        }}
        QTabBar::tab {{
            background: {t["soft_bg"]};
            border: 1px solid {t["soft_border"]};
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            color: {t["soft_text"]};
            padding: 8px 14px;
            margin-right: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background: {t["primary_bg"]};
            border-color: {t["primary_border"]};
            color: {t["primary_text"]};
        }}
        QTabBar::tab:hover:!selected {{
            background: {t["soft_hover"]};
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QPushButton {{
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


def _monospace_font(size: int = 11) -> QFont:
    font = QFont("Consolas", size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "string"
    return "json"


class CustomApiParamRow(QWidget):
    remove_requested = pyqtSignal(QWidget)

    def __init__(self, t_func: Callable[[str], str] | None = None, parent=None):
        super().__init__(parent)
        self._t = t_func or (lambda text: text)
        self.setObjectName("param_row")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        key_col = QVBoxLayout()
        key_col.setSpacing(6)
        key_label = QLabel(self._t("Key"))
        key_label.setObjectName("section_label")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("temperature")
        self.key_input.setMinimumWidth(180)
        key_col.addWidget(key_label)
        key_col.addWidget(self.key_input)
        layout.addLayout(key_col, 3)

        type_col = QVBoxLayout()
        type_col.setSpacing(6)
        type_label = QLabel(self._t("Type"))
        type_label.setObjectName("section_label")
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(118)
        self.type_combo.setView(QListView())
        for label, value in [
            (self._t("String"), "string"),
            (self._t("Number"), "number"),
            (self._t("Boolean"), "boolean"),
            (self._t("Null"), "null"),
            ("JSON", "json"),
        ]:
            self.type_combo.addItem(label, value)
        type_col.addWidget(type_label)
        type_col.addWidget(self.type_combo)
        layout.addLayout(type_col, 2)

        value_col = QVBoxLayout()
        value_col.setSpacing(6)
        value_label = QLabel(self._t("Value"))
        value_label.setObjectName("section_label")
        self.value_stack = QStackedWidget()

        self.string_input = QLineEdit()
        self.string_input.setPlaceholderText("gpt-4o-mini")

        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("0.2")
        self.number_input.setFont(_monospace_font(10))

        self.boolean_input = QComboBox()
        self.boolean_input.setView(QListView())
        self.boolean_input.addItem("true", True)
        self.boolean_input.addItem("false", False)

        self.null_label = QLabel("null")
        self.null_label.setObjectName("null_value_label")
        self.null_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.json_input = QLineEdit()
        self.json_input.setPlaceholderText('{"type": "json"}')
        self.json_input.setFont(_monospace_font(10))

        self.value_stack.addWidget(self.string_input)
        self.value_stack.addWidget(self.number_input)
        self.value_stack.addWidget(self.boolean_input)
        self.value_stack.addWidget(self.null_label)
        self.value_stack.addWidget(self.json_input)

        value_col.addWidget(value_label)
        value_col.addWidget(self.value_stack)
        layout.addLayout(value_col, 4)

        remove_col = QVBoxLayout()
        remove_col.setSpacing(6)
        remove_col.addWidget(QLabel(""))
        self.remove_button = QPushButton(self._t("Delete"))
        self.remove_button.setProperty("role", "soft")
        self.remove_button.setFixedWidth(80)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        remove_col.addWidget(self.remove_button)
        remove_col.addStretch(1)
        layout.addLayout(remove_col)

        self.type_combo.currentIndexChanged.connect(self._sync_type_editor)
        self._sync_type_editor()

    def _sync_type_editor(self):
        current_type = self.type_combo.currentData()
        index_map = {
            "string": 0,
            "number": 1,
            "boolean": 2,
            "null": 3,
            "json": 4,
        }
        self.value_stack.setCurrentIndex(index_map.get(current_type, 0))

    def set_entry(self, key: str, value: Any):
        self.key_input.setText(key)
        value_type = _infer_type(value)
        combo_index = self.type_combo.findData(value_type)
        if combo_index >= 0:
            self.type_combo.setCurrentIndex(combo_index)

        if value_type == "string":
            self.string_input.setText(value)
        elif value_type == "number":
            self.number_input.setText(str(value))
        elif value_type == "boolean":
            bool_index = self.boolean_input.findData(bool(value))
            self.boolean_input.setCurrentIndex(max(bool_index, 0))
        elif value_type == "json":
            self.json_input.setText(json.dumps(value, ensure_ascii=False))

        self._sync_type_editor()

    def _parse_number(self) -> int | float:
        raw = self.number_input.text().strip()
        if not raw:
            raise ValueError(self._t("Number value is empty"))
        parsed = json.loads(raw)
        if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
            raise ValueError(self._t("Number value is invalid"))
        return parsed

    def _parse_json_value(self) -> Any:
        raw = self.json_input.text().strip()
        if not raw:
            raise ValueError(self._t("JSON value is empty"))
        return json.loads(raw)

    def get_entry(self) -> tuple[str, Any]:
        key = self.key_input.text().strip()
        if not key:
            raise ValueError(self._t("Parameter name cannot be empty"))

        value_type = self.type_combo.currentData()
        if value_type == "string":
            value = self.string_input.text()
        elif value_type == "number":
            value = self._parse_number()
        elif value_type == "boolean":
            value = self.boolean_input.currentData()
        elif value_type == "null":
            value = None
        else:
            value = self._parse_json_value()
        return key, value


class CustomApiParamsEditorDialog(QDialog):
    def __init__(self, file_path: str, t_func: Callable[[str], str] | None = None, parent=None):
        super().__init__(parent)
        self._t = t_func or (lambda text: text)
        self._file_path = file_path
        self._original_content = ""
        self._setup_ui()
        self._load_from_disk()

    def _setup_ui(self):
        self.setWindowTitle(self._t("Edit Custom API Params"))
        self.setMinimumSize(880, 620)
        self.resize(980, 720)
        self.setStyleSheet(_dialog_stylesheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel(self._t("Edit Custom API Params"))
        title.setObjectName("dialog_title")
        subtitle = QLabel(self._t("Edit custom API request parameters passed directly to the translator backend."))
        subtitle.setObjectName("dialog_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_params_tab()
        self._build_raw_tab()

        self.status_label = QLabel("")
        self.status_label.setObjectName("hint_label")
        root.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self.refresh_button = QPushButton(self._t("Refresh"))
        self.refresh_button.setProperty("role", "soft")
        self.refresh_button.clicked.connect(self._load_from_disk)

        self.cancel_button = QPushButton(self._t("Cancel"))
        self.cancel_button.setProperty("role", "soft")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton(self._t("Save"))
        self.save_button.setProperty("role", "primary")
        self.save_button.clicked.connect(self._save)

        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.save_button)
        root.addLayout(button_row)

    def _build_params_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(8, 8, 8, 8)
        page_layout.setSpacing(8)

        card = QWidget()
        card.setObjectName("path_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(4)
        title = QLabel(self._t("Top-level API Params"))
        title.setObjectName("section_label")
        hint = QLabel(self._t("Supports string, number, boolean, null and JSON values."))
        hint.setObjectName("hint_label")
        hint.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(hint)
        page_layout.addWidget(card)

        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.params_scroll_content = QWidget()
        self.params_scroll_content.setStyleSheet("background: transparent;")
        self.params_layout = QVBoxLayout(self.params_scroll_content)
        self.params_layout.setContentsMargins(0, 0, 0, 0)
        self.params_layout.setSpacing(10)
        self.params_layout.addStretch(1)
        self.params_scroll.setWidget(self.params_scroll_content)
        page_layout.addWidget(self.params_scroll, 1)

        add_row = QHBoxLayout()
        add_row.addStretch(1)
        self.add_param_button = QPushButton("+ " + self._t("Add Row"))
        self.add_param_button.setProperty("role", "soft")
        self.add_param_button.clicked.connect(lambda: self._append_row())
        add_row.addWidget(self.add_param_button)
        page_layout.addLayout(add_row)

        self.tabs.addTab(page, self._t("Template Edit"))

    def _build_raw_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(8, 8, 8, 8)
        page_layout.setSpacing(8)

        hint = QLabel(self._t("Edit the raw file content directly"))
        hint.setObjectName("hint_label")
        page_layout.addWidget(hint)

        self.raw_editor = QPlainTextEdit()
        self.raw_editor.setFont(_monospace_font())
        self.raw_editor.setTabStopDistance(28)
        page_layout.addWidget(self.raw_editor, 1)

        self.tabs.addTab(page, self._t("Raw Edit"))

    def _insert_row_widget(self, row: CustomApiParamRow):
        row.remove_requested.connect(self._remove_row)
        insert_index = max(self.params_layout.count() - 1, 0)
        self.params_layout.insertWidget(insert_index, row)

    def _append_row(self, key: str = "", value: Any = ""):
        row = CustomApiParamRow(t_func=self._t, parent=self.params_scroll_content)
        if key:
            row.set_entry(key, value)
        self._insert_row_widget(row)
        return row

    def _clear_rows(self):
        while self.params_layout.count() > 1:
            item = self.params_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _remove_row(self, row: QWidget):
        row.setParent(None)
        row.deleteLater()

    def _load_from_disk(self):
        try:
            with open(self._file_path, "r", encoding="utf-8") as handle:
                content = handle.read().strip()
        except FileNotFoundError:
            content = "{}"
        except Exception as exc:
            self._set_status(f"{self._t('Load failed')}: {exc}", kind="error")
            return

        if not content:
            content = "{}"

        self._original_content = content
        self.raw_editor.setPlainText(content)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            self._clear_rows()
            self._append_row()
            self._set_status(f"{self._t('JSON format error')}: {exc}", kind="error")
            return

        if not isinstance(parsed, dict):
            self._clear_rows()
            self._append_row()
            self._set_status(self._t("JSON root must be an object"), kind="error")
            return

        self._populate_rows(parsed)
        self._set_status(self._t("Loaded successfully"))

    def _populate_rows(self, data: dict[str, Any]):
        self._clear_rows()
        if not data:
            self._append_row()
            return
        for key, value in data.items():
            self._append_row(key, value)

    def _collect_structured_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        row_widgets = self.params_scroll_content.findChildren(CustomApiParamRow, options=Qt.FindChildOption.FindDirectChildrenOnly)
        if not row_widgets:
            return {}

        for row in row_widgets:
            key, value = row.get_entry()
            if key in data:
                raise ValueError(self._t("Duplicate parameter name: {name}", name=key))
            data[key] = value
        return data

    def _collect_raw_data(self) -> dict[str, Any]:
        content = self.raw_editor.toPlainText().strip() or "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError(self._t("JSON root must be an object"))
        return parsed

    def _set_status(self, message: str, kind: str = "default"):
        if kind == "success":
            color = _tokens()["status_success"]
        elif kind == "error":
            color = _tokens()["status_error"]
        else:
            color = _tokens()["fg_dim"]
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)

    def _save(self):
        try:
            if self.tabs.currentIndex() == 0:
                data = self._collect_structured_data()
            else:
                data = self._collect_raw_data()
        except json.JSONDecodeError as exc:
            self._set_status(f"{self._t('JSON format error')}: {exc}", kind="error")
            return
        except ValueError as exc:
            self._set_status(str(exc), kind="error")
            return

        content = json.dumps(data, indent=2, ensure_ascii=False)
        try:
            with open(self._file_path, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.write("\n")
        except Exception as exc:
            self._set_status(f"{self._t('Save failed')}: {exc}", kind="error")
            return

        self._original_content = content
        self.raw_editor.setPlainText(content)
        self._populate_rows(data)
        self._set_status(self._t("Saved successfully"), kind="success")

    def get_was_modified(self) -> bool:
        current = self.raw_editor.toPlainText().strip()
        return current != self._original_content.strip()
