from pathlib import Path


TRANSLATOR_SOURCE = (
    Path(__file__).resolve().parents[1] / "manga_translator" / "manga_translator.py"
).read_text(encoding="utf-8")
LAMA_SOURCE = (
    Path(__file__).resolve().parents[1] / "manga_translator" / "inpainting" / "inpainting_lama_mpe.py"
).read_text(encoding="utf-8")


def test_progress_logger_includes_inpainting_state():
    assert "'inpainting': 'Running inpainting'" in TRANSLATOR_SOURCE


def test_run_inpainting_emits_info_log():
    assert 'logger.info(\n            f"[修复] inpainter=' in TRANSLATOR_SOURCE


def test_lama_inpainting_resolution_logs_use_info_level():
    assert "self.logger.info(f'Inpainting resolution: {new_w}x{new_h}')" in LAMA_SOURCE
    assert "self.logger.debug(f'Inpainting resolution: {new_w}x{new_h}')" not in LAMA_SOURCE
