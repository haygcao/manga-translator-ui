"""
统一区域几何数据模型 — 纯数据类（无 Qt 依赖）

管理两个几何来源：
- 源区域（检测区域）：lines, center, angle  →  派生 polygons_local
- 白框（渲染区域 / 手动边界）：自动模式 = 渲染框；手动模式 = 用户拖动后持久化

坐标系约定：
- 世界坐标（world / model）：图片像素坐标
- 局部坐标（local）：以 center 为原点、未旋转的坐标系
  world_to_local:  dx, dy = world - center;  lx = dx*cos + dy*sin;  ly = -dx*sin + dy*cos
  local_to_world:  wx = cx + lx*cos - ly*sin;  wy = cy + lx*sin + ly*cos
"""
import copy
import math
from typing import List, Optional, Tuple

import numpy as np


class RegionGeometryState:
    """统一管理源区域 / 白框几何状态的纯数据类。"""

    # ------------------------------------------------------------------
    # 构造
    # ------------------------------------------------------------------

    def __init__(
        self,
        lines: list,
        center: List[float],
        angle: float,
        white_frame_local: Optional[List[float]] = None,
        has_custom_white_frame: bool = False,
    ):
        self.lines = lines                   # List[List[[x, y]]]（世界坐标）
        self.center = list(center)           # [cx, cy]
        self.angle = float(angle)            # degrees

        # 派生：源区域各多边形在局部坐标系中的顶点
        self.polygons_local: List[List[List[float]]] = []
        self._rebuild_polygons_local()

        # 白框（局部坐标 [left, top, right, bottom]）
        self._white_frame_local: Optional[List[float]] = (
            list(white_frame_local) if white_frame_local is not None else None
        )
        self.has_custom_white_frame: bool = has_custom_white_frame

        # 没有给定白框 → 自动从源区域计算
        if self._white_frame_local is None:
            self._auto_update_white_frame()

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def white_frame_local(self) -> Optional[List[float]]:
        return self._white_frame_local

    # ------------------------------------------------------------------
    # 坐标变换（纯计算，无状态修改）
    # ------------------------------------------------------------------

    def _angle_trig(self) -> Tuple[float, float]:
        rad = math.radians(self.angle)
        return math.cos(rad), math.sin(rad)

    def world_to_local(self, wx: float, wy: float) -> Tuple[float, float]:
        cos_a, sin_a = self._angle_trig()
        dx = wx - self.center[0]
        dy = wy - self.center[1]
        return (dx * cos_a + dy * sin_a,
                -dx * sin_a + dy * cos_a)

    def local_to_world(self, lx: float, ly: float) -> Tuple[float, float]:
        cos_a, sin_a = self._angle_trig()
        return (self.center[0] + lx * cos_a - ly * sin_a,
                self.center[1] + lx * sin_a + ly * cos_a)

    def white_frame_center_world(self) -> Optional[Tuple[float, float]]:
        """白框中心的世界坐标，供外部文字定位使用。"""
        if self._white_frame_local is None:
            return None
        left, top, right, bottom = self._white_frame_local
        return self.local_to_world((left + right) / 2.0, (top + bottom) / 2.0)

    # ------------------------------------------------------------------
    # 工厂
    # ------------------------------------------------------------------

    @classmethod
    def from_region_data(
        cls,
        region_data: dict,
        prev_state: Optional["RegionGeometryState"] = None,
    ) -> "RegionGeometryState":
        lines = region_data.get("lines", [])
        center = region_data.get("center")
        angle = region_data.get("angle", 0)

        if center is None:
            all_verts = [v for poly in lines for v in poly]
            if all_verts:
                xs = [v[0] for v in all_verts]
                ys = [v[1] for v in all_verts]
                center = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
            else:
                center = [0, 0]

        # 尝试从 region_data 恢复白框
        wf_local = region_data.get("white_frame_rect_local")
        has_custom = region_data.get("has_custom_white_frame", False)
        has_custom_explicit = "has_custom_white_frame" in region_data
        wf_explicit = "white_frame_rect_local" in region_data

        # 仅当本次数据没有显式给出白框状态时，才继承上一次自定义白框
        if (
            prev_state is not None
            and prev_state.has_custom_white_frame
            and not has_custom_explicit
            and not wf_explicit
        ):
            wf_local = (
                list(prev_state._white_frame_local)
                if prev_state._white_frame_local is not None else None
            )
            has_custom = True

        return cls(
            lines=lines,
            center=center,
            angle=angle,
            white_frame_local=wf_local if has_custom else None,
            has_custom_white_frame=has_custom,
        )

    # ------------------------------------------------------------------
    # 白框操作
    # ------------------------------------------------------------------

    def set_render_box(self, dst_points: Optional[np.ndarray]):
        """接收渲染框（世界坐标），在自动模式下同步到白框。

        dst_points 是世界坐标系中的轴对齐矩形 4 角点 (shape: [1,4,2] 或 [4,2])。
        我们将其转为局部坐标，用中心 + 邻边长度重建局部 AABB（避免旋转后的 min/max 误差）。
        """
        if dst_points is None:
            if self._white_frame_local is None:
                self._auto_update_white_frame()
            return

        # 展平为 (4, 2)
        pts_world = dst_points.reshape(-1, 2) if len(dst_points.shape) == 3 else dst_points
        if pts_world is None or len(pts_world) < 4:
            if self._white_frame_local is None:
                self._auto_update_white_frame()
            return

        # 世界 → 局部
        pts_local = np.array(
            [self.world_to_local(float(p[0]), float(p[1])) for p in pts_world[:4]],
            dtype=np.float64,
        )

        # 用中心 + 邻边宽高重建局部 AABB
        cpx = float(np.mean(pts_local[:, 0]))
        cpy = float(np.mean(pts_local[:, 1]))
        width = float(np.hypot(pts_local[1][0] - pts_local[0][0],
                               pts_local[1][1] - pts_local[0][1]))
        height = float(np.hypot(pts_local[3][0] - pts_local[0][0],
                                pts_local[3][1] - pts_local[0][1]))
        if width <= 0.0 or height <= 0.0:
            if self._white_frame_local is None:
                self._auto_update_white_frame()
            return

        hw, hh = width / 2.0, height / 2.0
        self._white_frame_local = [cpx - hw, cpy - hh, cpx + hw, cpy + hh]

    def set_custom_white_frame_local(self, rect_local: List[float]):
        """用户拖白框时调用 — 标记 has_custom_white_frame = True。"""
        self._white_frame_local = list(rect_local)
        self.has_custom_white_frame = True

    def get_white_frame_model_for_drag_start(self) -> Optional[List[float]]:
        """当前白框的模型坐标 (left, top, right, bottom)，用作拖动起点。

        局部坐标 + center = 模型坐标（注意：这是未旋转的"建模坐标"，不是世界坐标）。
        """
        if self._white_frame_local is None:
            return None
        cx, cy = self.center
        left, top, right, bottom = self._white_frame_local
        return [left + cx, top + cy, right + cx, bottom + cy]

    def to_region_data_patch(self) -> dict:
        """序列化白框状态为可合并到 region_data 的补丁字典。"""
        patch = {"has_custom_white_frame": self.has_custom_white_frame}
        if self._white_frame_local is not None:
            patch["white_frame_rect_local"] = list(self._white_frame_local)
        return patch

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _rebuild_polygons_local(self):
        cx, cy = self.center
        self.polygons_local = [
            [[x - cx, y - cy] for x, y in line]
            for line in self.lines
        ]

    def _auto_update_white_frame(self):
        all_pts = [p for poly in self.polygons_local for p in poly]
        if not all_pts:
            self._white_frame_local = None
            return
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        self._white_frame_local = [min(xs), min(ys), max(xs), max(ys)]
