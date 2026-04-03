import copy
import hashlib
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np
from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from desktop_qt_ui.editor.editor_model import EditorModel


class _PatchDeleteMarker:
    def __deepcopy__(self, memo):
        return self


_PATCH_DELETE = _PatchDeleteMarker()
_GEOMETRY_KEYS = {
    "center",
    "lines",
    "angle",
    "white_frame_rect_local",
    "has_custom_white_frame",
    "render_box_rect_local",
}


def _values_equal(left: Any, right: Any) -> bool:
    try:
        if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
            return np.array_equal(np.asarray(left), np.asarray(right))
        return left == right
    except Exception:
        return False


def _build_region_patch(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    all_keys = set(old_data.keys()) | set(new_data.keys())
    for key in all_keys:
        old_value = old_data.get(key, _PATCH_DELETE)
        new_value = new_data.get(key, _PATCH_DELETE)
        if _values_equal(old_value, new_value):
            continue
        patch[key] = _PATCH_DELETE if new_value is _PATCH_DELETE else copy.deepcopy(new_value)
    return patch


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
        self._old_patch = _build_region_patch(new_data, old_data)
        self._new_patch = _build_region_patch(old_data, new_data)
        self._changed_keys = set(self._old_patch.keys()) | set(self._new_patch.keys())
        self._requires_full_update = bool(self._changed_keys & _GEOMETRY_KEYS)
        self._old_data = copy.deepcopy(old_data) if self._requires_full_update else None
        self._new_data = copy.deepcopy(new_data) if self._requires_full_update else None

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
        self._new_patch = copy.deepcopy(other._new_patch)
        self._changed_keys |= other._changed_keys
        self._requires_full_update = bool(self._changed_keys & _GEOMETRY_KEYS)
        self.setText(other.text())
        return True

    @staticmethod
    def _apply_patch_to_region(region_data: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        updated = copy.deepcopy(region_data)
        for key, value in patch.items():
            if value is _PATCH_DELETE:
                updated.pop(key, None)
            else:
                updated[key] = copy.deepcopy(value)
        return updated

    def _apply_patch(self, patch: Dict[str, Any]):
        """将给定 patch 应用到模型中的区域。"""
        regions = self._model.get_regions()
        if not (0 <= self._index < len(regions)):
            return

        regions[self._index] = self._apply_patch_to_region(regions[self._index], patch)
        self._model.set_regions_silent(regions)

        if self._requires_full_update:
            old_selection = self._model.get_selection()
            self._model.regions_changed.emit(self._model.get_regions())
            if old_selection:
                current_regions = self._model.get_regions()
                valid_selection = [idx for idx in old_selection if 0 <= idx < len(current_regions)]
                if valid_selection:
                    self._model.set_selection(valid_selection)
        else:
            self._model.region_style_updated.emit(self._index)

    def _apply_full_data(self, data: Dict[str, Any]) -> None:
        regions = self._model.get_regions()
        if not (0 <= self._index < len(regions)):
            return

        regions[self._index] = copy.deepcopy(data)
        self._model.set_regions_silent(regions)

        old_selection = self._model.get_selection()
        self._model.regions_changed.emit(self._model.get_regions())
        if old_selection:
            current_regions = self._model.get_regions()
            valid_selection = [idx for idx in old_selection if 0 <= idx < len(current_regions)]
            if valid_selection:
                self._model.set_selection(valid_selection)

    def redo(self):
        """执行操作：应用新 patch。"""
        if self._requires_full_update and self._new_data is not None:
            self._apply_full_data(self._new_data)
            return
        self._apply_patch(self._new_patch)

    def undo(self):
        """撤销操作：应用旧 patch。"""
        if self._requires_full_update and self._old_data is not None:
            self._apply_full_data(self._old_data)
            return
        self._apply_patch(self._old_patch)


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
        self._mask_shape: Optional[tuple[int, int]] = None
        self._bounds: Optional[tuple[int, int, int, int]] = None
        self._old_patch: Optional[np.ndarray] = None
        self._new_patch: Optional[np.ndarray] = None
        self._full_old_mask: Optional[np.ndarray] = None
        self._full_new_mask: Optional[np.ndarray] = None

        old_mask_np = self._normalize_mask(old_mask)
        new_mask_np = self._normalize_mask(new_mask)

        reference_shape = None
        if old_mask_np is not None:
            reference_shape = old_mask_np.shape
        elif new_mask_np is not None:
            reference_shape = new_mask_np.shape

        if reference_shape is None:
            return

        if old_mask_np is None:
            old_mask_np = np.zeros(reference_shape, dtype=np.uint8)
        if new_mask_np is None:
            new_mask_np = np.zeros(reference_shape, dtype=np.uint8)

        if old_mask_np.shape != new_mask_np.shape:
            self._full_old_mask = old_mask_np.copy()
            self._full_new_mask = new_mask_np.copy()
            return

        self._mask_shape = old_mask_np.shape
        diff = old_mask_np != new_mask_np
        if not np.any(diff):
            self._full_old_mask = old_mask_np.copy()
            self._full_new_mask = new_mask_np.copy()
            return

        coords = np.where(diff)
        y_min = int(np.min(coords[0]))
        y_max = int(np.max(coords[0])) + 1
        x_min = int(np.min(coords[1]))
        x_max = int(np.max(coords[1])) + 1
        self._bounds = (y_min, y_max, x_min, x_max)
        self._old_patch = old_mask_np[y_min:y_max, x_min:x_max].copy()
        self._new_patch = new_mask_np[y_min:y_max, x_min:x_max].copy()

    @staticmethod
    def _normalize_mask(mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if mask is None:
            return None
        mask_np = np.array(mask, copy=False)
        if mask_np.ndim == 3:
            mask_np = mask_np[:, :, 0]
        return np.where(mask_np > 0, 255, 0).astype(np.uint8, copy=False)

    def _apply_mask(self, full_mask: Optional[np.ndarray], patch: Optional[np.ndarray]) -> None:
        if full_mask is not None:
            self._model.set_refined_mask(full_mask.copy())
            return

        if self._mask_shape is None:
            self._model.set_refined_mask(None)
            return

        current_mask = self._normalize_mask(self._model.get_refined_mask())
        if current_mask is None or current_mask.shape != self._mask_shape:
            current_mask = np.zeros(self._mask_shape, dtype=np.uint8)
        else:
            current_mask = current_mask.copy()

        if self._bounds is not None and patch is not None:
            y_min, y_max, x_min, x_max = self._bounds
            current_mask[y_min:y_max, x_min:x_max] = patch

        self._model.set_refined_mask(current_mask)

    def redo(self):
        self._apply_mask(self._full_new_mask, self._new_patch)

    def undo(self):
        self._apply_mask(self._full_old_mask, self._old_patch)
