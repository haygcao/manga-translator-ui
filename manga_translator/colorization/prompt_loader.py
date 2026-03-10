import os
from typing import Optional

from ..utils import BASE_PATH
from ..translators.prompt_loader import load_prompt_file

DEFAULT_AI_COLORIZER_PROMPT = (
    "You are a manga colorization engine. Colorize the provided manga page while preserving "
    "the original composition, character identities, panel structure, line art, shading, and "
    "readability of all existing details. Keep the page content unchanged except for adding "
    "natural, coherent color. Return only the final colorized image."
)

DEFAULT_AI_COLORIZER_PROMPT_PATH = os.path.join("dict", "ai_colorizer_prompt.yaml").replace("\\", "/")
AI_COLORIZER_PROMPT_KEYS = ("ai_colorizer_prompt", "colorizer_prompt", "prompt")


def resolve_ai_colorizer_prompt_path(path: Optional[str]) -> str:
    rel_path = (path or DEFAULT_AI_COLORIZER_PROMPT_PATH).replace("\\", "/")
    if os.path.isabs(rel_path):
        return os.path.normpath(rel_path)
    return os.path.normpath(os.path.join(BASE_PATH, rel_path))


def load_ai_colorizer_prompt_file(path: Optional[str]) -> str:
    resolved_path = resolve_ai_colorizer_prompt_path(path)
    if not os.path.exists(resolved_path):
        return ""

    data = load_prompt_file(resolved_path)
    if not isinstance(data, dict):
        return ""

    for key in AI_COLORIZER_PROMPT_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def save_ai_colorizer_prompt_file(path: Optional[str], prompt_text: str) -> str:
    resolved_path = resolve_ai_colorizer_prompt_path(path)
    os.makedirs(os.path.dirname(resolved_path), exist_ok=True)

    lines = prompt_text.splitlines() or [""]
    content = ["ai_colorizer_prompt: |"]
    content.extend(f"  {line}" if line else "  " for line in lines)
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content) + "\n")
    return resolved_path


def ensure_ai_colorizer_prompt_file(path: Optional[str] = None) -> str:
    resolved_path = resolve_ai_colorizer_prompt_path(path)
    if not os.path.exists(resolved_path):
        save_ai_colorizer_prompt_file(resolved_path, DEFAULT_AI_COLORIZER_PROMPT)
    return resolved_path
