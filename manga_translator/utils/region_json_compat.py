from __future__ import annotations

import math
from typing import Any, MutableMapping, Optional, Sequence, Tuple

import cv2
import numpy as np


def _coerce_pair(value: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(value, (list, tuple, np.ndarray)) or len(value) < 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def _coerce_white_frame_rect(value: Any) -> Optional[Tuple[float, float, float, float]]:
    if not isinstance(value, (list, tuple, np.ndarray)) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    return left, top, right, bottom


def _coerce_points(lines: Any) -> Optional[np.ndarray]:
    try:
        pts = np.asarray(lines, dtype=np.float64)
    except (TypeError, ValueError):
        return None

    if pts.size == 0 or pts.ndim < 2 or pts.shape[-1] != 2:
        return None

    return pts.reshape(-1, 2)


def estimate_region_center_from_lines(lines: Any) -> Optional[Tuple[float, float]]:
    pts = _coerce_points(lines)
    if pts is None or len(pts) == 0:
        return None

    if len(pts) >= 3:
        (cx, cy), _, _ = cv2.minAreaRect(pts.astype(np.float32))
        return float(cx), float(cy)

    center = pts.mean(axis=0)
    return float(center[0]), float(center[1])


def repair_legacy_white_frame_center(
    region_data: MutableMapping[str, Any],
    tolerance: float = 2.0,
) -> bool:
    """Repair JSON written by the buggy editor export path.

    Old editor exports overwrote region["center"] with the white-frame center,
    while still saving white_frame_rect_local relative to the original rotation
    center. Re-opening that JSON applies the white-frame offset twice.
    """

    white_frame = _coerce_white_frame_rect(region_data.get("white_frame_rect_local"))
    stored_center = _coerce_pair(region_data.get("center"))
    if white_frame is None or stored_center is None:
        return False

    local_cx = (white_frame[0] + white_frame[2]) / 2.0
    local_cy = (white_frame[1] + white_frame[3]) / 2.0
    if math.hypot(local_cx, local_cy) <= tolerance:
        return False

    source_center = estimate_region_center_from_lines(region_data.get("lines"))
    if source_center is None:
        return False

    if math.dist(stored_center, source_center) <= tolerance:
        return False

    angle = float(region_data.get("angle") or 0.0)
    theta = math.radians(angle)
    rotated_offset = (
        local_cx * math.cos(theta) - local_cy * math.sin(theta),
        local_cx * math.sin(theta) + local_cy * math.cos(theta),
    )
    expected_buggy_center = (
        source_center[0] + rotated_offset[0],
        source_center[1] + rotated_offset[1],
    )

    if math.dist(stored_center, expected_buggy_center) > tolerance:
        return False

    region_data["center"] = [source_center[0], source_center[1]]
    return True
