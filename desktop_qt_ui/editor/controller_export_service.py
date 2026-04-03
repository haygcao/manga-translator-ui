from __future__ import annotations

import asyncio
import copy
import math
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from services import get_render_parameter_service

from manga_translator.utils.path_manager import (
    find_inpainted_path,
    find_json_path,
    get_inpainted_path,
    get_json_path,
)

from .image_utils import image_like_to_pil, image_like_to_rgb_array

if TYPE_CHECKING:
    from .editor_controller import EditorController


class EditorControllerExportService:
    """导出与导出前持久化流程。"""

    def __init__(self, controller: "EditorController"):
        self.controller = controller

    @property
    def model(self):
        return self.controller.model

    @property
    def logger(self):
        return self.controller.logger

    @property
    def config_service(self):
        return self.controller.config_service

    @property
    def resource_manager(self):
        return self.controller.resource_manager

    @property
    def async_service(self):
        return self.controller.async_service

    def generate_export_snapshot(self) -> dict:
        regions = self.controller._get_regions()
        snapshot_data = []
        for region in regions:
            region_key = {
                "translation": region.get("translation", ""),
                "font_size": region.get("font_size"),
                "font_color": region.get("font_color"),
                "alignment": region.get("alignment"),
                "direction": region.get("direction"),
                "xyxy": region.get("xyxy"),
                "lines": str(region.get("lines", [])),
            }
            snapshot_data.append(str(region_key))

        mask = self.model.get_refined_mask()
        if mask is None:
            mask = self.model.get_raw_mask()
        mask_signature = ""
        if mask is not None:
            mask_signature = f"{mask.shape}_{mask.sum()}_{np.count_nonzero(mask)}"

        return {
            "regions_hash": hash("|".join(snapshot_data)),
            "mask_signature": mask_signature,
            "source_path": self.model.get_source_image_path(),
        }

    def has_changes_since_last_export(self) -> bool:
        if self.controller._last_export_snapshot is None:
            return self.controller.history_service.can_undo()

        current_snapshot = self.generate_export_snapshot()
        if current_snapshot["source_path"] != self.controller._last_export_snapshot["source_path"]:
            return self.controller.history_service.can_undo()

        return (
            current_snapshot["regions_hash"] != self.controller._last_export_snapshot["regions_hash"]
            or current_snapshot["mask_signature"] != self.controller._last_export_snapshot["mask_signature"]
        )

    def save_export_snapshot(self) -> None:
        self.controller._last_export_snapshot = self.generate_export_snapshot()
        self.logger.debug(f"Export snapshot saved: {self.controller._last_export_snapshot}")

    def export_image(self):
        try:
            image = self.controller._get_current_image()
            regions = self.controller._get_regions()
            source_path = self.model.get_source_image_path()

            if image is None:
                self.logger.warning("Cannot export: missing image data")
                toast_manager = self.controller.get_toast_manager()
                if toast_manager is not None:
                    toast_manager.show_error("导出失败：缺少图像数据")
                return

            if regions is None:
                regions = []

            mask = self.model.get_refined_mask()
            if mask is None:
                mask = self.model.get_raw_mask()
            if mask is None and regions:
                self.logger.warning("Cannot export: no mask data available for regions")
                toast_manager = self.controller.get_toast_manager()
                if toast_manager is not None:
                    toast_manager.show_error("导出失败：没有可用的蒙版数据")
                return None

            self.controller._export_toast = None
            toast_manager = self.controller.get_toast_manager()
            if toast_manager is not None:
                self.controller._export_toast = toast_manager.show_info("正在导出...", duration=0)

            image_snapshot = self.controller._snapshot_image_for_export(image, "base image")
            inpainted_snapshot = self.controller._snapshot_image_for_export(
                self.model.get_inpainted_image(),
                "inpainted image",
            )
            regions_snapshot = copy.deepcopy(regions)
            mask_snapshot = None if mask is None else np.array(mask, copy=True)

            return self.async_service.submit_task(
                self.async_export_with_desktop_ui_service(
                    image_snapshot,
                    regions_snapshot,
                    mask_snapshot,
                    source_path,
                    inpainted_snapshot,
                )
            )
        except Exception as e:
            self.logger.error(f"Error during export request: {e}", exc_info=True)
            toast_manager = self.controller.get_toast_manager()
            if toast_manager is not None:
                toast_manager.show_error("导出失败")
            return None

    @staticmethod
    def resolve_effective_box_local(region: dict):
        if not isinstance(region, dict):
            return None

        custom_box = region.get("white_frame_rect_local")
        render_box = region.get("render_box_rect_local")
        has_custom = bool(region.get("has_custom_white_frame", False))

        if isinstance(render_box, (list, tuple)) and len(render_box) == 4:
            return render_box
        if isinstance(custom_box, (list, tuple)) and len(custom_box) == 4 and has_custom:
            return custom_box
        if isinstance(custom_box, (list, tuple)) and len(custom_box) == 4:
            return custom_box
        return None

    @classmethod
    def apply_white_frame_center(cls, region: dict) -> None:
        wf_local = cls.resolve_effective_box_local(region)
        base_center = region.get("center")
        if not (
            isinstance(wf_local, (list, tuple))
            and len(wf_local) == 4
            and isinstance(base_center, (list, tuple))
            and len(base_center) >= 2
        ):
            return
        try:
            left, top, right, bottom = (float(v) for v in wf_local)
            lx = (left + right) / 2.0
            ly = (top + bottom) / 2.0
            cx, cy = float(base_center[0]), float(base_center[1])
            angle = float(region.get("angle") or 0.0)
            rad = math.radians(angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            region["center"] = [cx + lx * cos_a - ly * sin_a, cy + lx * sin_a + ly * cos_a]
        except (TypeError, ValueError):
            return

    def resolve_editor_json_path(self, source_path: str) -> str:
        json_path = find_json_path(source_path)
        if not json_path:
            json_path = get_json_path(source_path, create_dir=True)
            self.logger.info(f"No existing JSON found, will create new one at: {json_path}")
        else:
            self.logger.info(f"Found existing JSON, will replace: {json_path}")
        return json_path

    def save_current_inpainted_image(
        self,
        source_path: str,
        config_dict: dict,
        mask: Optional[np.ndarray],
        current_inpainted_image: Optional[object] = None,
        has_regions: bool = False,
    ) -> None:
        try:
            image_to_save = current_inpainted_image
            if image_to_save is None:
                image_to_save = self.model.get_inpainted_image()
            if image_to_save is None:
                if mask is not None or has_regions:
                    existing_inpainted_path = find_inpainted_path(source_path)
                    if existing_inpainted_path and os.path.exists(existing_inpainted_path):
                        self.logger.info(
                            "No live inpainted preview during export, keep existing inpainted image: %s",
                            existing_inpainted_path,
                        )
                    else:
                        self.logger.warning(
                            "Skipped updating inpainted image during export because no inpainted preview is available yet: %s",
                            source_path,
                        )
                    return
                image_to_save = self.model.get_image()
            if image_to_save is None:
                return

            inpainted_path = get_inpainted_path(source_path, create_dir=True)
            save_quality = config_dict.get("cli", {}).get("save_quality", 95)

            save_image = image_like_to_pil(image_to_save)
            if save_image is None:
                return
            try:
                save_kwargs = {}
                if inpainted_path.lower().endswith((".jpg", ".jpeg")):
                    if save_image.mode in ("RGBA", "LA"):
                        converted_image = save_image.convert("RGB")
                        save_image.close()
                        save_image = converted_image
                    save_kwargs["quality"] = save_quality
                elif inpainted_path.lower().endswith(".webp"):
                    save_kwargs["quality"] = save_quality

                save_image.save(inpainted_path, **save_kwargs)

                if self.controller._is_same_source_image(self.model.get_source_image_path(), source_path):
                    self.model.set_inpainted_image_path(inpainted_path)
                    self.resource_manager.set_cache(
                        self.controller.CACHE_LAST_INPAINTED,
                        image_like_to_rgb_array(save_image, copy=True),
                    )
                    if mask is not None:
                        mask_to_cache = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) if len(mask.shape) == 3 else mask
                        self.resource_manager.set_cache(
                            self.controller.CACHE_LAST_MASK,
                            np.array(mask_to_cache, copy=True),
                        )
                else:
                    self.logger.debug(
                        "Skipped runtime inpaint cache update because active image changed during export"
                    )

                self.logger.info(f"已更新修复图片: {inpainted_path}")
            finally:
                try:
                    save_image.close()
                except Exception:
                    pass
        except Exception as e:
            self.logger.warning(f"更新inpainted图片失败: {e}")

    def persist_editor_state_for_export(
        self,
        export_service,
        source_path: str,
        regions: list,
        mask: Optional[np.ndarray],
        config_dict: dict,
        inpainted_image: Optional[object] = None,
    ) -> str:
        json_path = self.resolve_editor_json_path(source_path)
        json_regions = [dict(region) for region in regions]
        for region in json_regions:
            self.apply_white_frame_center(region)
        export_service._save_regions_data_with_path(json_regions, json_path, source_path, mask, config_dict)
        self.save_current_inpainted_image(
            source_path,
            config_dict,
            mask,
            current_inpainted_image=inpainted_image,
            has_regions=bool(regions),
        )
        return json_path

    def _build_output_path(self, config, source_path: Optional[str]) -> str:
        save_to_source_dir = getattr(config.cli, "save_to_source_dir", False) if hasattr(config, "cli") else False
        if save_to_source_dir and source_path:
            output_dir = os.path.join(os.path.dirname(source_path), "manga_translator_work", "result")
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = getattr(config.app, "last_output_path", None) if hasattr(config, "app") else None
            if not output_dir or not os.path.exists(output_dir):
                output_dir = os.path.dirname(source_path) if source_path else os.getcwd()

        if source_path:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_format = getattr(config.cli, "format", "") if hasattr(config, "cli") else ""
            if output_format == "不指定":
                output_format = None
            if output_format and output_format.strip():
                output_filename = f"{base_name}.{output_format.lower()}"
            else:
                original_ext = os.path.splitext(source_path)[1].lower()
                output_filename = f"{base_name}{original_ext}" if original_ext else f"{base_name}.png"
        else:
            output_filename = f"exported_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        return os.path.join(output_dir, output_filename)

    @staticmethod
    def _build_config_dict(config) -> dict:
        if hasattr(config, "model_dump"):
            return config.model_dump()
        if hasattr(config, "dict"):
            return config.dict()
        return {}

    @staticmethod
    def _prepare_render_config(config_dict: dict) -> None:
        render_config = config_dict.setdefault("render", {})
        render_config["disable_auto_wrap"] = True

    def _build_enhanced_regions(self, regions: list[dict]) -> list[dict]:
        render_service = get_render_parameter_service()
        enhanced_regions = []
        for index, region in enumerate(regions):
            enhanced_region = region.copy()
            if not enhanced_region.get("translation"):
                enhanced_region["translation"] = enhanced_region.get("text", "")
            if not enhanced_region.get("font_size"):
                enhanced_region["font_size"] = 16
            if not enhanced_region.get("alignment"):
                enhanced_region["alignment"] = "center"
            if not enhanced_region.get("direction"):
                enhanced_region["direction"] = "auto"

            self.apply_white_frame_center(enhanced_region)
            enhanced_region.update(render_service.export_parameters_for_backend(index, enhanced_region))
            enhanced_regions.append(enhanced_region)
        return enhanced_regions

    async def async_export_with_desktop_ui_service(
        self,
        image,
        regions,
        mask,
        source_path: Optional[str] = None,
        inpainted_image=None,
    ):
        outcome = {
            "success": False,
            "error": None,
            "output_path": None,
            "json_path": None,
        }
        try:
            from services.export_service import ExportService

            config = self.config_service.get_config()
            output_path = self._build_output_path(config, source_path)
            outcome["output_path"] = output_path
            export_service = ExportService()
            config_dict = self._build_config_dict(config)
            self._prepare_render_config(config_dict)

            persisted_json_path = None
            if source_path:
                persisted_json_path = self.persist_editor_state_for_export(
                    export_service=export_service,
                    source_path=source_path,
                    regions=regions,
                    mask=mask,
                    config_dict=config_dict,
                    inpainted_image=inpainted_image,
                )
                outcome["json_path"] = persisted_json_path
            else:
                self.logger.warning("Exporting without source image path, skipped JSON persistence")

            def progress_callback(_message):
                return None

            def success_callback(_message):
                outcome["success"] = True
                success_message = f"导出成功\n{output_path}"
                if persisted_json_path:
                    success_message += "\n已同步 JSON"
                self.controller._show_toast_signal.emit(success_message, 5000, True, output_path)

                if self.controller._is_same_source_image(self.model.get_source_image_path(), source_path):
                    self.save_export_snapshot()
                    self.resource_manager.release_memory_after_export()
                    self.resource_manager.release_image_cache_except_current()
                    self.controller._log_memory_snapshot("after-export-cleanup")
                else:
                    self.logger.debug("Skipped export snapshot update because active image changed during export")

            def error_callback(message):
                outcome["error"] = str(message)
                self.logger.error(f"Export error: {message}")
                self.controller._show_toast_signal.emit(f"导出失败：{message}", 5000, False, "")

            enhanced_regions = self._build_enhanced_regions(regions)
            await asyncio.to_thread(
                export_service._perform_backend_render_export,
                image,
                enhanced_regions,
                config_dict,
                output_path,
                mask,
                progress_callback,
                success_callback,
                error_callback,
                source_path,
                False,
                inpainted_image,
            )
            if not outcome["success"] and outcome["error"] is None:
                outcome["error"] = "导出未返回成功状态"
            return outcome
        except Exception as e:
            self.logger.error(f"Error during async export: {e}", exc_info=True)
            err_msg = str(e)
            outcome["error"] = err_msg
            QTimer.singleShot(
                0,
                lambda: QMessageBox.critical(None, "导出失败", f"导出过程中发生意外错误:\n{err_msg}"),
            )
            return outcome
