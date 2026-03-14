import importlib.util
from pathlib import Path


def _load_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "manga_translator"
        / "utils"
        / "region_json_compat.py"
    )
    spec = importlib.util.spec_from_file_location("region_json_compat", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


repair_legacy_white_frame_center = _load_module().repair_legacy_white_frame_center


def test_repair_legacy_white_frame_center_restores_source_center():
    region = {
        "lines": [
            [[80.0, 90.0], [120.0, 90.0], [120.0, 110.0], [80.0, 110.0]],
        ],
        "center": [140.0, 110.0],
        "angle": 0.0,
        "white_frame_rect_local": [20.0, -10.0, 60.0, 30.0],
        "has_custom_white_frame": True,
    }

    assert repair_legacy_white_frame_center(region) is True
    assert region["center"] == [100.0, 100.0]


def test_repair_legacy_white_frame_center_keeps_valid_region_untouched():
    region = {
        "lines": [
            [[80.0, 90.0], [120.0, 90.0], [120.0, 110.0], [80.0, 110.0]],
        ],
        "center": [100.0, 100.0],
        "angle": 0.0,
        "white_frame_rect_local": [20.0, -10.0, 60.0, 30.0],
        "has_custom_white_frame": True,
    }

    assert repair_legacy_white_frame_center(region) is False
    assert region["center"] == [100.0, 100.0]
