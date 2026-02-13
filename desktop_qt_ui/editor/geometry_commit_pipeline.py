"""几何编辑提交管线 — 构建旋转 / 白框编辑的 region_data。"""
import copy
from typing import Optional

from manga_translator.rendering import calc_font_from_box


def build_rotate_region_data(
    region_data: dict,
    new_angle: float,
    new_center: Optional[list] = None,
    new_lines: Optional[list] = None,
) -> dict:
    """构建旋转提交数据（可选包含 center / lines 同步）。"""
    data = copy.deepcopy(region_data)
    data["angle"] = float(new_angle)
    if new_center is not None and len(new_center) >= 2:
        data["center"] = [float(new_center[0]), float(new_center[1])]
    if new_lines is not None:
        data["lines"] = copy.deepcopy(new_lines)
    return data


def build_white_frame_region_data(
    region_data: dict,
    white_patch: dict,
    white_frame_local: Optional[list],
) -> dict:
    """构建白框编辑提交数据（含可选字体尺寸回写）。"""
    data = copy.deepcopy(region_data)
    data.update(white_patch)

    new_fs = _calc_font_size(data, white_frame_local)
    if new_fs is not None:
        data["font_size"] = new_fs
    return data


def _calc_font_size(region_data: dict, wf_local: Optional[list]) -> Optional[int]:
    if wf_local is None or len(wf_local) != 4:
        return None
    left, top, right, bottom = wf_local
    w = float(max(0.0, right - left))
    h = float(max(0.0, bottom - top))
    text = region_data.get("translation", "")
    direction = region_data.get("direction", "h")
    is_h = direction in ("h", "horizontal", "hr")
    if not (text and str(text).strip() and w > 0 and h > 0):
        return None
    fs = calc_font_from_box(w, h, text, is_h, region_data.get("line_spacing", 1.0) or 1.0)
    return int(max(8, fs))
