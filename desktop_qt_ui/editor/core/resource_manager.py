"""资源管理器

统一管理编辑器的所有资源，包括图片、蒙版、区域等。
"""

import logging
import os
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from manga_translator.utils import open_pil_image

from .resources import ImageResource, MaskResource, RegionResource
from .types import MaskType


def _release_gpu_memory():
    """释放GPU显存"""
    try:
        import torch
        if torch.cuda.is_available():
            pass
            pass
    except ImportError:
        pass
    except Exception:
        pass


class ResourceManager:
    """资源管理器
    
    统一管理所有编辑器资源的生命周期。
    """
    
    def __init__(self):
        """初始化资源管理器"""
        self.logger = logging.getLogger(__name__)
        
        # 当前加载的资源
        self._current_image: Optional[ImageResource] = None
        self._masks: Dict[MaskType, MaskResource] = {}
        self._regions: Dict[int, RegionResource] = {}
        self._next_region_id = 0
        
        # 资源缓存（用于快速切换）
        self._image_cache: Dict[str, ImageResource] = {}
        self._cache_limit = 5  # 最多缓存5张图片
        
        # 通用缓存（用于存储临时数据）
        self._temp_cache: Dict[str, any] = {}
    
    # ==================== 图片管理 ====================

    @staticmethod
    def _resolve_image_path(image_path: str) -> str:
        """规范化图片路径并校验存在性。"""
        from pathlib import Path

        path_obj = Path(image_path)
        if not path_obj.exists():
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")

        return str(path_obj.resolve())

    def load_image(self, image_path: str) -> ImageResource:
        """加载当前编辑底图资源，并更新 current_image。"""
        image_path = self._resolve_image_path(image_path)

        if image_path in self._image_cache:
            self.logger.debug(f"Image loaded from cache: {image_path}")
            resource = self._image_cache[image_path]
            self._current_image = resource
            return resource

        try:
            self.logger.debug(f"Loading image: {image_path}")
            image = open_pil_image(image_path, eager=False)
            resource = ImageResource(
                path=image_path,
                image=image,
                width=image.width,
                height=image.height,
            )
            self._add_to_cache(image_path, resource)
            self._current_image = resource
            self.logger.debug(f"Image loaded successfully: {image_path} ({image.width}x{image.height})")
            return resource
        except Exception as e:
            self.logger.error(f"Failed to load image {image_path}: {e}")
            raise

    def load_detached_image(self, image_path: str) -> Image.Image:
        """加载辅助图片，不写入 current_image，也不污染缓存。"""
        image_path = self._resolve_image_path(image_path)
        self.logger.debug(f"Loading detached image: {image_path}")
        return open_pil_image(image_path, eager=False)
    
    def _add_to_cache(self, path: str, resource: ImageResource) -> None:
        """添加图片到缓存
        
        Args:
            path: 图片路径
            resource: 图片资源
        """
        # 如果缓存已满，删除最旧的
        if len(self._image_cache) >= self._cache_limit:
            # 按加载时间排序，删除最旧的
            oldest_path = min(self._image_cache.items(), key=lambda x: x[1].load_time)[0]
            old_resource = self._image_cache.pop(oldest_path)
            old_resource.release()
            self.logger.debug(f"Removed oldest image from cache: {oldest_path}")
            
            # 释放内存
            pass
        self._image_cache[path] = resource
    
    def release_image_from_cache(self, path: str) -> bool:
        """从缓存中释放指定图片
        
        Args:
            path: 图片路径
        
        Returns:
            bool: 是否成功释放
        """
        from pathlib import Path
        
        # 规范化路径以匹配缓存中的键
        path = str(Path(path).resolve())
        if path in self._image_cache:
            resource = self._image_cache.pop(path)
            resource.release()
            pass
            self.logger.debug(f"Released image from cache: {path}")
            return True
        return False
    
    def clear_image_cache(self) -> None:
        """清空所有图片缓存"""
        for resource in self._image_cache.values():
            resource.release()
        self._image_cache.clear()
        pass
        _release_gpu_memory()
        self.logger.info("Cleared all image cache")
    
    def unload_image(self, release_from_cache: bool = False) -> None:
        """卸载当前图片及所有关联资源
        
        Args:
            release_from_cache: 是否同时从缓存中释放该图片
        """
        if self._current_image:
            current_path = self._current_image.path
            
            # 如果需要从缓存中释放
            if release_from_cache and current_path in self._image_cache:
                resource = self._image_cache.pop(current_path)
                resource.release()
                self.logger.debug(f"Released image from cache: {current_path}")
            
            self._current_image = None
        
        # 清空所有关联资源
        self.clear_masks()
        self.clear_regions()
        self.clear_cache()
        
        # 强制垃圾回收
        pass
        _release_gpu_memory()
        
        self.logger.debug("Image unloaded and memory released")
    
    def get_current_image(self) -> Optional[ImageResource]:
        """获取当前图片资源
        
        Returns:
            Optional[ImageResource]: 当前图片资源，如果没有加载返回None
        """
        return self._current_image
    
    # ==================== 蒙版管理 ====================
    
    def set_mask(self, mask_type: MaskType, mask_data: np.ndarray) -> MaskResource:
        """设置蒙版
        
        Args:
            mask_type: 蒙版类型
            mask_data: 蒙版数据
        
        Returns:
            MaskResource: 蒙版资源
        """
        if not self._current_image:
            raise RuntimeError("No image loaded")
        
        # 创建蒙版资源
        resource = MaskResource(
            mask_type=mask_type,
            data=mask_data.copy(),
            width=mask_data.shape[1],
            height=mask_data.shape[0],
        )
        
        # 释放旧蒙版
        if mask_type in self._masks:
            self._masks[mask_type].release()
        
        self._masks[mask_type] = resource
        self.logger.debug(f"Set mask: {mask_type}")
        return resource
    
    def get_mask(self, mask_type: MaskType) -> Optional[MaskResource]:
        """获取蒙版
        
        Args:
            mask_type: 蒙版类型
        
        Returns:
            Optional[MaskResource]: 蒙版资源，如果不存在返回None
        """
        return self._masks.get(mask_type)
    
    def clear_masks(self) -> None:
        """清空所有蒙版"""
        for mask in self._masks.values():
            mask.release()
        self._masks.clear()
        self.logger.debug("Cleared all masks")
    
    # ==================== 区域管理 ====================
    
    def add_region(self, region_data: Dict) -> RegionResource:
        """添加文本区域
        
        Args:
            region_data: 区域数据
        
        Returns:
            RegionResource: 区域资源
        """
        region_id = self._next_region_id
        self._next_region_id += 1
        
        resource = RegionResource(
            region_id=region_id,
            data=region_data.copy(),
        )
        
        self._regions[region_id] = resource
        self.logger.debug(f"Added region: {region_id}")
        return resource

    def get_all_regions(self) -> List[RegionResource]:
        """获取所有区域（按region_id排序）
        
        Returns:
            List[RegionResource]: 区域列表，按region_id升序排列
        """
        # 按region_id排序，确保顺序正确
        return [self._regions[rid] for rid in sorted(self._regions.keys())]
    
    def clear_regions(self) -> None:
        """清空所有区域"""
        self._regions.clear()
        self._next_region_id = 0
        self.logger.debug("Cleared all regions")
    
    # ==================== 缓存管理 ====================
    
    def set_cache(self, key: str, value: any) -> None:
        """设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        self._temp_cache[key] = value
        self.logger.debug(f"Set cache: {key}")
    
    def get_cache(self, key: str, default=None) -> any:
        """获取缓存数据
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存值，如果不存在返回default
        """
        return self._temp_cache.get(key, default)
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """清空缓存
        
        Args:
            key: 如果指定，只清空该键；否则清空所有缓存
        """
        if key:
            if key in self._temp_cache:
                del self._temp_cache[key]
                self.logger.debug(f"Cleared cache: {key}")
        else:
            self._temp_cache.clear()
            self.logger.debug("Cleared all cache")
    
    # ==================== 资源清理 ====================
    
    def cleanup_all(self) -> None:
        """清理所有资源"""
        self.logger.info("Cleaning up all resources")
        
        # 卸载当前图片（不从缓存释放，因为下面会清空缓存）
        if self._current_image:
            self._current_image = None
        
        # 清空蒙版
        self.clear_masks()
        
        # 清空区域
        self.clear_regions()
        
        # 清空临时缓存
        self._temp_cache.clear()
        
        # 清理图片缓存
        for resource in self._image_cache.values():
            resource.release()
        self._image_cache.clear()
        
        # 强制垃圾回收和GPU显存释放
        pass
        _release_gpu_memory()
        
        self.logger.info("All resources cleaned up")
    
    def release_memory_after_export(self) -> None:
        """导出后释放内存
        
        清理临时缓存和GPU显存，但保留图片缓存以便快速切换
        """
        self.logger.info("Releasing memory after export")
        
        # 清空临时缓存（inpainted图片等）
        self._temp_cache.clear()
        
        # 强制垃圾回收
        pass
        # 释放GPU显存
        _release_gpu_memory()
        
        self.logger.info("Memory released after export")
    
    def __del__(self):
        """析构函数"""
        self.cleanup_all()



