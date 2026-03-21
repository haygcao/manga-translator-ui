import copy
import hashlib
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np
from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from desktop_qt_ui.editor.editor_model import EditorModel


def _stable_command_id(key: str) -> int:
    """将 merge_key 稳定映射为 QUndoCommand.id 所需的整数。"""
    digest = hashlib.sha1(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="little", signed=False) & 0x7FFFFFFF


class UpdateRegionCommand(QUndoCommand):
    """用于更新单个区域数据的通用命令。"""

    def __init__(
        self,
        model: "EditorModel",
        region_index: int,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        description: str = "Update Region",
        merge_key: Optional[str] = None,
    ):
        super().__init__(description)
        self._model = model
        self._index = region_index
        self._merge_key = merge_key
        # 存储深拷贝以防止后续修改影响历史状态
        self._old_data = copy.deepcopy(old_data)
        self._new_data = copy.deepcopy(new_data)

    def id(self) -> int:
        if not self._merge_key:
            return -1
        return _stable_command_id(self._merge_key)

    def mergeWith(self, other) -> bool:  # noqa: N802 - Qt API naming
        if not isinstance(other, UpdateRegionCommand):
            return False
        if self.id() == -1 or other.id() != self.id():
            return False
        if self._index != other._index or self._merge_key != other._merge_key:
            return False
        # 保留第一条命令的 old_data，更新成最新 new_data。
        self._new_data = copy.deepcopy(other._new_data)
        self.setText(other.text())
        return True

    def _apply_data(self, data_to_apply: Dict[str, Any]):
        """将给定的数据字典应用到模型中的区域。"""
        regions = self._model.get_regions()
        if not (0 <= self._index < len(regions)):
            return

        # 检查 center 是否改变
        old_center = regions[self._index].get("center")
        new_center = data_to_apply.get("center")
        center_changed = old_center != new_center

        # 更新区域数据
        regions[self._index] = copy.deepcopy(data_to_apply)
        # set_regions_silent 只同步到 resource_manager，不 emit 信号
        # 由下面的逻辑自行控制信号发射（避免双重 emit）
        self._model.set_regions_silent(regions)

        # 如果 center 改变了,需要触发完全更新,重新创建 item
        # 否则只触发单个 item 更新
        if center_changed:
            old_selection = self._model.get_selection()
            self._model.regions_changed.emit(self._model.get_regions())
            if old_selection:
                current_regions = self._model.get_regions()
                valid_selection = [idx for idx in old_selection if 0 <= idx < len(current_regions)]
                if valid_selection:
                    self._model.set_selection(valid_selection)
        else:
            self._model.region_style_updated.emit(self._index)

    def redo(self):
        """执行操作：应用新数据。"""
        self._apply_data(self._new_data)

    def undo(self):
        """撤销操作：应用旧数据。"""
        self._apply_data(self._old_data)


class AddRegionCommand(QUndoCommand):
    """用于添加新区域的命令。"""

    def __init__(self, model: "EditorModel", region_data: Dict[str, Any], description: str = "Add Region"):
        super().__init__(description)
        self._model = model
        self._region_data = copy.deepcopy(region_data)
        self._index: Optional[int] = None

    def redo(self):
        """执行添加操作。"""
        regions = self._model.get_regions()
        if self._index is None or self._index > len(regions):
            self._index = len(regions)
        regions.insert(self._index, copy.deepcopy(self._region_data))
        self._model.set_regions(regions)

    def undo(self):
        """撤销添加操作。"""
        regions = self._model.get_regions()
        if self._index is not None and 0 <= self._index < len(regions):
            regions.pop(self._index)
            self._model.set_regions(regions)
            self._model.set_selection([])


class DeleteRegionCommand(QUndoCommand):
    """用于删除区域的命令。"""

    def __init__(
        self,
        model: "EditorModel",
        region_index: int,
        region_data: Dict[str, Any],
        description: str = "Delete Region",
    ):
        super().__init__(description)
        self._model = model
        self._index = region_index
        self._deleted_data = copy.deepcopy(region_data)

    def redo(self):
        """执行删除操作。"""
        regions = self._model.get_regions()
        if 0 <= self._index < len(regions):
            regions.pop(self._index)
            self._model.set_regions(regions)
            self._model.set_selection([])

    def undo(self):
        """撤销删除操作。"""
        regions = self._model.get_regions()
        if 0 <= self._index <= len(regions):
            regions.insert(self._index, copy.deepcopy(self._deleted_data))
            self._model.set_regions(regions)
            self._model.set_selection([self._index])


class MaskEditCommand(QUndoCommand):
    """用于处理蒙版编辑的命令。"""

    def __init__(self, model: "EditorModel", old_mask: np.ndarray, new_mask: np.ndarray):
        super().__init__("Edit Mask")
        self._model = model
        self._old_mask = None if old_mask is None else old_mask.copy()
        self._new_mask = None if new_mask is None else new_mask.copy()

    def redo(self):
        self._model.set_refined_mask(None if self._new_mask is None else self._new_mask.copy())

    def undo(self):
        self._model.set_refined_mask(None if self._old_mask is None else self._old_mask.copy())
