import ast
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "manga_translator" / "inpainting" / "__init__.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
SOURCE_AST = ast.parse(SOURCE_TEXT)


def _get_function_source(function_name: str) -> str:
    for node in SOURCE_AST.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            function_source = ast.get_source_segment(SOURCE_TEXT, node)
            if function_source is None:
                raise AssertionError(f"Unable to read source for {function_name}")
            return function_source
    raise AssertionError(f"{function_name} not found")


def test_inpainting_split_ratio_is_fixed_to_three():
    assert "INPAINT_SPLIT_RATIO = 3.0" in SOURCE_TEXT
    assert "config.inpainting_split_ratio" not in SOURCE_TEXT


def test_dispatch_uses_split_strategy_not_detector_rearrange():
    dispatch_source = _get_function_source("dispatch")

    assert "_dispatch_with_split" in dispatch_source
    assert "build_det_rearrange_plan" not in dispatch_source
    assert "_dispatch_with_det_rearrange" not in dispatch_source


def test_split_helper_exists_and_logs_split_flow():
    split_source = _get_function_source("_dispatch_with_split")

    assert "num_splits" in split_source
    assert "overlap" in split_source
    assert "[Inpainting Split]" in split_source
