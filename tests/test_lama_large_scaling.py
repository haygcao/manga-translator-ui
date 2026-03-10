import ast
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "manga_translator" / "inpainting" / "inpainting_lama_mpe.py"
SOURCE_TEXT = SOURCE_PATH.read_text(encoding="utf-8")
SOURCE_AST = ast.parse(SOURCE_TEXT)


def _get_lama_large_class() -> ast.ClassDef:
    for node in SOURCE_AST.body:
        if isinstance(node, ast.ClassDef) and node.name == "LamaLargeInpainter":
            return node
    raise AssertionError("LamaLargeInpainter not found")


def _get_method_source(method_name: str) -> str:
    class_node = _get_lama_large_class()
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            method_source = ast.get_source_segment(SOURCE_TEXT, node)
            if method_source is None:
                raise AssertionError(f"Unable to read source for {method_name}")
            return method_source
    raise AssertionError(f"{method_name} not found")


def test_lama_large_has_shared_scaling_helpers():
    class_node = _get_lama_large_class()
    method_names = {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_prepare_large_image" in method_names
    assert "_restore_large_output" in method_names
    assert "_infer_torch_large" in method_names


def test_lama_large_torch_path_uses_large_scaling_flow():
    infer_source = _get_method_source("_infer")

    assert "return await self._infer_torch_large" in infer_source
    assert "return await super()._infer" not in infer_source


def test_lama_large_onnx_and_torch_share_prepare_restore_flow():
    onnx_source = _get_method_source("_infer_onnx")
    torch_source = _get_method_source("_infer_torch_large")

    assert "_prepare_large_image" in onnx_source
    assert "_restore_large_output" in onnx_source
    assert "_prepare_large_image" in torch_source
    assert "_restore_large_output" in torch_source


def test_lama_large_onnx_load_disables_ort_cpu_allocators():
    load_source = _get_method_source("_load")

    assert "enable_mem_pattern=False" in load_source
    assert "enable_cpu_mem_arena=False" in load_source
