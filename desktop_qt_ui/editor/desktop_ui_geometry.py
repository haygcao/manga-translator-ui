"""
完全基于 desktop-ui 的几何系统
替换 Qt 的坐标系统，使用 desktop-ui 的数据结构和算法
"""
import math
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPolygonF

# === desktop-ui 的核心几何函数 ===

def rotate_point(x, y, angle_deg, cx, cy):
    """围绕中心点旋转一个点"""
    angle_rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    x_new = cx + (x - cx) * cos_a - (y - cy) * sin_a
    y_new = cy + (x - cx) * sin_a + (y - cy) * cos_a
    return x_new, y_new

def get_polygon_center(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    计算多边形的中心点（边界框中心）

    注意：lines存储的是未旋转的世界坐标，所以这里计算的是
    这些未旋转坐标的简单边界框中心，不使用cv2.minAreaRect
    """
    if not vertices:
        return 0, 0

    # 直接计算边界框中心（对于未旋转的坐标）
    x_coords = [v[0] for v in vertices]
    y_coords = [v[1] for v in vertices]

    if not x_coords or not y_coords:
        return 0, 0

    center_x = (min(x_coords) + max(x_coords)) / 2
    center_y = (min(y_coords) + max(y_coords)) / 2

    return center_x, center_y

def extract_rectangle_params(polygon):
    """
    从四边形提取矩形参数
    返回: (center_x, center_y, width, height, angle_rad)
    """
    if len(polygon) != 4:
        # 不是四边形,返回边界框
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        center_x = (min(xs) + max(xs)) / 2
        center_y = (min(ys) + max(ys)) / 2
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return (center_x, center_y, width, height, 0.0)

    # 使用 cv2.minAreaRect 提取参数
    points_np = np.array(polygon, dtype=np.float32)
    (center_x, center_y), (w, h), angle_deg = cv2.minAreaRect(points_np)

    # cv2.minAreaRect 返回的角度范围是 [-90, 0)
    # 转换为弧度
    angle_rad = math.radians(angle_deg)

    return (center_x, center_y, w, h, angle_rad)

def build_rectangle(center_x, center_y, width, height, angle_rad):
    """
    根据参数构建矩形的四个顶点
    返回: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    """
    # 半宽和半高
    hw = width / 2
    hh = height / 2

    # 未旋转的四个顶点(相对于中心)
    corners_local = [
        [-hw, -hh],  # 左上
        [hw, -hh],   # 右上
        [hw, hh],    # 右下
        [-hw, hh]    # 左下
    ]

    # 旋转并平移到世界坐标
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    corners_world = []
    for lx, ly in corners_local:
        wx = center_x + lx * cos_a - ly * sin_a
        wy = center_y + lx * sin_a + ly * cos_a
        corners_world.append([wx, wy])

    return corners_world

def _project_vector(v_to_project: Tuple[float, float], v_target: Tuple[float, float]) -> Tuple[float, float]:
    """将一个向量投影到另一个向量上"""
    dot_product = v_to_project[0] * v_target[0] + v_to_project[1] * v_target[1]
    target_len_sq = v_target[0]**2 + v_target[1]**2
    if target_len_sq < 1e-9:
        return (0, 0)
    scale = dot_product / target_len_sq
    return (v_target[0] * scale, v_target[1] * scale)

def calculate_rectangle_from_diagonal(start_point, end_point, angle_deg):
    """
    Calculates the four vertices of a rectangle whose diagonal is defined by
    start_point and end_point, and whose sides are aligned with a given angle.
    """
    angle_rad = math.radians(angle_deg)
    
    # World-space direction vectors for the rotated axes
    u_x_axis = (math.cos(angle_rad), math.sin(angle_rad))
    u_y_axis = (-math.sin(angle_rad), math.cos(angle_rad))
    
    # The vector of the dragged diagonal
    vec_drag = (end_point[0] - start_point[0], end_point[1] - start_point[1])
    
    # Project the drag vector onto the rotated axes to find the side vectors
    vec_width = _project_vector(vec_drag, u_x_axis)
    vec_height = _project_vector(vec_drag, u_y_axis)
    
    # Calculate the four corners in order for drawing
    p1 = start_point
    p2 = (start_point[0] + vec_width[0], start_point[1] + vec_width[1])
    p3 = end_point
    p4 = (start_point[0] + vec_height[0], start_point[1] + vec_height[1])
    
    return [p1, p2, p3, p4]

def calculate_new_vertices_on_drag(
    original_vertices: List[Tuple[float, float]],
    dragged_vertex_index: int,
    new_mouse_position: Tuple[float, float],
    angle: float = 0,
    center: Optional[Tuple[float, float]] = None
) -> List[Tuple[float, float]]:
    """当单个顶点被拖拽时，计算所有顶点的新位置。"""
    
    rotation_center = center if center else get_polygon_center(original_vertices)

    # For non-quadrilaterals, use simple logic
    if len(original_vertices) != 4:
        if angle != 0:
             new_mouse_position = rotate_point(new_mouse_position[0], new_mouse_position[1], -angle, rotation_center[0], rotation_center[1])
        new_vertices_fallback = list(original_vertices)
        new_vertices_fallback[dragged_vertex_index] = new_mouse_position
        return new_vertices_fallback

    # --- Corrected logic for rotated parallelograms ---
    # 1. Identify points in model space
    p_drag_idx = dragged_vertex_index
    p_anchor_idx = (p_drag_idx + 2) % 4
    p_adj1_idx = (p_drag_idx - 1 + 4) % 4
    p_adj2_idx = (p_drag_idx + 1) % 4

    p_anchor_model = original_vertices[p_anchor_idx]

    # If not rotated, use the original simple (but flawed) projection logic for now
    if angle == 0:
        p_adj1_orig = original_vertices[p_adj1_idx]
        p_adj2_orig = original_vertices[p_adj2_idx]
        v_anchor_adj1 = (p_adj1_orig[0] - p_anchor_model[0], p_adj1_orig[1] - p_anchor_model[1])
        v_anchor_adj2 = (p_adj2_orig[0] - p_anchor_model[0], p_adj2_orig[1] - p_anchor_model[1])
        v_anchor_mouse = (new_mouse_position[0] - p_anchor_model[0], new_mouse_position[1] - p_anchor_model[1])
        v_new_adj1 = _project_vector(v_anchor_mouse, v_anchor_adj1)
        v_new_adj2 = _project_vector(v_anchor_mouse, v_anchor_adj2)
        new_p_adj1 = (p_anchor_model[0] + v_new_adj1[0], p_anchor_model[1] + v_new_adj1[1])
        new_p_adj2 = (p_anchor_model[0] + v_new_adj2[0], p_anchor_model[1] + v_new_adj2[1])
        new_p_drag = (p_anchor_model[0] + v_new_adj1[0] + v_new_adj2[0], p_anchor_model[1] + v_new_adj1[1] + v_new_adj2[1])
        new_vertices = [ (0,0) ] * 4
        new_vertices[p_anchor_idx] = p_anchor_model
        new_vertices[p_adj1_idx] = new_p_adj1
        new_vertices[p_adj2_idx] = new_p_adj2
        new_vertices[p_drag_idx] = new_p_drag
        return new_vertices

    # --- Logic for rotated parallelograms ---
    # 1. Rotate anchor to world space
    p_anchor_world = rotate_point(p_anchor_model[0], p_anchor_model[1], angle, rotation_center[0], rotation_center[1])

    # 2. Calculate mouse drag vector in world space
    v_mouse_drag_world = (new_mouse_position[0] - p_anchor_world[0], new_mouse_position[1] - p_anchor_world[1])

    # 3. Un-rotate the mouse drag vector to get the drag in model space
    v_mouse_drag_model_x, v_mouse_drag_model_y = rotate_point(v_mouse_drag_world[0], v_mouse_drag_world[1], -angle, 0, 0)
    v_mouse_drag_model = (v_mouse_drag_model_x, v_mouse_drag_model_y)

    # 4. Decompose the model-space drag vector along the model-space sides
    p_adj1_model = original_vertices[p_adj1_idx]
    p_adj2_model = original_vertices[p_adj2_idx]
    v_side1_model = (p_adj1_model[0] - p_anchor_model[0], p_adj1_model[1] - p_anchor_model[1])
    v_side2_model = (p_adj2_model[0] - p_anchor_model[0], p_adj2_model[1] - p_anchor_model[1])

    # We need to solve v_mouse_drag_model = c1*v_side1_model + c2*v_side2_model for c1, c2
    # This is a 2x2 system of linear equations
    m_det = v_side1_model[0] * v_side2_model[1] - v_side1_model[1] * v_side2_model[0]
    if abs(m_det) < 1e-9: # Sides are collinear, cannot decompose
        return original_vertices

    # Using Cramer's rule to solve for c1 and c2
    c1 = (v_mouse_drag_model[0] * v_side2_model[1] - v_mouse_drag_model[1] * v_side2_model[0]) / m_det
    c2 = (v_side1_model[0] * v_mouse_drag_model[1] - v_side1_model[1] * v_mouse_drag_model[0]) / m_det

    # 5. Calculate new model-space points
    new_p_adj1_model = (p_anchor_model[0] + c1 * v_side1_model[0], p_anchor_model[1] + c1 * v_side1_model[1])
    new_p_adj2_model = (p_anchor_model[0] + c2 * v_side2_model[0], p_anchor_model[1] + c2 * v_side2_model[1])
    new_p_drag_model = (new_p_adj1_model[0] + (new_p_adj2_model[0] - p_anchor_model[0]), new_p_adj1_model[1] + (new_p_adj2_model[1] - p_anchor_model[1]))

    # 6. Assemble final list
    new_vertices = [ (0,0) ] * 4
    new_vertices[p_anchor_idx] = p_anchor_model
    new_vertices[p_adj1_idx] = new_p_adj1_model
    new_vertices[p_adj2_idx] = new_p_adj2_model
    new_vertices[p_drag_idx] = new_p_drag_model
    
    return new_vertices

def calculate_new_edge_on_drag(
    original_vertices: List[Tuple[float, float]],
    dragged_edge_index: int,
    new_mouse_position: Tuple[float, float],
    angle: float = 0,
    center: Optional[Tuple[float, float]] = None
) -> List[Tuple[float, float]]:
    """当边缘被拖拽时，计算新的顶点位置 (沿法线移动)"""
    
    rotation_center = center if center else get_polygon_center(original_vertices)

    # 1. Get edge vertices in model space
    v1_model_idx = dragged_edge_index
    v2_model_idx = (v1_model_idx + 1) % len(original_vertices)
    v1_model = original_vertices[v1_model_idx]
    v2_model = original_vertices[v2_model_idx]

    # 2. Rotate them to world space to find the visual edge and its normal
    v1_world = rotate_point(v1_model[0], v1_model[1], angle, rotation_center[0], rotation_center[1])
    v2_world = rotate_point(v2_model[0], v2_model[1], angle, rotation_center[0], rotation_center[1])

    # 3. Calculate the edge normal in world space
    edge_vector_world_x = v2_world[0] - v1_world[0]
    edge_vector_world_y = v2_world[1] - v1_world[1]
    normal_vector_world_x = -edge_vector_world_y
    normal_vector_world_y = edge_vector_world_x
    
    norm_len = math.hypot(normal_vector_world_x, normal_vector_world_y)
    if norm_len == 0: return original_vertices

    unit_normal_world_x = normal_vector_world_x / norm_len
    unit_normal_world_y = normal_vector_world_y / norm_len

    # 4. Project the mouse drag vector onto the world-space normal
    mouse_drag_vector_world_x = new_mouse_position[0] - v1_world[0]
    mouse_drag_vector_world_y = new_mouse_position[1] - v1_world[1]
    
    projection_length = mouse_drag_vector_world_x * unit_normal_world_x + mouse_drag_vector_world_y * unit_normal_world_y
    
    # 5. Calculate the offset vector in world space
    offset_world_x = projection_length * unit_normal_world_x
    offset_world_y = projection_length * unit_normal_world_y

    # 6. Un-rotate the world-space offset vector back to model space
    offset_model_x, offset_model_y = rotate_point(offset_world_x, offset_world_y, -angle, 0, 0)

    # Correction: For near-rectangular shapes, ensure offset is only along one axis in model space
    # to prevent drift when dragging edges.
    model_edge_dx = abs(v2_model[0] - v1_model[0])
    model_edge_dy = abs(v2_model[1] - v1_model[1])
    if model_edge_dx > model_edge_dy: # Horizontal edge
        offset_model_x = 0
    else: # Vertical edge
        offset_model_y = 0

    # 7. Apply the model-space offset to the two vertices of the edge
    new_vertices = list(original_vertices)
    
    new_v1_model = (v1_model[0] + offset_model_x, v1_model[1] + offset_model_y)
    new_v2_model = (v2_model[0] + offset_model_x, v2_model[1] + offset_model_y)

    new_vertices[v1_model_idx] = new_v1_model
    new_vertices[v2_model_idx] = new_v2_model
        
    return new_vertices

# === desktop-ui 的数据结构管理器 ===

class DesktopUIGeometry:
    """
    完全基于 desktop-ui 的几何管理器
    使用 desktop-ui 的数据结构：lines, center, angle
    """
    
    def __init__(self, region_data: Dict[str, Any]):
        self.lines = region_data.get('lines', [])  # List[List[Tuple[float, float]]]
        self.angle = region_data.get('angle', 0)  # degrees

        # 如果传入了 center,使用传入的值
        # 否则从 lines 重新计算 center
        if 'center' in region_data:
            self.center = region_data['center']
        else:
            all_vertices = [vertex for poly in self.lines for vertex in poly]
            if all_vertices:
                center_x, center_y = get_polygon_center(all_vertices)
                self.center = [center_x, center_y]
            else:
                self.center = [0, 0]
        
    def get_all_vertices(self) -> List[Tuple[float, float]]:
        """获取所有顶点"""
        return [vertex for poly in self.lines for vertex in poly]
    
    def get_world_polygons(self) -> List[List[Tuple[float, float]]]:
        """获取世界坐标下的多边形"""
        if self.angle == 0:
            return [poly[:] for poly in self.lines]
        
        world_polygons = []
        for poly_model in self.lines:
            poly_world = [rotate_point(p[0], p[1], self.angle, self.center[0], self.center[1]) for p in poly_model]
            world_polygons.append(poly_world)
        return world_polygons
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """获取边界框 (min_x, max_x, min_y, max_y)"""
        world_polygons = self.get_world_polygons()
        all_vertices = [vertex for poly in world_polygons for vertex in poly]
        if not all_vertices:
            return 0, 0, 0, 0
        
        min_x = min(p[0] for p in all_vertices)
        max_x = max(p[0] for p in all_vertices)
        min_y = min(p[1] for p in all_vertices)
        max_y = max(p[1] for p in all_vertices)
        return min_x, max_x, min_y, max_y
    
    def get_white_frame_bounds(self, padding: float = 40) -> Tuple[float, float, float, float]:
        """获取白框边界 (left, top, right, bottom)"""
        min_x, max_x, min_y, max_y = self.get_bounds()
        return min_x - padding, min_y - padding, max_x + padding, max_y + padding
    
    def to_qt_polygons(self) -> List[QPolygonF]:
        """转换为 Qt 多边形用于显示（返回世界坐标）"""
        world_polygons = self.get_world_polygons()
        return [QPolygonF([QPointF(p[0], p[1]) for p in poly]) for poly in world_polygons]
    
    def to_region_data(self) -> Dict[str, Any]:
        """转换回 region_data 格式"""
        return {
            'lines': self.lines,
            'center': self.center,
            'angle': self.angle
        }

# === desktop-ui 的白框编辑逻辑 ===

def handle_white_frame_edit(
    geometry: DesktopUIGeometry,
    action_type: str,  # 'white_frame_corner_edit' or 'white_frame_edge_edit'
    handle_index: int,
    mouse_x: float,
    mouse_y: float,
    white_frame_model_rect: List[float] = None,  # [left, top, right, bottom] 模型坐标，可选
    start_mouse_x: float = None,
    start_mouse_y: float = None,
) -> Optional[Dict[str, Any]]:
    """
    处理白框编辑 - 在世界坐标系中进行边编辑
    white_frame_model_rect: 如果提供，使用这个作为白框起始位置（模型坐标），否则从源区域边界+padding计算
    """
    center = geometry.center
    angle = geometry.angle
    original_lines = geometry.lines
    padding = 40

    # 1. 计算源区域在模型坐标系中的边界（仅用于白框初始值）
    all_vertices_model = [vertex for poly in original_lines for vertex in poly]
    if not all_vertices_model:
        return None

    model_min_x = min(v[0] for v in all_vertices_model)
    model_max_x = max(v[0] for v in all_vertices_model)
    model_min_y = min(v[1] for v in all_vertices_model)
    model_max_y = max(v[1] for v in all_vertices_model)

    # 2. 构建原始白框(模型坐标,轴对齐)
    if white_frame_model_rect is not None:
        wl, wt, wr, wb = white_frame_model_rect
        old_white_frame_model = [
            [wl, wt],  # 左上
            [wr, wt],  # 右上
            [wr, wb],  # 右下
            [wl, wb],  # 左下
        ]
    else:
        old_white_frame_model = [
            [model_min_x - padding, model_min_y - padding],  # 左上
            [model_max_x + padding, model_min_y - padding],  # 右上
            [model_max_x + padding, model_max_y + padding],  # 右下
            [model_min_x - padding, model_max_y + padding],  # 左下
        ]

    # 3. 将白框转换到世界坐标系
    if angle != 0:
        old_white_frame_world = [
            rotate_point(p[0], p[1], angle, center[0], center[1]) for p in old_white_frame_model
        ]
    else:
        old_white_frame_world = old_white_frame_model[:]

    # 4. 根据拖动类型计算新的白框(世界坐标)
    if action_type == 'white_frame_edge_edit':
        edge_idx = handle_index
        v1_world = old_white_frame_world[edge_idx]
        v2_world = old_white_frame_world[(edge_idx + 1) % 4]

        edge_vec_x = v2_world[0] - v1_world[0]
        edge_vec_y = v2_world[1] - v1_world[1]
        normal_x = edge_vec_y
        normal_y = -edge_vec_x

        norm_len = math.hypot(normal_x, normal_y)
        if norm_len < 1e-9:
            return None

        unit_normal_x = normal_x / norm_len
        unit_normal_y = normal_y / norm_len

        edge_center_x = (v1_world[0] + v2_world[0]) / 2
        edge_center_y = (v1_world[1] + v2_world[1]) / 2
        mouse_offset_x = mouse_x - edge_center_x
        mouse_offset_y = mouse_y - edge_center_y
        projection_dist = mouse_offset_x * unit_normal_x + mouse_offset_y * unit_normal_y
        if start_mouse_x is not None and start_mouse_y is not None:
            start_offset_x = start_mouse_x - edge_center_x
            start_offset_y = start_mouse_y - edge_center_y
            start_projection = start_offset_x * unit_normal_x + start_offset_y * unit_normal_y
            projection_dist -= start_projection

        new_v1_world = [
            v1_world[0] + projection_dist * unit_normal_x,
            v1_world[1] + projection_dist * unit_normal_y,
        ]
        new_v2_world = [
            v2_world[0] + projection_dist * unit_normal_x,
            v2_world[1] + projection_dist * unit_normal_y,
        ]

        new_white_frame_world = old_white_frame_world[:]
        new_white_frame_world[edge_idx] = new_v1_world
        new_white_frame_world[(edge_idx + 1) % 4] = new_v2_world
    else:  # white_frame_corner_edit
        corner_idx = handle_index
        if angle != 0:
            mouse_model_x, mouse_model_y = rotate_point(mouse_x, mouse_y, -angle, center[0], center[1])
        else:
            mouse_model_x, mouse_model_y = mouse_x, mouse_y

        anchor_corner_idx = (corner_idx + 2) % 4
        anchor_point_model = old_white_frame_model[anchor_corner_idx]
        new_white_frame_model = [
            [min(anchor_point_model[0], mouse_model_x), min(anchor_point_model[1], mouse_model_y)],
            [max(anchor_point_model[0], mouse_model_x), min(anchor_point_model[1], mouse_model_y)],
            [max(anchor_point_model[0], mouse_model_x), max(anchor_point_model[1], mouse_model_y)],
            [min(anchor_point_model[0], mouse_model_x), max(anchor_point_model[1], mouse_model_y)],
        ]

        if angle != 0:
            new_white_frame_world = [
                rotate_point(p[0], p[1], angle, center[0], center[1]) for p in new_white_frame_model
            ]
        else:
            new_white_frame_world = new_white_frame_model[:]

    # 5. 新白框世界坐标 -> 模型坐标（保持区域中心不变）
    if angle != 0:
        new_white_frame_model = [
            rotate_point(p[0], p[1], -angle, center[0], center[1]) for p in new_white_frame_world
        ]
    else:
        new_white_frame_model = new_white_frame_world[:]

    wf_min_x = min(p[0] for p in new_white_frame_model)
    wf_max_x = max(p[0] for p in new_white_frame_model)
    wf_min_y = min(p[1] for p in new_white_frame_model)
    wf_max_y = max(p[1] for p in new_white_frame_model)

    return {
        'white_frame_rect_local': [
            wf_min_x - center[0],
            wf_min_y - center[1],
            wf_max_x - center[0],
            wf_max_y - center[1],
        ]
    }

