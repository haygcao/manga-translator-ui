import asyncio
import base64
import io
import os
from typing import Optional

import numpy as np
from PIL import Image

from .common import CommonColorizer
from .prompt_loader import (
    DEFAULT_AI_COLORIZER_PROMPT,
    ensure_ai_colorizer_prompt_file,
    load_ai_colorizer_prompt_file,
)
from ..utils.ai_image_preprocess import normalize_ai_image, prepare_square_ai_image, restore_square_ai_image
from ..utils.openai_image_interface import request_openai_image_with_fallback
from ..utils import get_logger


OPENAI_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

GEMINI_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
    "Origin": "https://aistudio.google.com",
    "Referer": "https://aistudio.google.com/",
}

_COLORIZER_SEMAPHORES: dict[str, tuple[int, asyncio.Semaphore]] = {}
_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def _get_colorizer_semaphore(name: str, concurrency: int) -> asyncio.Semaphore:
    current = _COLORIZER_SEMAPHORES.get(name)
    if current is None or current[0] != concurrency:
        current = (concurrency, asyncio.Semaphore(concurrency))
        _COLORIZER_SEMAPHORES[name] = current
    return current[1]


class BaseAPIColorizer(CommonColorizer):
    API_KEY_ENV = ""
    API_BASE_ENV = ""
    MODEL_ENV = ""
    FALLBACK_API_KEY_ENV = ""
    FALLBACK_API_BASE_ENV = ""
    FALLBACK_MODEL_ENV = ""
    DEFAULT_API_BASE = ""
    DEFAULT_MODEL = ""
    BROWSER_HEADERS = {}
    PROVIDER_NAME = "API Colorizer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger("colorizer")
        self.client = None
        self.api_key = None
        self.base_url = None
        self.model_name = None
        self._client_signature = None
        self._client_loop = None

        is_web_server = os.getenv("MANGA_TRANSLATOR_WEB_SERVER", "false").lower() == "true"
        if not is_web_server:
            try:
                from dotenv import load_dotenv

                load_dotenv(override=True)
            except Exception:
                pass

    def _read_runtime_config(self):
        try:
            from dotenv import load_dotenv

            load_dotenv(override=True)
        except Exception:
            pass

        api_key = os.getenv(self.API_KEY_ENV) or os.getenv(self.FALLBACK_API_KEY_ENV)
        base_url = (
            os.getenv(self.API_BASE_ENV)
            or os.getenv(self.FALLBACK_API_BASE_ENV)
            or self.DEFAULT_API_BASE
        )
        model_name = (
            os.getenv(self.MODEL_ENV)
            or os.getenv(self.FALLBACK_MODEL_ENV)
            or self.DEFAULT_MODEL
        )
        return api_key, base_url.rstrip("/"), model_name

    async def _ensure_client(self):
        current_loop = asyncio.get_running_loop()
        api_key, base_url, model_name = self._read_runtime_config()
        signature = (api_key or "", base_url, model_name)
        if (
            self.client is not None
            and signature == self._client_signature
            and self._client_loop is current_loop
        ):
            return

        if self.client is not None:
            if self._client_loop is current_loop:
                try:
                    await self.client.close()
                except Exception:
                    pass
            else:
                self.logger.info(f"{self.PROVIDER_NAME}: recreating API client for a new event loop.")
            self.client = None
            self._client_loop = None

        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self._client_signature = signature

        if api_key:
            self.client = self._create_client(api_key=api_key, base_url=base_url)
            self._client_loop = current_loop

    def _build_colorizer_prompt(self) -> str:
        ensure_ai_colorizer_prompt_file()
        return load_ai_colorizer_prompt_file(None) or DEFAULT_AI_COLORIZER_PROMPT

    def _resolve_concurrency(self, kwargs) -> int:
        config = kwargs.get("config")
        colorizer_config = getattr(config, "colorizer", None) if config is not None else None
        try:
            return max(int(getattr(colorizer_config, "ai_colorizer_concurrency", 1) or 1), 1)
        except (TypeError, ValueError):
            return 1

    def _to_rgb_image(self, image) -> Image.Image:
        if not isinstance(image, Image.Image):
            image = Image.fromarray(np.asarray(image).astype(np.uint8))
        return normalize_ai_image(image)

    def _image_to_png_bytes(self, image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        self._to_rgb_image(image).save(buffer, format="PNG")
        return buffer.getvalue()

    async def _fetch_image_from_url(self, url: str) -> Image.Image:
        response = await self.client.session.get(url, timeout=600.0)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download generated image: HTTP {response.status_code}")
        return Image.open(io.BytesIO(response.content)).convert("RGB")

    def _load_image_from_bytes(self, payload: bytes) -> Image.Image:
        return Image.open(io.BytesIO(payload)).convert("RGB")

    def _extract_gemini_image(self, response) -> Optional[Image.Image]:
        raw = getattr(response, "raw", None) or {}
        for candidate in raw.get("candidates") or []:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                inline_data = part.get("inlineData") or part.get("inline_data")
                if not isinstance(inline_data, dict):
                    continue
                data = inline_data.get("data")
                if not data:
                    continue
                return self._load_image_from_bytes(base64.b64decode(data))
        return None

    async def _colorize(self, image: Image.Image, colorization_size: int, **kwargs) -> Image.Image:
        del colorization_size
        await self._ensure_client()
        if not self.client or not self.api_key:
            raise RuntimeError(
                f"{self.PROVIDER_NAME} is not configured. Set {self.API_KEY_ENV} in .env "
                f"(or fallback {self.FALLBACK_API_KEY_ENV})."
            )

        image = self._to_rgb_image(image)
        original_size = image.size
        request_image, restore_info = prepare_square_ai_image(image)
        prompt_text = self._build_colorizer_prompt()
        semaphore = _get_colorizer_semaphore(self.PROVIDER_NAME, self._resolve_concurrency(kwargs))

        async with semaphore:
            result_image = await self._request_colorized_image(image=request_image, prompt_text=prompt_text)

        result_image = restore_square_ai_image(self._to_rgb_image(result_image), restore_info)
        if result_image.size != original_size:
            result_image = result_image.resize(original_size, _LANCZOS)
        return result_image

    def _create_client(self, api_key: str, base_url: str):
        raise NotImplementedError

    async def _request_colorized_image(self, image: Image.Image, prompt_text: str) -> Image.Image:
        raise NotImplementedError


class OpenAIColorizer(BaseAPIColorizer):
    API_KEY_ENV = "COLOR_OPENAI_API_KEY"
    API_BASE_ENV = "COLOR_OPENAI_API_BASE"
    MODEL_ENV = "COLOR_OPENAI_MODEL"
    FALLBACK_API_KEY_ENV = "OPENAI_API_KEY"
    FALLBACK_API_BASE_ENV = "OPENAI_API_BASE"
    FALLBACK_MODEL_ENV = "OPENAI_MODEL"
    DEFAULT_API_BASE = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-image-1"
    BROWSER_HEADERS = OPENAI_BROWSER_HEADERS
    PROVIDER_NAME = "OpenAI Colorizer"

    def _create_client(self, api_key: str, base_url: str):
        from ..translators.common import AsyncOpenAICurlCffi

        return AsyncOpenAICurlCffi(
            api_key=api_key,
            base_url=base_url,
            default_headers=self.BROWSER_HEADERS,
            impersonate="chrome110",
            timeout=600.0,
            stream_timeout=300.0,
        )

    async def _request_colorized_image(self, image: Image.Image, prompt_text: str) -> Image.Image:
        return await request_openai_image_with_fallback(
            session=self.client.session,
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=self.BROWSER_HEADERS,
            model_name=self.model_name,
            prompt_text=prompt_text,
            image_bytes=self._image_to_png_bytes(image),
            filename="page.png",
            timeout=600.0,
            fetch_remote_image=self._fetch_image_from_url,
            provider_name=self.PROVIDER_NAME,
            logger=self.logger,
        )


class GeminiColorizer(BaseAPIColorizer):
    API_KEY_ENV = "COLOR_GEMINI_API_KEY"
    API_BASE_ENV = "COLOR_GEMINI_API_BASE"
    MODEL_ENV = "COLOR_GEMINI_MODEL"
    FALLBACK_API_KEY_ENV = "GEMINI_API_KEY"
    FALLBACK_API_BASE_ENV = "GEMINI_API_BASE"
    FALLBACK_MODEL_ENV = "GEMINI_MODEL"
    DEFAULT_API_BASE = "https://generativelanguage.googleapis.com"
    DEFAULT_MODEL = "gemini-2.0-flash-preview-image-generation"
    BROWSER_HEADERS = GEMINI_BROWSER_HEADERS
    PROVIDER_NAME = "Gemini Colorizer"
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
    ]

    def _create_client(self, api_key: str, base_url: str):
        from ..translators.common import AsyncGeminiCurlCffi

        return AsyncGeminiCurlCffi(
            api_key=api_key,
            base_url=base_url,
            default_headers=self.BROWSER_HEADERS,
            impersonate="chrome110",
            timeout=600.0,
            stream_timeout=300.0,
        )

    async def _request_colorized_image(self, image: Image.Image, prompt_text: str) -> Image.Image:
        image_b64 = base64.b64encode(self._image_to_png_bytes(image)).decode("ascii")
        response = await self.client.models.generate_content(
            model=self.model_name,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": image_b64,
                            }
                        },
                    ],
                }
            ],
            generationConfig={
                "temperature": 0.2,
                "maxOutputTokens": 8192,
                "responseModalities": ["TEXT", "IMAGE"],
            },
            safetySettings=self.SAFETY_SETTINGS,
        )
        image_result = self._extract_gemini_image(response)
        if image_result is None:
            raise RuntimeError("Gemini colorization response did not contain an image.")
        return image_result
