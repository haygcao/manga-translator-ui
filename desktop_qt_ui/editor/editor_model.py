from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal


class EditorModel(QObject):
    """
    编辑器数据模型 (Model)。
    负责封装和管理所有核心数据，如图像、区域、蒙版等。
    当数据变化时，通过信号通知视图更新。
    """
    # --- 定义信号 ---
    image_changed = pyqtSignal(object)
    regions_changed = pyqtSignal(list)
    raw_mask_changed = pyqtSignal(object)
    refined_mask_changed = pyqtSignal(object)
    display_mask_type_changed = pyqtSignal(str)
    selection_changed = pyqtSignal(list)
    inpainted_image_changed = pyqtSignal(object)
    compare_image_changed = pyqtSignal(object)
    region_display_mode_changed = pyqtSignal(str) # New signal
    original_image_alpha_changed = pyqtSignal(float)
    region_style_updated = pyqtSignal(int) # NEW SIGNAL for targeted style updates
    active_tool_changed = pyqtSignal(str)
    brush_size_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        from services import get_resource_manager
        self.resource_manager = get_resource_manager()
        
        self._source_image_path: Optional[str] = None
        # self._image, self._regions, etc. removed in favor of ResourceManager
        
        self._inpainted_image_path: Optional[str] = None  # Store inpainted path
        self._display_mask_type: str = 'none'
        self._selected_indices: List[int] = []
        self._region_display_mode: str = 'full'
        self._original_image_alpha: float = 0.0
        self._compare_image = None
        self._active_tool: str = 'select'
        self._brush_size: int = 30
    # --- Getter / Setter 方法 ---

    def set_source_image_path(self, path: str):
        self._source_image_path = path

    def get_source_image_path(self) -> Optional[str]:
        return self._source_image_path

    def set_image(self, image: Any):
        # Assume ResourceManager has been updated by the caller (Controller) if loaded from file.
        # Or if passed directly, we can't easily update RM without path. 
        # For now, we rely on Controller's workflow where RM is the source of truth for loading.
        # This setter is mainly for triggering the signal.
        self.image_changed.emit(image)

    def get_image(self) -> Optional[Any]:
        resource = self.resource_manager.get_current_image()
        return resource.image if resource else None

    def set_regions(self, regions: List[Dict[str, Any]]):
        # Clear and update ResourceManager
        self.resource_manager.clear_regions()
        for region_data in regions:
            self.resource_manager.add_region(region_data)
        self.regions_changed.emit(regions)

    def set_regions_silent(self, regions: List[Dict[str, Any]]):
        """更新 regions 数据但不 emit 信号。由 command 自行控制信号发射。"""
        self.resource_manager.clear_regions()
        for region_data in regions:
            self.resource_manager.add_region(region_data)

    def get_regions(self) -> List[Dict[str, Any]]:
        resources = self.resource_manager.get_all_regions()
        return [r.data for r in resources]

    @staticmethod
    def _normalize_binary_mask(mask: Any):
        import numpy as np

        if mask is None:
            return None
        if not isinstance(mask, np.ndarray):
            mask = np.array(mask)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        return np.where(mask > 0, 255, 0).astype(np.uint8)

    def set_raw_mask(self, mask: Any):
        from desktop_qt_ui.editor.core.types import MaskType
        if mask is not None:
            mask = self._normalize_binary_mask(mask)
            self.resource_manager.set_mask(MaskType.RAW, mask)
        else:
            # How to unset? ResourceManager doesn't have unset_mask specific, 
            # but we can assume setting None isn't supported by set_mask directly likely.
            # But ResourceManager.clear_masks clears ALL.
            # Ideally we only clear RAW.
            pass
            
        self.raw_mask_changed.emit(mask)

    def get_raw_mask(self) -> Optional[Any]:
        from desktop_qt_ui.editor.core.types import MaskType
        resource = self.resource_manager.get_mask(MaskType.RAW)
        return resource.data if resource else None

    def set_refined_mask(self, mask: Any):
        from desktop_qt_ui.editor.core.types import MaskType
        if mask is not None:
            mask = self._normalize_binary_mask(mask)
            self.resource_manager.set_mask(MaskType.REFINED, mask)
        
        self.refined_mask_changed.emit(mask)
        # Force immediate display update if this is the current display type
        if self._display_mask_type == 'refined':
            self.display_mask_type_changed.emit('refined')

    def get_refined_mask(self) -> Optional[Any]:
        from desktop_qt_ui.editor.core.types import MaskType
        resource = self.resource_manager.get_mask(MaskType.REFINED)
        return resource.data if resource else None

    def set_display_mask_type(self, mask_type: str):
        """Sets which mask ('raw', 'refined', or 'none') should be displayed."""
        if mask_type not in ['raw', 'refined', 'none']:
            return
        
        if self._display_mask_type != mask_type:
            self._display_mask_type = mask_type
            self.display_mask_type_changed.emit(mask_type)

    def get_display_mask_type(self) -> str:
        return self._display_mask_type

    def set_inpainted_image_path(self, path: Optional[str]):
        """设置inpainted图片路径"""
        self._inpainted_image_path = path

    def get_inpainted_image_path(self) -> Optional[str]:
        """获取inpainted图片路径"""
        return self._inpainted_image_path


    def set_selection(self, indices: List[int]):
        if self._selected_indices != indices:
            self._selected_indices = sorted(indices)
            self.selection_changed.emit(self._selected_indices)

    def get_selection(self) -> List[int]:
        return self._selected_indices

    def get_region_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """通过索引安全地获取区域数据"""
        regions = self.get_regions()
        if 0 <= index < len(regions):
            return regions[index]
        return None

    def set_inpainted_image(self, image: Any):
        # Store in temp cache of ResourceManager or keep local?
        # Let's use ResourceManager's temp cache to be consistent with "Unification"
        self.resource_manager.set_cache("inpainted_image", image)
        self.inpainted_image_changed.emit(image)

    def get_inpainted_image(self) -> Optional[Any]:
        return self.resource_manager.get_cache("inpainted_image")

    def set_compare_image(self, image: Any):
        self._compare_image = image
        self.compare_image_changed.emit(image)

    def set_region_display_mode(self, mode: str):
        """设置区域显示模式 ('full', 'text_only', 'box_only', 'none')"""
        if self._region_display_mode != mode:
            self._region_display_mode = mode
            self.region_display_mode_changed.emit(mode)

    def get_region_display_mode(self) -> str:
        return self._region_display_mode

    def set_original_image_alpha(self, alpha: float):
        if self._original_image_alpha != alpha:
            self._original_image_alpha = alpha
            self.original_image_alpha_changed.emit(alpha)

    def get_original_image_alpha(self) -> float:
        return self._original_image_alpha

    def set_active_tool(self, tool: str):
        if self._active_tool != tool:
            self._active_tool = tool
            self.active_tool_changed.emit(tool)

    def set_brush_size(self, size: int):
        if self._brush_size != size:
            self._brush_size = size
            self.brush_size_changed.emit(size)

    def get_brush_size(self) -> int:
        return self._brush_size
