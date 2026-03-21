"""资源数据结构

定义编辑器中使用的所有资源类。
"""

import time
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from PIL import Image

from .types import MaskType


@dataclass
class ImageResource:
    """图片资源"""
    path: str
    image: Image.Image  # PIL Image
    width: int
    height: int
    load_time: float = field(default_factory=time.time)
    
    def release(self) -> None:
        """释放资源"""
        if self.image:
            try:
                self.image.close()
            except Exception:
                pass
            self.image = None
    
    def __del__(self):
        """析构函数，确保资源释放"""
        self.release()


@dataclass
class MaskResource:
    """蒙版资源"""
    mask_type: MaskType
    data: np.ndarray
    width: int
    height: int
    create_time: float = field(default_factory=time.time)
    
    def release(self) -> None:
        """释放资源"""
        if self.data is not None:
            self.data = None
    
    def __del__(self):
        """析构函数，确保资源释放"""
        self.release()


@dataclass
class RegionResource:
    """文本区域资源"""
    region_id: int
    data: Dict  # 区域数据（包含坐标、文本、样式等）
    create_time: float = field(default_factory=time.time)
    update_time: float = field(default_factory=time.time)

