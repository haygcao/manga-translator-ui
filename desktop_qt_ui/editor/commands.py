
import copy
from typing import Any, Dict, TYPE_CHECKING

import numpy as np
from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from desktop_qt_ui.editor.editor_model import EditorModel

class UpdateRegionCommand(QUndoCommand):
    """用于更新单个区域数据的通用命令。"""
    def __init__(self, model: "EditorModel", region_index: int, old_data: Dict[str, Any], new_data: Dict[str, Any], description: str = "Update Region"):
        super().__init__(description)
        self._model = model
        self._index = region_index
        # 存储深拷贝以防止后续修改影响历史状态
        self._old_data = copy.deepcopy(old_data)
        self._new_data = copy.deepcopy(new_data)

    def _apply_data(self, data_to_apply: Dict[str, Any]):
        """将给定的数据字典应用到模型中的区域。"""
        regions = self._model.get_regions()
        if not (0 <= self._index < len(regions)):
            return

        # 检查 center 是否改变
        old_center = regions[self._index].get('center')
        new_center = data_to_apply.get('center')
        center_changed = old_center != new_center

        # 更新区域数据
        regions[self._index] = data_to_apply
        # set_regions_silent 只同步到 resource_manager，不 emit 信号
        # 由下面的逻辑自行控制信号发射（避免双重 emit）
        self._model.set_regions_silent(regions)

        # 如果 center 改变了,需要触发完全更新,重新创建 item
        # 否则只触发单个 item 更新
        if center_changed:
            # 保存当前选择状态
            old_selection = self._model.get_selection()
            # 触发完全更新
            self._model.regions_changed.emit(self._model.get_regions())
            # 恢复选择状态(只有当选择的region还存在时)
            if old_selection:
                # 检查选择的region是否还在有效范围内
                current_regions = self._model.get_regions()
                valid_selection = [idx for idx in old_selection if 0 <= idx < len(current_regions)]
                if valid_selection:
                    self._model.set_selection(valid_selection)
        else:
            # 发出目标性强的信号，让UI只刷新这一个区域
            # region_style_updated 是一个理想的通用信号，因为它只传递索引
            self._model.region_style_updated.emit(self._index)

    def redo(self):
        """执行操作：应用新数据。"""
        self._apply_data(copy.deepcopy(self._new_data))

    def undo(self):
        """撤销操作：应用旧数据。"""
        self._apply_data(copy.deepcopy(self._old_data))

class AddRegionCommand(QUndoCommand):
    """用于添加新区域的命令。"""
    def __init__(self, model: "EditorModel", region_data: Dict[str, Any], description: str = "Add Region"):
        super().__init__(description)
        self._model = model
        # 存储新区域的数据
        self._region_data = copy.deepcopy(region_data)
        # 记录添加的位置(索引)
        self._index = None

    def redo(self):
        """执行添加操作"""
        regions = self._model.get_regions()
        regions.append(copy.deepcopy(self._region_data))
        self._index = len(regions) - 1
        # set_regions 会自动同步到 resource_manager，不需要手动调用
        self._model.set_regions(regions)

    def undo(self):
        """撤销添加操作:删除最后添加的区域"""
        regions = self._model.get_regions()
        if self._index is not None and 0 <= self._index < len(regions):
            regions.pop(self._index)
            # set_regions 会自动同步到 resource_manager
            self._model.set_regions(regions)
            # 清除选择
            self._model.set_selection([])

class DeleteRegionCommand(QUndoCommand):
    """用于删除区域的命令。"""
    def __init__(self, model: "EditorModel", region_index: int, region_data: Dict[str, Any], description: str = "Delete Region"):
        super().__init__(description)
        self._model = model
        self._index = region_index
        # 存储被删除区域的数据,用于撤销
        self._deleted_data = copy.deepcopy(region_data)

    def redo(self):
        """执行删除操作"""
        regions = self._model.get_regions()
        if 0 <= self._index < len(regions):
            regions.pop(self._index)
            # set_regions 会自动同步到 resource_manager
            self._model.set_regions(regions)
            # 清除选择,因为被删除的区域可能被选中
            self._model.set_selection([])

    def undo(self):
        """撤销删除操作:在原位置插入回区域"""
        regions = self._model.get_regions()
        if 0 <= self._index <= len(regions):
            regions.insert(self._index, copy.deepcopy(self._deleted_data))
            # set_regions 会自动同步到 resource_manager
            self._model.set_regions(regions)
            # 恢复选择到被恢复的区域
            self._model.set_selection([self._index])

class MaskEditCommand(QUndoCommand):
    """用于处理蒙版编辑的命令。"""
    def __init__(self, model: "EditorModel", old_mask: np.ndarray, new_mask: np.ndarray):
        super().__init__("Edit Mask")
        self._model = model
        self._old_mask = old_mask
        self._new_mask = new_mask

    def redo(self):
        self._model.set_refined_mask(self._new_mask)

    def undo(self):
        self._model.set_refined_mask(self._old_mask)
