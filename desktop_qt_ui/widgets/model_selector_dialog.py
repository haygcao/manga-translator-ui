"""带搜索功能的模型选择对话框"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QListWidget, QPushButton, QLabel, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class ModelSelectorDialog(QDialog):
    """带搜索功能的模型选择对话框"""
    
    model_selected = pyqtSignal(str)
    
    def __init__(self, models: list[str], title: str = "选择模型", 
                 prompt: str = "可用模型：", parent=None):
        super().__init__(parent)
        self.models = models
        self.selected_model = None
        
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._setup_ui(prompt)
        self._populate_list()
        
    def _setup_ui(self, prompt: str):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 提示标签
        prompt_label = QLabel(prompt)
        layout.addWidget(prompt_label)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索模型...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 模型列表
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.model_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 连接列表选择事件
        self.model_list.itemSelectionChanged.connect(self._on_selection_changed)
        
    def _populate_list(self, filter_text: str = ""):
        """填充模型列表"""
        self.model_list.clear()
        
        filter_text = filter_text.lower()
        for model in self.models:
            if not filter_text or filter_text in model.lower():
                item = QListWidgetItem(model)
                self.model_list.addItem(item)
        
        # 如果只有一个结果，自动选中
        if self.model_list.count() == 1:
            self.model_list.setCurrentRow(0)
    
    def _on_search_text_changed(self, text: str):
        """搜索文本变化"""
        self._populate_list(text)
    
    def _on_selection_changed(self):
        """选择变化"""
        has_selection = len(self.model_list.selectedItems()) > 0
        self.ok_button.setEnabled(has_selection)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击列表项"""
        self.selected_model = item.text()
        self.accept()
    
    def _on_ok_clicked(self):
        """点击确定按钮"""
        selected_items = self.model_list.selectedItems()
        if selected_items:
            self.selected_model = selected_items[0].text()
            self.accept()
    
    def get_selected_model(self) -> str | None:
        """获取选中的模型"""
        return self.selected_model
    
    @staticmethod
    def get_model(models: list[str], title: str = "选择模型", 
                  prompt: str = "可用模型：", parent=None) -> tuple[str | None, bool]:
        """静态方法：显示对话框并返回选中的模型
        
        Returns:
            (selected_model, ok): 选中的模型和是否点击了确定
        """
        dialog = ModelSelectorDialog(models, title, prompt, parent)
        result = dialog.exec()
        return dialog.get_selected_model(), result == QDialog.DialogCode.Accepted
