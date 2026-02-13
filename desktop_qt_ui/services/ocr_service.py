"""
OCR识别服务
集成后端OCR模块，实现文本框内容的光学字符识别功能
"""
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

# 添加后端模块路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))

try:
    from manga_translator.config import Ocr, OcrConfig
    from manga_translator.ocr import dispatch as dispatch_ocr
    from manga_translator.ocr import prepare as prepare_ocr
    from manga_translator.utils import Quadrilateral
    OCR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"OCR后端模块导入失败: {e}")
    OCR_AVAILABLE = False

@dataclass
class OcrResult:
    """OCR识别结果"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    processing_time: float

class OcrService:
    """OCR识别服务"""
    
    def __init__(self, config_service=None):
        self.logger = logging.getLogger(__name__)
        
        # OCR配置
        self.default_config = OcrConfig(
            ocr=Ocr.ocr48px,  # 默认使用48px OCR模型
            min_text_length=0,
            ignore_bubble=0,
            prob=0.3,  # 最小置信度阈值
            use_mocr_merge=False
        )
        
        # 配置服务依赖
        self.config_service = config_service
        if not self.config_service:
            # 懒加载配置服务，避免循环依赖
            from . import get_config_service
            self.config_service = get_config_service()
        
        # 设备配置
        self.device = 'cpu'
        if self._check_gpu_available():
            self.device = 'cuda'
            
        # OCR模型缓存
        self.model_prepared = False
        
        self.logger.info(f"OCR识别服务初始化完成，使用设备: {self.device}")
    
    def _get_current_config(self) -> OcrConfig:
        """从配置服务获取当前OCR配置"""
        if not self.config_service:
            # 回退到默认配置
            return OcrConfig(
                ocr=Ocr.ocr48px,
                min_text_length=0,
                ignore_bubble=0,
                prob=0.3,
                use_mocr_merge=False
            )
        
        try:
            config = self.config_service.get_config()
            # Use attribute access for Pydantic models
            ocr_config_dict = config.ocr.model_dump() if hasattr(config, 'ocr') else {}
            cli_config_dict = config.cli.model_dump() if hasattr(config, 'cli') else {}
            
            # 从配置构建OcrConfig
            ocr_config = OcrConfig()
            
            # OCR模型设置
            if 'ocr' in ocr_config_dict:
                try:
                    # The value from the config might be the enum member name (e.g., 'ocr48px')
                    ocr_config.ocr = Ocr(ocr_config_dict['ocr'])
                except (ValueError, KeyError):
                    self.logger.warning(f"未知OCR模型: {ocr_config_dict.get('ocr')}，使用默认模型")
                    ocr_config.ocr = Ocr.ocr48px
            
            # 其他OCR参数
            ocr_config.min_text_length = ocr_config_dict.get('min_text_length', 0)
            ocr_config.ignore_bubble = ocr_config_dict.get('ignore_bubble', 0)
            ocr_config.prob = ocr_config_dict.get('prob', 0.3)
            ocr_config.use_mocr_merge = ocr_config_dict.get('use_mocr_merge', False)
            
            # GPU设置从CLI配置获取
            if cli_config_dict.get('use_gpu', False) and self._check_gpu_available():
                self.device = 'cuda'
            else:
                self.device = 'cpu'
                
            return ocr_config
            
        except Exception as e:
            self.logger.error(f"获取OCR配置失败，使用默认配置: {e}")
            return OcrConfig(
                ocr=Ocr.ocr48px,
                min_text_length=0,
                ignore_bubble=0,
                prob=0.3,
                use_mocr_merge=False
            )
        
    def _check_gpu_available(self) -> bool:
        """检查GPU是否可用"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    async def prepare_model(self, ocr_type: Optional[Ocr] = None):
        """准备OCR模型"""
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR后端模块不可用")
        if self.model_prepared:
            return
            
        ocr_to_use = ocr_type or self.default_config.ocr
        
        try:
            await prepare_ocr(ocr_to_use, self.device)
            self.model_prepared = True
            self.logger.info(f"OCR模型准备完成: {ocr_to_use.value}")
        except Exception as e:
            self.logger.error(f"OCR模型准备失败: {e}")
            raise
    
    def _region_to_quadrilateral(self, region: Dict[str, Any], image_shape: Tuple[int, int]) -> Quadrilateral:
        """将文本框区域转换为OCR所需的Quadrilateral格式"""
        try:
            # 获取文本框的四个角点
            lines = region.get('lines', [[]])
            if not lines or not lines[0]:
                return None
                
            # 获取第一个多边形的所有点
            points = lines[0]
            if len(points) < 4:
                return None
            
            # 转换为numpy数组格式
            pts = np.array(points, dtype=np.float32)
            
            # 创建Quadrilateral对象
            quadrilateral = Quadrilateral(
                pts=pts,
                text='',  # 待识别
                prob=1.0
            )
            
            return quadrilateral
            
        except Exception as e:
            self.logger.error(f"区域转换失败: {e}")
            return None
    
    def _extract_region_image(self, image: np.ndarray, region: Dict[str, Any]) -> Optional[np.ndarray]:
        """从图像中提取文本框区域"""
        try:
            lines = region.get('lines', [[]])
            if not lines or not lines[0]:
                return None
                
            points = np.array(lines[0], dtype=np.int32)
            
            # 获取边界框
            x, y, w, h = cv2.boundingRect(points)
            
            # 确保边界框在图像范围内
            x = max(0, x)
            y = max(0, y)
            w = min(w, image.shape[1] - x)
            h = min(h, image.shape[0] - y)
            
            if w <= 0 or h <= 0:
                return None
            
            # 提取区域
            region_image = image[y:y+h, x:x+w]
            
            return region_image
            
        except Exception as e:
            self.logger.error(f"区域图像提取失败: {e}")
            return None

    def _build_text_mask_canny_flood(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Build a text mask from a rectified region using a Canny+flood-fill pipeline.
        This is adapted from BallonsTranslator's canny_flood preprocessing.
        """
        try:
            if img is None or img.size == 0:
                return None
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif img.ndim == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

            kernel = np.ones((3, 3), np.uint8)
            orih, oriw = img.shape[:2]
            scale_r = 1.0
            if orih > 300 and oriw > 300:
                scale_r = 0.6
            elif orih < 120 or oriw < 120:
                scale_r = 1.4

            if scale_r != 1.0:
                orimg = np.copy(img)
                new_w = max(int(oriw * scale_r), 2)
                new_h = max(int(orih * scale_r), 2)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            h, w = img.shape[:2]
            if h < 2 or w < 2:
                return None
            img_area = h * w

            cpimg = cv2.GaussianBlur(img, (3, 3), cv2.BORDER_DEFAULT)
            detected_edges = cv2.Canny(cpimg, 70, 140, L2gradient=True, apertureSize=3)
            cv2.rectangle(detected_edges, (0, 0), (w - 1, h - 1), (255, 255, 255), 1, cv2.LINE_8)
            cons, _ = cv2.findContours(detected_edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
            cv2.rectangle(detected_edges, (0, 0), (w - 1, h - 1), (0, 0, 0), 1, cv2.LINE_8)

            ballon_mask = np.zeros((h, w), np.uint8)
            min_retval = np.inf
            contour_mask = np.zeros((h, w), np.uint8)
            difres = 10
            seedpnt = (int(w / 2), int(h / 2))
            for i in range(len(cons)):
                rect = cv2.boundingRect(cons[i])
                if rect[2] * rect[3] < img_area * 0.4:
                    continue

                contour_mask = cv2.drawContours(contour_mask, cons, i, 255, 2)
                cpmask = np.copy(contour_mask)
                cv2.rectangle(contour_mask, (0, 0), (w - 1, h - 1), 255, 1, cv2.LINE_8)
                retval, _, _, _ = cv2.floodFill(
                    cpmask,
                    mask=None,
                    seedPoint=seedpnt,
                    flags=4,
                    newVal=127,
                    loDiff=(difres, difres, difres),
                    upDiff=(difres, difres, difres),
                )
                if retval <= img_area * 0.3:
                    contour_mask = cv2.drawContours(contour_mask, cons, i, 0, 2)
                if retval < min_retval and retval > img_area * 0.3:
                    min_retval = retval
                    ballon_mask = cpmask

            if np.count_nonzero(ballon_mask) == 0:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                _, fallback_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                if scale_r != 1.0:
                    fallback_mask = cv2.resize(fallback_mask, (oriw, orih), interpolation=cv2.INTER_NEAREST)
                return fallback_mask

            ballon_mask = 127 - ballon_mask
            ballon_mask = cv2.dilate(ballon_mask, kernel, iterations=1)
            outer_area, _, _, _ = cv2.floodFill(
                ballon_mask,
                mask=None,
                seedPoint=seedpnt,
                flags=4,
                newVal=30,
                loDiff=(difres, difres, difres),
                upDiff=(difres, difres, difres),
            )
            ballon_mask = 30 - ballon_mask
            _, ballon_mask = cv2.threshold(ballon_mask, 1, 255, cv2.THRESH_BINARY)
            ballon_mask = cv2.bitwise_not(ballon_mask, ballon_mask)

            detected_edges = cv2.dilate(detected_edges, kernel, iterations=1)
            work_mask = np.copy(detected_edges)
            outer_area = max(int(outer_area), 1)
            for _ in range(2):
                work_mask = cv2.bitwise_and(work_mask, ballon_mask)
                flood_base = np.copy(work_mask)
                bgarea1, _, _, _ = cv2.floodFill(
                    flood_base,
                    mask=None,
                    seedPoint=(0, 0),
                    flags=4,
                    newVal=127,
                    loDiff=(difres, difres, difres),
                    upDiff=(difres, difres, difres),
                )
                bgarea2, _, _, _ = cv2.floodFill(
                    flood_base,
                    mask=None,
                    seedPoint=(w - 1, h - 1),
                    flags=4,
                    newVal=127,
                    loDiff=(difres, difres, difres),
                    upDiff=(difres, difres, difres),
                )
                txt_area = min(img_area - bgarea1, img_area - bgarea2)
                ratio_ob = txt_area / outer_area
                ballon_mask = cv2.erode(ballon_mask, kernel, iterations=1)
                if ratio_ob < 0.85:
                    work_mask = flood_base
                    break
                work_mask = flood_base

            text_mask = 127 - work_mask
            _, text_mask = cv2.threshold(text_mask, 1, 255, cv2.THRESH_BINARY)

            if scale_r != 1.0:
                ballon_mask = cv2.resize(ballon_mask, (oriw, orih), interpolation=cv2.INTER_NEAREST)
                text_mask = cv2.resize(text_mask, (oriw, orih), interpolation=cv2.INTER_NEAREST)

            text_mask = cv2.bitwise_and(text_mask, ballon_mask)
            return text_mask
        except Exception as e:
            self.logger.debug(f"canny_flood preprocessing failed, fallback to original region: {e}")
            return None

    def _split_spans_from_mask(self, mask: np.ndarray, axis: str) -> List[Tuple[int, int]]:
        """
        Split a text mask into line spans using projection on Y (horizontal text)
        or X (vertical text).
        """
        if mask is None or mask.size == 0:
            return []
        if axis == 'y':
            proj = mask.mean(axis=1)
            dim = mask.shape[0]
        else:
            proj = mask.mean(axis=0)
            dim = mask.shape[1]
        if proj.size < 2:
            return []

        base = float(np.mean(proj))
        if base <= 1e-6:
            return []
        threshold = base * 0.4
        active = np.where(proj > threshold)[0]
        if active.size == 0:
            return []

        spans: List[Tuple[int, int]] = []
        start = int(active[0])
        prev = start
        for idx in active[1:]:
            idx = int(idx)
            if idx - prev > 1:
                spans.append((start, prev))
                start = idx
            prev = idx
        spans.append((start, prev))

        if not spans:
            return []

        max_len = max(e - s + 1 for s, e in spans)
        min_len = max(3, int(round(max_len * 0.3)))
        filtered = [(s, e) for s, e in spans if (e - s + 1) >= min_len]
        if not filtered:
            filtered = spans

        expanded: List[Tuple[int, int]] = []
        for i, (s, e) in enumerate(filtered):
            if i == 0:
                start_pad = max(0, s - 2)
            else:
                gap = max(1, s - filtered[i - 1][1] - 1)
                start_pad = max(0, s - gap // 2)

            if i == len(filtered) - 1:
                end_pad = min(dim - 1, e + 2)
            else:
                gap = max(1, filtered[i + 1][0] - e - 1)
                end_pad = min(dim - 1, e + gap // 2)

            if end_pad - start_pad >= 1:
                expanded.append((start_pad, end_pad))

        return expanded

    def _split_single_polygon(self, image: np.ndarray, pts: np.ndarray) -> List[np.ndarray]:
        """
        Split a single large polygon into multiple sub-polygons using:
        rectify -> canny_flood mask -> projection spans -> inverse projection.
        """
        if pts is None or len(pts) < 4:
            return []

        quad = Quadrilateral(pts=pts.astype(np.int32), text='', prob=1.0)
        [l1a, l1b, l2a, l2b] = [a.astype(np.float32) for a in quad.structure]
        norm_v = np.linalg.norm(l1b - l1a)
        norm_h = np.linalg.norm(l2b - l2a)
        if norm_v <= 1 or norm_h <= 1:
            return []

        h = max(int(round(norm_v)), 2)
        w = max(int(round(norm_h)), 2)

        dst_pts = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
        M, _ = cv2.findHomography(quad.pts.astype(np.float32), dst_pts, cv2.RANSAC, 5.0)
        if M is None:
            return []

        rectified = cv2.warpPerspective(image, M, (w, h))
        text_mask = self._build_text_mask_canny_flood(rectified)
        if text_mask is None:
            return []

        axis = 'y' if quad.direction == 'h' else 'x'
        spans = self._split_spans_from_mask(text_mask, axis=axis)
        if len(spans) <= 1:
            return []

        try:
            inv_m = np.linalg.inv(M)
        except np.linalg.LinAlgError:
            return []

        split_polygons: List[np.ndarray] = []
        for start, end in spans:
            if axis == 'y':
                local_quad = np.array(
                    [[0, start], [w - 1, start], [w - 1, end], [0, end]],
                    dtype=np.float32
                )
            else:
                local_quad = np.array(
                    [[start, 0], [end, 0], [end, h - 1], [start, h - 1]],
                    dtype=np.float32
                )
            restored = cv2.perspectiveTransform(local_quad.reshape(1, 4, 2), inv_m)[0]
            restored[:, 0] = np.clip(restored[:, 0], 0, image.shape[1] - 1)
            restored[:, 1] = np.clip(restored[:, 1], 0, image.shape[0] - 1)
            restored_int = np.round(restored).astype(np.int32)
            if cv2.contourArea(restored_int) < 16:
                continue
            split_polygons.append(restored_int)

        return split_polygons
    
    async def recognize_region(self, image: np.ndarray, region: Dict[str, Any], 
                             config: Optional[OcrConfig] = None) -> Optional[OcrResult]:
        """识别单个文本框区域的文字（支持一个区域包含多个多边形）"""
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR后端模块不可用")

        # --- FIX: Sanitize region data by ensuring all coordinates are rounded integers ---
        import copy
        region_clean = copy.deepcopy(region)
        if 'lines' in region_clean:
            for poly in region_clean['lines']:
                for i, point in enumerate(poly):
                    poly[i] = [int(round(point[0])), int(round(point[1]))]
        # --- END FIX ---
            
        if not self.model_prepared:
            await self.prepare_model()
        
        # Convert PIL Image to numpy array if necessary
        if isinstance(image, Image.Image):
            image = np.array(image.convert('RGB'))

        config = config or self._get_current_config()
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Handle multiple polygons within one region
            quadrilaterals = []
            all_polygons = region_clean.get('lines', []) # Use the cleaned data
            if not all_polygons:
                return None

            should_try_split = len(all_polygons) == 1 and config.ocr in {
                Ocr.ocr32px, Ocr.ocr48px, Ocr.ocr48px_ctc
            }

            for poly_points in all_polygons:
                if len(poly_points) >= 4:
                    pts = np.array(poly_points, dtype=np.int32)
                    if should_try_split:
                        split_polys = self._split_single_polygon(image, pts.astype(np.float32))
                        if len(split_polys) > 1:
                            self.logger.debug(f"OCR pre-split triggered: {len(split_polys)} sub-lines")
                            for sp in split_polys:
                                quadrilaterals.append(Quadrilateral(pts=sp, text='', prob=1.0))
                            continue
                    quadrilaterals.append(Quadrilateral(pts=pts, text='', prob=1.0))

            if not quadrilaterals:
                return None

            # Call backend OCR with all polygons from the region
            results = await dispatch_ocr(
                config.ocr, 
                image, 
                quadrilaterals, 
                config, 
                self.device,
                verbose=False
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            if results:
                # Combine text from all recognized polygons
                combined_text = ''.join([res.text for res in results if res.text])
                # Average the confidence
                avg_confidence = sum(res.prob for res in results) / len(results) if results else 0
                
                # The bbox for a multi-polygon region is the bounding box of all polygons
                all_points = [p for poly in all_polygons for p in poly]
                min_x = int(min(p[0] for p in all_points))
                max_x = int(max(p[0] for p in all_points))
                min_y = int(min(p[1] for p in all_points))
                max_y = int(max(p[1] for p in all_points))
                bbox_tuple = (min_x, min_y, max_x - min_x, max_y - min_y)

                return OcrResult(
                    text=combined_text,
                    confidence=avg_confidence,
                    bbox=bbox_tuple,
                    processing_time=processing_time
                )
            else:
                self.logger.warning("OCR识别无结果")
                return None
                
        except Exception as e:
            self.logger.error(f"OCR识别失败: {e}")
            return None
    
    async def recognize_multiple_regions(self, image: np.ndarray, regions: List[Dict[str, Any]], 
                                       config: Optional[OcrConfig] = None) -> List[Optional[OcrResult]]:
        """批量识别多个文本框区域"""
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR后端模块不可用")
            
        if not self.model_prepared:
            await self.prepare_model()
        
        config = config or self.default_config
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 转换所有区域格式
            quadrilaterals = []
            valid_indices = []
            
            for i, region in enumerate(regions):
                quad = self._region_to_quadrilateral(region, image.shape[:2])
                if quad is not None:
                    quadrilaterals.append(quad)
                    valid_indices.append(i)
            
            if not quadrilaterals:
                return [None] * len(regions)
            
            # 批量调用OCR
            results = await dispatch_ocr(
                config.ocr,
                image,
                quadrilaterals,
                config,
                self.device,
                verbose=False
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # 构建结果列表
            ocr_results = [None] * len(regions)
            
            for i, result in enumerate(results):
                if i < len(valid_indices):
                    original_index = valid_indices[i]
                    bbox = result.aabb
                    bbox_tuple = (bbox.x, bbox.y, bbox.w, bbox.h)
                    
                    ocr_results[original_index] = OcrResult(
                        text=result.text,
                        confidence=result.prob,
                        bbox=bbox_tuple,
                        processing_time=processing_time / len(results)
                    )
            
            return ocr_results
            
        except Exception as e:
            self.logger.error(f"批量OCR识别失败: {e}")
            return [None] * len(regions)
    
    def get_available_models(self) -> List[str]:
        """获取可用的OCR模型列表"""
        if not OCR_AVAILABLE:
            return []
            
        return [ocr.value for ocr in Ocr]
    
    def set_model(self, model_name: str):
        """设置OCR模型，支持通过value或name设置"""
        if not OCR_AVAILABLE:
            return
        
        try:
            # 先尝试通过name查找（最常见的情况）
            if hasattr(Ocr, model_name):
                self.default_config.ocr = Ocr[model_name]
                self.model_prepared = False  # 重置模型准备状态
                self.logger.info(f"通过name设置OCR模型: {model_name}")
                return
            
            # 如果name查找失败，尝试通过value查找
            for ocr_model in Ocr:
                if ocr_model.value == model_name:
                    self.default_config.ocr = ocr_model
                    self.model_prepared = False  # 重置模型准备状态
                    self.logger.info(f"通过value设置OCR模型: {model_name} -> {ocr_model.name}")
                    return
                    
            # 如果都没找到，记录警告
            self.logger.warning(f"未找到OCR模型: {model_name}，保持当前设置")
        except Exception as e:
            self.logger.error(f"设置OCR模型时发生错误: {e}")
    
    def get_current_model(self) -> str:
        """获取当前OCR模型名称"""
        return self.default_config.ocr.value
    
    
    def set_config(self, **kwargs):
        """设置OCR配置"""
        for key, value in kwargs.items():
            if hasattr(self.default_config, key):
                setattr(self.default_config, key, value)
                self.logger.info(f"OCR配置更新: {key} = {value}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前OCR配置"""
        return {
            'ocr': self.default_config.ocr.value,
            'min_text_length': self.default_config.min_text_length,
            'ignore_bubble': self.default_config.ignore_bubble,
            'prob': self.default_config.prob,
            'use_mocr_merge': self.default_config.use_mocr_merge,
            'device': self.device
        }
    
    def is_available(self) -> bool:
        """检查OCR服务是否可用"""
        return OCR_AVAILABLE
    
    def _is_valid_quadrilateral(self, pts: np.ndarray) -> bool:
        """检查四边形是否适合OCR识别"""
        if len(pts) < 4:
            return False
        
        # 计算面积
        area = cv2.contourArea(pts)
        if area < 100:  # 面积太小
            return False
        
        # 检查是否过于扭曲（长宽比过大）
        rect = cv2.boundingRect(pts)
        if rect[2] <= 0 or rect[3] <= 0:
            return False
        
        aspect_ratio = max(rect[2], rect[3]) / min(rect[2], rect[3])
        if aspect_ratio > 20:  # 长宽比超过20:1，可能过于扭曲
            return False
        
        return True

# The ServiceContainer in services/__init__.py is responsible for instantiation.
