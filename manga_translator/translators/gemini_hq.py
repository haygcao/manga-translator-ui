import os
import re
import asyncio
import base64
import json
from io import BytesIO
from typing import List, Dict, Any
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .common import CommonTranslator, VALID_LANGUAGES
from .keys import GEMINI_API_KEY
from ..utils import Context


def encode_image_for_gemini(image, max_size=1024):
    """将图片处理为适合Gemini API的格式"""
    # 转换图片格式
    if image.mode == "P":
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    elif image.mode == "RGBA":
        # Gemini更喜欢RGB格式
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    
    # 调整图片大小
    w, h = image.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.LANCZOS)
    
    return image


class GeminiHighQualityTranslator(CommonTranslator):
    """
    Gemini高质量翻译器
    支持多图片批量处理，提供文本框顺序、原文和原图给AI进行更精准的翻译
    """
    _LANGUAGE_CODE_MAP = VALID_LANGUAGES
    
    def __init__(self):
        super().__init__()
        self.client = None
        # Initial setup from environment variables
        self.api_key = os.getenv('GEMINI_API_KEY', GEMINI_API_KEY)
        self.base_url = os.getenv('GEMINI_API_BASE', 'https://generativelanguage.googleapis.com')
        self.model_name = os.getenv('GEMINI_MODEL', "gemini-1.5-flash")
        self.max_tokens = 4000
        self.temperature = 0.1
        self.safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]
        self._setup_client()
        
    def _setup_client(self):
        """设置Gemini客户端"""
        if not self.client and self.api_key:
            client_options = {"api_endpoint": self.base_url} if self.base_url else None

            genai.configure(
                api_key=self.api_key,
                transport='rest',  # 支持自定义base_url
                client_options=client_options
            )
            
            generation_config = {
                "temperature": self.temperature,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": self.max_tokens,
                "response_mime_type": "text/plain",
            }

            model_args = {
                "model_name": self.model_name,
                "generation_config": generation_config,
            }

            # Conditionally add safety settings
            is_third_party_api = self.base_url and self.base_url != 'https://generativelanguage.googleapis.com'
            if not is_third_party_api:
                model_args["safety_settings"] = self.safety_settings
            else:
                self.logger.info("检测到第三方API，已禁用安全设置。")

            self.client = genai.GenerativeModel(**model_args)
    
    def parse_args(self, config):
        """解析配置参数，使用和原有Gemini翻译器相同的环境变量"""
        # 从UI配置覆盖环境变量
        ui_api_key = getattr(config, 'GEMINI_API_KEY', None) or getattr(config, 'api_key', None)
        if ui_api_key:
            self.api_key = ui_api_key

        ui_base_url = getattr(config, 'api_base', None)
        if ui_base_url:
            self.base_url = ui_base_url
        
        self.model_name = getattr(config, 'model', self.model_name)
        
        # 设置翻译参数
        self.max_tokens = getattr(config, 'max_tokens', self.max_tokens)
        self.temperature = getattr(config, 'temperature', self.temperature)
        
        # 使用新配置重新设置客户端
        self.client = None  # 强制重新初始化
        self._setup_client()
        
        # 调用父类解析
        super().parse_args(config)
    
    def _build_system_prompt(self, source_lang: str, target_lang: str, custom_prompt_json: Dict[str, Any] = None) -> str:
        """构建系统提示词"""
        custom_prompts = []
        if custom_prompt_json:
            for key, value in custom_prompt_json.items():
                if isinstance(value, str):
                    custom_prompts.append(value)
        
        custom_prompt_str = "\n\n".join(custom_prompts)

        base_prompt = f"""You are an expert manga translator. Your task is to accurately translate manga text from the source language into **{{{target_lang}}}**. You will be given the full manga page for context.

**CRITICAL INSTRUCTIONS (FOLLOW STRICTLY):**

1.  **DIRECT TRANSLATION ONLY**: Your output MUST contain ONLY the raw, translated text. Nothing else.
    -   DO NOT include the original text.
    -   DO NOT include any explanations, greetings, apologies, or any conversational text.
    -   DO NOT use Markdown formatting (like ```json or ```).
    -   The output is fed directly to an automated script. Any extra text will cause it to fail.

2.  **MATCH LINE COUNT**: The number of lines in your output MUST EXACTLY match the number of text regions you are asked to translate. Each line in your output corresponds to one numbered text region in the input.

3.  **TRANSLATE EVERYTHING**: Translate all text provided, including sound effects and single characters. Do not leave any line untranslated.

4.  **ACCURACY AND TONE**:
    -   Preserve the original tone, emotion, and character's voice.
    -   Ensure consistent translation of names, places, and special terms.
    -   For onomatopoeia (sound effects), provide the equivalent sound in {{{target_lang}}} or a brief description (e.g., '(rumble)', '(thud)').

---

**EXAMPLE OF CORRECT AND INCORRECT OUTPUT:**

**[ CORRECT OUTPUT EXAMPLE ]**
This is a correct response. Notice it only contains the translated text, with each translation on a new line.

(Imagine the user input was: "1. うるさい！", "2. 黙れ！")
```
吵死了！
闭嘴！
```

**[ ❌ INCORRECT OUTPUT EXAMPLE ]**
This is an incorrect response because it includes extra text and explanations.

(Imagine the user input was: "1. うるさい！", "2. 黙れ！")
```
好的，这是您的翻译：
1. 吵死了！
2. 闭嘴！
```
**REASONING:** The above example is WRONG because it includes "好的，这是您的翻译：" and numbering. Your response must be ONLY the translated text, line by line.

---

**FINAL INSTRUCTION:** Now, perform the translation task. Remember, your response must be clean, containing only the translated text.
"""

        if custom_prompt_str:
            return f"{custom_prompt_str}\n\n---\n\n{base_prompt}"
        else:
            return base_prompt

    def _build_user_prompt(self, batch_data: List[Dict], texts: List[str]) -> str:
        """构建用户提示词"""
        prompt = "Please translate the following manga text regions. I'm providing multiple images with their text regions in reading order:\n\n"
        
        # 添加图片信息
        for i, data in enumerate(batch_data):
            prompt += f"=== Image {i+1} ===\n"
            prompt += f"Text regions ({len(data['original_texts'])} regions):\n"
            for j, text in enumerate(data['original_texts']):
                prompt += f"  {j+1}. {text}\n"
            prompt += "\n"
        
        prompt += "All texts to translate (in order):\n"
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        prompt += "\nPlease provide translations in the same order:"
        
        return prompt

    async def _translate_batch_high_quality(self, texts: List[str], batch_data: List[Dict], source_lang: str, target_lang: str, custom_prompt_json: Dict[str, Any] = None) -> List[str]:
        """高质量批量翻译方法"""
        if not texts:
            return []
        
        if not self.client:
            self._setup_client()
        
        if not self.client:
            self.logger.error("Gemini客户端初始化失败")
            return texts
        
        # 准备图片和内容
        content_parts = []
        
        # 打印输入的原文
        self.logger.info("--- Original Texts for Translation ---")
        for i, text in enumerate(texts):
            self.logger.info(f"{i+1}: {text}")
        self.logger.info("------------------------------------")

        # 打印图片信息
        self.logger.info("--- Image Info ---")
        for i, data in enumerate(batch_data):
            image = data['image']
            self.logger.info(f"Image {i+1}: size={image.size}, mode={image.mode}")
        self.logger.info("--------------------")

        # 添加系统提示词和用户提示词
        system_prompt = self._build_system_prompt(source_lang, target_lang, custom_prompt_json=custom_prompt_json)
        user_prompt = self._build_user_prompt(batch_data, texts)
        
        content_parts.append(system_prompt + "\n\n" + user_prompt)
        
        # 添加图片
        for data in batch_data:
            image = data['image']
            processed_image = encode_image_for_gemini(image)
            content_parts.append(processed_image)
        
        # 发送请求
        max_retries = self.attempts
        attempt = 0
        is_infinite = max_retries == -1

        while is_infinite or attempt < max_retries:
            try:
                response = await asyncio.to_thread(
                    self.client.generate_content,
                    content_parts
                )
                
                # 尝试访问 .text 属性，如果API因安全原因等返回空内容，这里会触发异常
                result_text = response.text.strip()
                
                # 如果成功获取文本，则处理并返回
                translations = []
                for line in result_text.split('\n'):
                    line = line.strip()
                    if line:
                        # 移除编号（如"1. "）
                        line = re.sub(r'^\d+\.\s*', '', line)
                        translations.append(line)
                
                # 确保翻译数量匹配
                while len(translations) < len(texts):
                    translations.append(texts[len(translations)] if len(translations) < len(texts) else "")
                
                # 打印原文和译文的对应关系
                self.logger.info("--- Translation Results ---")
                for original, translated in zip(texts, translations):
                    self.logger.info(f'{original} -> {translated}')
                self.logger.info("---------------------------")

                return translations[:len(texts)]

            except Exception as e:
                attempt += 1
                log_attempt = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                self.logger.warning(f"Gemini高质量翻译出错 ({log_attempt}): {e}")

                if "finish_reason: 2" in str(e) or "finish_reason is 2" in str(e):
                    self.logger.warning("检测到Gemini安全设置拦截。正在重试...")
                
                if not is_infinite and attempt >= max_retries:
                    self.logger.error("Gemini翻译在多次重试后仍然失败。即将终止程序。")
                    raise e
                
                await asyncio.sleep(1) # Wait before retrying
        
        return texts # Fallback in case loop finishes unexpectedly

    async def _translate(self, from_lang: str, to_lang: str, queries: List[str], ctx=None) -> List[str]:
        """主翻译方法"""
        if not self.client:
            from .. import manga_translator
            if hasattr(manga_translator, 'config') and hasattr(manga_translator.config, 'translator'):
                self.parse_args(manga_translator.config.translator)
        
        if not queries:
            return []
        
        # 检查是否为高质量批量翻译模式
        if ctx and hasattr(ctx, 'high_quality_batch_data'):
            batch_data = ctx.high_quality_batch_data
            if batch_data and len(batch_data) > 0:
                self.logger.info(f"高质量翻译模式：正在打包 {len(batch_data)} 张图片并发送...")
                custom_prompt_json = getattr(ctx, 'custom_prompt_json', None)
                return await self._translate_batch_high_quality(queries, batch_data, from_lang, to_lang, custom_prompt_json=custom_prompt_json)
        
        # 普通单文本翻译（后备方案）
        if not self.client:
            self._setup_client()
        
        if not self.client:
            self.logger.error("Gemini客户端初始化失败，请检查 GEMINI_API_KEY 是否已在UI或.env文件中正确设置。")
            return queries
        
        try:
            simple_prompt = f"Translate the following {from_lang} text to {to_lang}. Provide only the translation:\n\n" + "\n".join(queries)
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                simple_prompt
            )
            
            if response and response.text:
                result = response.text.strip()
                translations = result.split('\n')
                translations = [t.strip() for t in translations if t.strip()]
                
                # 确保数量匹配
                while len(translations) < len(queries):
                    translations.append(queries[len(translations)] if len(translations) < len(queries) else "")
                
                return translations[:len(queries)]
                
        except Exception as e:
            self.logger.error(f"Gemini翻译出错: {e}")
        
        return queries
