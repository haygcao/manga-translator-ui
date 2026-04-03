from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage


@dataclass(slots=True)
class DisplayImageFrame:
    qimage: QImage
    source_width: int
    source_height: int
    preview_width: int
    preview_height: int

    @property
    def scale_x(self) -> float:
        return float(self.source_width) / float(max(1, self.preview_width))

    @property
    def scale_y(self) -> float:
        return float(self.source_height) / float(max(1, self.preview_height))

    @property
    def is_downsampled(self) -> bool:
        return self.source_width != self.preview_width or self.source_height != self.preview_height


def _ensure_uint8(array: np.ndarray, *, copy: bool) -> np.ndarray:
    if array.dtype != np.uint8:
        array = array.astype(np.uint8, copy=False)
    if copy:
        return np.array(array, copy=True)
    if not array.flags.c_contiguous:
        return np.ascontiguousarray(array)
    return array


def _resolve_preview_size(width: int, height: int, max_pixels: Optional[int]) -> tuple[int, int]:
    if not max_pixels or width <= 0 or height <= 0:
        return width, height
    source_pixels = int(width) * int(height)
    if source_pixels <= max_pixels:
        return width, height
    scale = math.sqrt(float(max_pixels) / float(source_pixels))
    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))
    return target_width, target_height


def _qimage_from_array(array: np.ndarray) -> QImage:
    array = _ensure_uint8(array, copy=False)
    if array.ndim == 2:
        height, width = array.shape
        return QImage(
            array.data,
            width,
            height,
            int(array.strides[0]),
            QImage.Format.Format_Grayscale8,
        ).copy()

    height, width, channels = array.shape
    if channels == 4:
        image_format = QImage.Format.Format_RGBA8888
    elif channels == 3:
        image_format = QImage.Format.Format_RGB888
    else:
        raise ValueError(f"Unsupported image channel count: {channels}")

    return QImage(
        array.data,
        width,
        height,
        int(array.strides[0]),
        image_format,
    ).copy()


def image_like_to_display_array(image: Any, *, copy: bool = False) -> Optional[np.ndarray]:
    if image is None:
        return None

    if isinstance(image, Image.Image):
        converted = image
        try:
            if image.mode == "LA" or "A" in image.mode:
                converted = image.convert("RGBA")
            elif image.mode in ("1", "L"):
                converted = image.convert("L")
            elif image.mode in ("RGB", "RGBA"):
                converted = image
            else:
                converted = image.convert("RGB")
            return _ensure_uint8(np.asarray(converted), copy=True)
        finally:
            if converted is not image:
                try:
                    converted.close()
                except Exception:
                    pass

    array = np.asarray(image)
    if array.ndim == 2:
        return _ensure_uint8(array, copy=copy)
    if array.ndim != 3:
        raise ValueError(f"Unsupported image array shape: {array.shape}")

    channels = array.shape[2]
    if channels == 1:
        return _ensure_uint8(array[:, :, 0], copy=copy)
    if channels == 2:
        rgb = np.repeat(array[:, :, :1], 3, axis=2)
        return _ensure_uint8(rgb, copy=True)
    if channels >= 4:
        return _ensure_uint8(array[:, :, :4], copy=copy)
    return _ensure_uint8(array[:, :, :3], copy=copy)


def build_display_image_frame(image: Any, *, max_pixels: Optional[int] = None) -> Optional[DisplayImageFrame]:
    if image is None:
        return None

    if isinstance(image, Image.Image):
        source_width, source_height = image.size
        preview_width, preview_height = _resolve_preview_size(source_width, source_height, max_pixels)
        resized_image = image
        normalized_image = None
        try:
            if (preview_width, preview_height) != (source_width, source_height):
                resized_image = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)

            if resized_image.mode == "LA" or "A" in resized_image.mode:
                normalized_image = resized_image.convert("RGBA")
            elif resized_image.mode in ("1", "L"):
                normalized_image = resized_image.convert("L")
            elif resized_image.mode in ("RGB", "RGBA"):
                normalized_image = resized_image
            else:
                normalized_image = resized_image.convert("RGB")

            array = _ensure_uint8(np.asarray(normalized_image), copy=True)
            return DisplayImageFrame(
                qimage=_qimage_from_array(array),
                source_width=source_width,
                source_height=source_height,
                preview_width=preview_width,
                preview_height=preview_height,
            )
        finally:
            if normalized_image is not None and normalized_image not in (image, resized_image):
                try:
                    normalized_image.close()
                except Exception:
                    pass
            if resized_image is not image:
                try:
                    resized_image.close()
                except Exception:
                    pass

    array = image_like_to_display_array(image, copy=False)
    if array is None:
        return None

    if array.ndim == 2:
        source_height, source_width = array.shape
    else:
        source_height, source_width = array.shape[:2]
    preview_width, preview_height = _resolve_preview_size(source_width, source_height, max_pixels)
    if (preview_width, preview_height) != (source_width, source_height):
        interpolation = cv2.INTER_AREA if preview_width < source_width or preview_height < source_height else cv2.INTER_LINEAR
        array = cv2.resize(array, (preview_width, preview_height), interpolation=interpolation)

    array = _ensure_uint8(array, copy=False)
    return DisplayImageFrame(
        qimage=_qimage_from_array(array),
        source_width=source_width,
        source_height=source_height,
        preview_width=preview_width,
        preview_height=preview_height,
    )


def image_like_to_rgb_array(image: Any, *, copy: bool = False) -> Optional[np.ndarray]:
    if image is None:
        return None

    if isinstance(image, Image.Image):
        converted = image if image.mode == "RGB" else image.convert("RGB")
        try:
            return _ensure_uint8(np.asarray(converted), copy=True)
        finally:
            if converted is not image:
                try:
                    converted.close()
                except Exception:
                    pass

    array = np.asarray(image)
    if array.ndim == 2:
        rgb = np.repeat(array[:, :, None], 3, axis=2)
        return _ensure_uint8(rgb, copy=True)
    if array.ndim != 3:
        raise ValueError(f"Unsupported image array shape: {array.shape}")

    channels = array.shape[2]
    if channels == 1:
        rgb = np.repeat(array, 3, axis=2)
        return _ensure_uint8(rgb, copy=True)
    if channels >= 3:
        return _ensure_uint8(array[:, :, :3], copy=copy)
    raise ValueError(f"Unsupported image channel count: {channels}")


def image_like_to_qimage(image: Any, *, max_pixels: Optional[int] = None) -> Optional[QImage]:
    frame = build_display_image_frame(image, max_pixels=max_pixels)
    return None if frame is None else frame.qimage


def copy_image_like(image: Any) -> Any:
    if image is None:
        return None
    if isinstance(image, Image.Image):
        return image.copy()
    return np.array(image, copy=True)


def image_like_to_pil(image: Any) -> Optional[Image.Image]:
    if image is None:
        return None
    if isinstance(image, Image.Image):
        return image.copy()

    array = np.asarray(image)
    if array.ndim == 2:
        return Image.fromarray(_ensure_uint8(array, copy=False), mode="L")
    if array.ndim != 3:
        raise ValueError(f"Unsupported image array shape: {array.shape}")

    channels = array.shape[2]
    if channels == 1:
        return Image.fromarray(_ensure_uint8(array[:, :, 0], copy=False), mode="L")
    if channels >= 4:
        return Image.fromarray(_ensure_uint8(array[:, :, :4], copy=False), mode="RGBA")
    if channels >= 3:
        return Image.fromarray(_ensure_uint8(array[:, :, :3], copy=False), mode="RGB")
    raise ValueError(f"Unsupported image channel count: {channels}")
