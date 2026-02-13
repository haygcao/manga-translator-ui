"""单区域渲染快照。

目标：一次渲染中 text_block / dst_points / render_params 使用同一份几何数据，
避免 model 与 item 之间的旧数据混用导致位置跳变。
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np


@dataclass
class RegionRenderSnapshot:
    region_index: int
    region_data: Dict[str, Any]
    source_center: Tuple[float, float]         # 源区域中心（世界坐标）
    render_center: Tuple[float, float]         # 白框中心（世界坐标），文字定位锚点
    white_frame_local: Optional[Tuple[float, float, float, float]]
    white_frame_world: Optional[np.ndarray]    # shape (1, 4, 2)

    @classmethod
    def from_sources(
        cls,
        region_index: int,
        region_data: Optional[dict],
        geo_state: Optional[object] = None,
    ) -> RegionRenderSnapshot:
        data = copy.deepcopy(region_data) if isinstance(region_data, dict) else {}

        # 优先合并 item 当前几何，避免"模型旧值"回流
        if geo_state is not None:
            try:
                data.update(geo_state.to_region_data_patch())
                data["center"] = list(geo_state.center)
            except Exception:
                pass

        center = data.get("center", [0.0, 0.0])
        if not (isinstance(center, (list, tuple)) and len(center) >= 2):
            center = [0.0, 0.0]
        cx, cy = float(center[0]), float(center[1])
        source_center = (cx, cy)

        wf_local_raw = data.get("white_frame_rect_local")
        white_frame_local = None
        white_frame_world = None
        render_center = source_center

        if isinstance(wf_local_raw, (list, tuple)) and len(wf_local_raw) == 4:
            left, top, right, bottom = (float(v) for v in wf_local_raw)
            white_frame_local = (left, top, right, bottom)

            theta = math.radians(float(data.get("angle") or 0.0))
            cos_t, sin_t = math.cos(theta), math.sin(theta)

            local_cx = (left + right) / 2.0
            local_cy = (top + bottom) / 2.0
            render_center = (
                cx + local_cx * cos_t - local_cy * sin_t,
                cy + local_cx * sin_t + local_cy * cos_t,
            )

            def _l2w(lx: float, ly: float):
                return [
                    float(cx + lx * cos_t - ly * sin_t),
                    float(cy + lx * sin_t + ly * cos_t),
                ]

            white_frame_world = np.array(
                [[_l2w(left, top), _l2w(right, top),
                  _l2w(right, bottom), _l2w(left, bottom)]],
                dtype=np.float32,
            )

        # 将渲染中心写回快照数据，后续流水线不再隐式改 center
        data["center"] = [render_center[0], render_center[1]]

        return cls(
            region_index=region_index,
            region_data=data,
            source_center=source_center,
            render_center=render_center,
            white_frame_local=white_frame_local,
            white_frame_world=white_frame_world,
        )

    def text_block_input(self) -> Dict[str, Any]:
        """用于构建 TextBlock 的 region_data（深拷贝）。"""
        return copy.deepcopy(self.region_data)

    def style_input(self) -> Dict[str, Any]:
        """用于构建 render_params 的 region_data（深拷贝）。"""
        return copy.deepcopy(self.region_data)
