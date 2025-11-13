# -*- coding: utf-8 -*-
"""
现代化文件夹选择器对话框
支持多选、快捷栏、路径导航等功能
"""

import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal
from PyQt6.QtGui import QIcon, QFileSystemModel, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeView,
    QListView, QSplitter, QLineEdit, QLabel, QWidget, QFileIconProvider,
    QMessageBox, QAbstractItemView
)


class FolderDialog(QDialog):
    """现代化文件夹选择对话框"""

    def __init__(self, parent=None, start_dir: str = "", multi_select: bool = True):
        super().__init__(parent)
        self.multi_select = multi_select
        self.selected_folders: List[str] = []

        self.setWindowTitle("选择文件夹" + (" (可多选)" if multi_select else ""))
        self.setMinimumSize(900, 600)
        self.resize(900, 600)

        # 初始化文件系统模型
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.rootPath())
        self.fs_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)

        self._init_ui()
        self._connect_signals()

        # 设置初始目录
        if start_dir and os.path.isdir(start_dir):
            self.navigate_to(start_dir)
        else:
            self.navigate_to(str(Path.home()))

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 顶部路径栏
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("当前路径:"))

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("输入路径后按回车跳转")
        path_layout.addWidget(self.path_edit, 1)

        self.go_button = QPushButton("跳转")
        path_layout.addWidget(self.go_button)

        self.parent_button = QPushButton("上级目录")
        path_layout.addWidget(self.parent_button)

        layout.addLayout(path_layout)

        # 主内容区域：左侧快捷栏 + 右侧文件夹树
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧快捷栏
        shortcuts_widget = self._create_shortcuts_panel()
        splitter.addWidget(shortcuts_widget)

        # 右侧文件夹树形视图
        self.folder_tree = QTreeView()
        self.folder_tree.setModel(self.fs_model)

        # 只显示名称列
        for i in range(1, self.fs_model.columnCount()):
            self.folder_tree.hideColumn(i)

        # 设置多选模式
        if self.multi_select:
            self.folder_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        else:
            self.folder_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.folder_tree.setHeaderHidden(False)
        self.folder_tree.setSortingEnabled(True)
        self.folder_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        splitter.addWidget(self.folder_tree)

        # 设置分割比例：快捷栏占20%，文件夹树占80%
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)

        layout.addWidget(splitter, 1)

        # 底部提示和选中信息
        info_layout = QHBoxLayout()

        if self.multi_select:
            tip_label = QLabel("💡 提示：按住 Ctrl 或 Shift 可以多选文件夹")
            tip_label.setStyleSheet("color: #666;")
            info_layout.addWidget(tip_label)

        info_layout.addStretch()

        self.selection_label = QLabel("未选择")
        self.selection_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        info_layout.addWidget(self.selection_label)

        layout.addLayout(info_layout)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumWidth(80)
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _create_shortcuts_panel(self) -> QWidget:
        """创建左侧快捷栏"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        label = QLabel("快捷访问")
        label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(label)

        # 创建快捷方式列表
        self.shortcuts_list = QListView()
        self.shortcuts_model = QStandardItemModel()
        self.shortcuts_list.setModel(self.shortcuts_model)
        self.shortcuts_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # 添加常用快捷方式
        self._add_shortcut("🏠 用户目录", str(Path.home()))
        self._add_shortcut("📁 桌面", str(Path.home() / "Desktop"))
        self._add_shortcut("📄 文档", str(Path.home() / "Documents"))
        self._add_shortcut("📥 下载", str(Path.home() / "Downloads"))
        self._add_shortcut("🖼️ 图片", str(Path.home() / "Pictures"))

        # 添加所有驱动器
        drives = QDir.drives()
        for drive in drives:
            drive_path = drive.absolutePath()
            self._add_shortcut(f"💾 {drive_path}", drive_path)

        layout.addWidget(self.shortcuts_list)

        return widget

    def _add_shortcut(self, name: str, path: str):
        """添加快捷方式"""
        if os.path.exists(path):
            item = QStandardItem(name)
            item.setData(path, Qt.ItemDataRole.UserRole)
            item.setToolTip(path)
            self.shortcuts_model.appendRow(item)

    def _connect_signals(self):
        """连接信号"""
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.go_button.clicked.connect(self._on_go_clicked)
        self.parent_button.clicked.connect(self._go_parent)
        self.path_edit.returnPressed.connect(self._on_go_clicked)

        self.folder_tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.folder_tree.doubleClicked.connect(self._on_folder_double_clicked)

        self.shortcuts_list.clicked.connect(self._on_shortcut_clicked)

    def navigate_to(self, path: str):
        """导航到指定路径"""
        if not os.path.isdir(path):
            return

        index = self.fs_model.index(path)
        if index.isValid():
            self.folder_tree.setRootIndex(index.parent())
            self.folder_tree.setCurrentIndex(index)
            self.folder_tree.expand(index)
            self.folder_tree.scrollTo(index)
            self.path_edit.setText(path)

    def _on_go_clicked(self):
        """跳转按钮点击"""
        path = self.path_edit.text().strip()
        if path and os.path.isdir(path):
            self.navigate_to(path)
        else:
            QMessageBox.warning(self, "路径错误", f"路径不存在或不是有效目录：\n{path}")

    def _go_parent(self):
        """返回上级目录"""
        current_path = self.path_edit.text().strip()
        if current_path:
            parent_path = str(Path(current_path).parent)
            if parent_path != current_path:  # 确保不是根目录
                self.navigate_to(parent_path)

    def _on_shortcut_clicked(self, index: QModelIndex):
        """快捷方式点击"""
        path = self.shortcuts_model.itemFromIndex(index).data(Qt.ItemDataRole.UserRole)
        if path:
            self.navigate_to(path)

    def _on_folder_double_clicked(self, index: QModelIndex):
        """文件夹双击：进入该文件夹"""
        path = self.fs_model.filePath(index)
        if os.path.isdir(path):
            self.navigate_to(path)

    def _on_selection_changed(self):
        """选择改变时更新状态"""
        indexes = self.folder_tree.selectionModel().selectedIndexes()
        self.selected_folders = [self.fs_model.filePath(idx) for idx in indexes]

        count = len(self.selected_folders)
        if count == 0:
            self.selection_label.setText("未选择")
            self.ok_button.setEnabled(False)
        elif count == 1:
            folder_name = os.path.basename(self.selected_folders[0])
            self.selection_label.setText(f"已选择: {folder_name}")
            self.ok_button.setEnabled(True)
        else:
            self.selection_label.setText(f"已选择 {count} 个文件夹")
            self.ok_button.setEnabled(True)

    def get_selected_folders(self) -> List[str]:
        """获取选中的文件夹列表"""
        return self.selected_folders


def select_folders(parent=None, start_dir: str = "", multi_select: bool = True) -> Optional[List[str]]:
    """
    显示文件夹选择对话框

    Args:
        parent: 父窗口
        start_dir: 起始目录
        multi_select: 是否支持多选

    Returns:
        选中的文件夹路径列表，如果取消则返回 None
    """
    dialog = FolderDialog(parent, start_dir, multi_select)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_folders()
    return None
