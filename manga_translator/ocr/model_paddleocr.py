# Copyright (c) 2025 PaddlePaddle Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""
PP-OCRv5 ONNX Adapter for Manga Translator

Uses PP-OCRv5 recognition models via ONNX Runtime (no PaddlePaddle dependency).
Text detection is handled by manga-translator's own detection modules.

Supports:
- Chinese/Japanese/English (ch_PP-OCRv5_rec_server_infer)
- Korean/English (korean_PP-OCRv5_rec_mobile_infer)
"""

import os
import numpy as np
from typing import List
import cv2
import math
import torch
import einops

from .common import OfflineOCR
from ..config import OcrConfig
from ..utils import Quadrilateral


class ModelPaddleOCR(OfflineOCR):
    """
    PP-OCRv5 ONNX text recognition for manga-image-translator.

    Supports Chinese, Japanese, Korean, and English text recognition.
    """

    # Use BASE_PATH for consistency with other models and PyInstaller compatibility
    # _MODEL_DIR and _MODEL_SUB_DIR are inherited from ModelWrapper and OfflineOCR
    # Final path: BASE_PATH/models/ocr

    # Model mapping for unified model management
    _MODEL_MAPPING = {
        'ch_onnx': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.1/ch_PP-OCRv5_rec_server_infer.onnx',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ch_PP-OCRv5_rec_server_infer.onnx',
            ],
            'hash': 'e09385400eaaaef34ceff54aeb7c4f0f1fe014c27fa8b9905d4709b65746562a',
            'file': '.',
        },
        'ch_dict': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.1/ppocrv5_dict.txt',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ppocrv5_dict.txt',
            ],
            'hash': 'd1979e9f794c464c0d2e0b70a7fe14dd978e9dc644c0e71f14158cdf8342af1b',
            'file': '.',
        },
        'korean_onnx': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.1/korean_PP-OCRv5_rec_mobile_infer.onnx',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/korean_PP-OCRv5_rec_mobile_infer.onnx',
            ],
            'hash': 'cd6e2ea50f6943ca7271eb8c56a877a5a90720b7047fe9c41a2e541a25773c9b',
            'file': '.',
        },
        'korean_dict': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.1/ppocrv5_korean_dict.txt',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ppocrv5_korean_dict.txt',
            ],
            'hash': 'a88071c68c01707489baa79ebe0405b7beb5cca229f4fc94cc3ef992328802d7',
            'file': '.',
        },
        'latin_onnx': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.8.0/latin_PP-OCRv5_rec_mobile_infer.onnx',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/latin_PP-OCRv5_rec_mobile_infer.onnx',
            ],
            'hash': '614ffc2d6d3902d360fad7f1b0dd455ee45e877069d14c4e51a99dc4ef144409',
            'file': '.',
        },
        'latin_dict': {
            'url': [
                'https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.8.0/ppocrv5_latin_dict.txt',
                'https://www.modelscope.cn/models/hgmzhn/manga-translator-ui/resolve/master/ppocrv5_latin_dict.txt',
            ],
            'hash': '3c0a8a79b612653c25f765271714f71281e4e955962c153e272b7b8c1d2b13ff',
            'file': '.',
        }
    }

    _MODELS = {
        'ch': {  # Chinese/Japanese/English
            'onnx': 'ch_PP-OCRv5_rec_server_infer.onnx',
            'dict': 'ppocrv5_dict.txt',
        },
        'korean': {  # Korean/English
            'onnx': 'korean_PP-OCRv5_rec_mobile_infer.onnx',
            'dict': 'ppocrv5_korean_dict.txt',
        },
        'latin': {  # Latin alphabet languages (English, Spanish, etc.)
            'onnx': 'latin_PP-OCRv5_rec_mobile_infer.onnx',
            'dict': 'ppocrv5_latin_dict.txt',
        }
    }

    def __init__(self, model_type='ch', *args, **kwargs):
        """
        Args:
            model_type: 'ch' for Chinese/Japanese/English, 'korean' for Korean/English, 'latin' for Latin/English
        """
        super().__init__(*args, **kwargs)
        self.model_type = model_type
        self.session = None
        self.char_dict = None
        self.device = 'cpu'
        self.color_model = None  # 48px 模型用于颜色预测
        self.use_gpu = False  # 初始化 use_gpu 标志

    async def _load(self, device: str):
        """Load PP-OCRv5 ONNX model and 48px color prediction model"""
        import onnxruntime as ort
        from .model_48px import OCR

        self.device = device
        model_config = self._MODELS[self.model_type]

        # Load model using inherited model_dir property (PyInstaller-compatible)
        model_path = self._get_file_path(model_config['onnx'])
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Load dictionary
        dict_path = self._get_file_path(model_config['dict'])
        if not os.path.exists(dict_path):
            raise FileNotFoundError(f"Dictionary not found: {dict_path}")

        with open(dict_path, 'r', encoding='utf-8') as f:
            self.char_dict = ['<blank>'] + [line.strip() for line in f]

        # Create ONNX session
        providers = ['CPUExecutionProvider']
        if device == 'cuda':
            providers.insert(0, 'CUDAExecutionProvider')

        self.session = ort.InferenceSession(model_path, providers=providers)

        # 加载 48px 模型用于颜色预测
        try:
            # 获取 48px 模型的路径（在 ocr 目录下）
            model_48px_dir = os.path.dirname(self.model_dir)
            dict_48px_path = os.path.join(model_48px_dir, 'alphabet-all-v7.txt')
            ckpt_48px_path = os.path.join(model_48px_dir, 'ocr_ar_48px.ckpt')
            
            if os.path.exists(dict_48px_path) and os.path.exists(ckpt_48px_path):
                with open(dict_48px_path, 'r', encoding='utf-8') as fp:
                    dictionary_48px = [s[:-1] for s in fp.readlines()]
                
                self.color_model = OCR(dictionary_48px, 768)
                sd = torch.load(ckpt_48px_path, map_location='cpu', weights_only=False)
                
                # Handle PyTorch Lightning checkpoint format
                if 'state_dict' in sd:
                    sd = sd['state_dict']
                
                # Remove 'model.' prefix from keys if present
                cleaned_sd = {}
                for k, v in sd.items():
                    if k.startswith('model.'):
                        cleaned_sd[k[6:]] = v
                    else:
                        cleaned_sd[k] = v
                
                self.color_model.load_state_dict(cleaned_sd)
                self.color_model.eval()
                
                if device == 'cuda' or device == 'mps':
                    self.color_model = self.color_model.to(device)
                    self.use_gpu = True
                else:
                    self.use_gpu = False
                
                self.logger.info(f"48px color prediction model loaded for PaddleOCR")
            else:
                self.logger.warning(f"48px model not found at {dict_48px_path} or {ckpt_48px_path}")
                self.color_model = None
        except Exception as e:
            self.logger.warning(f"Failed to load 48px color model: {e}")
            self.color_model = None

        self.logger.info(f"PP-OCRv5 ONNX loaded: {model_config['onnx']} ({len(self.char_dict)} chars, device={device})")

    async def _unload(self):
        """Unload model"""
        if self.session is not None:
            del self.session
            self.session = None
        self.char_dict = None
        if self.color_model is not None:
            del self.color_model
            self.color_model = None

    async def _infer(self, image: np.ndarray, textlines: List[Quadrilateral],
                     config: OcrConfig, verbose: bool = False) -> List[Quadrilateral]:
        """
        Perform OCR on detected text regions.

        Args:
            image: RGB image
            textlines: Detected text regions
            config: OCR configuration
            verbose: Verbose logging
        """
        if self.session is None:
            self.logger.error("Model not loaded")
            return textlines

        threshold = 0.2 if config.prob is None else config.prob

        # Extract and preprocess regions
        regions = []
        valid_indices = []

        # Prepare debug output directory if verbose
        if verbose:
            ocr_result_dir = os.environ.get('MANGA_OCR_RESULT_DIR', 'result/ocrs/')
            os.makedirs(ocr_result_dir, exist_ok=True)

        for i, textline in enumerate(textlines):
            try:
                pts = textline.pts

                # Use perspective transform to extract rotated text regions
                # This handles tilted text and automatically rotates vertical text
                region = self._get_rotate_crop_image(image, pts)

                if region is None or region.size == 0:
                    continue

                # Convert RGB to BGR
                if len(region.shape) == 3 and region.shape[2] == 3:
                    region_bgr = cv2.cvtColor(region, cv2.COLOR_RGB2BGR)
                else:
                    region_bgr = region

                # Save debug image if verbose
                if verbose:
                    from ..utils import imwrite_unicode
                    img_data = region_bgr.copy()

                    # Limit OCR debug image max size to 200 pixels
                    max_ocr_size = 200
                    height, width = img_data.shape[:2]
                    if max(height, width) > max_ocr_size:
                        scale = max_ocr_size / max(height, width)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        img_data = cv2.resize(img_data, (new_width, new_height), interpolation=cv2.INTER_AREA)

                    # Use high compression for saving
                    compression_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
                    imwrite_unicode(os.path.join(ocr_result_dir, f'{i}.png'), img_data, self.logger, compression_params)

                regions.append(region_bgr)
                valid_indices.append(i)

            except Exception as e:
                self.logger.warning(f"Failed to extract region {i}: {e}")
                continue

        # Batch inference
        if regions:
            try:
                preprocessed = [self._preprocess(r) for r in regions]
                batch = np.concatenate(preprocessed, axis=0)

                # Run inference
                input_name = self.session.get_inputs()[0].name
                outputs = self.session.run(None, {input_name: batch})
                predictions = outputs[0]  # [batch, seq_len, num_classes]

                # Decode predictions
                for idx, pred in zip(valid_indices, predictions):
                    text, confidence = self._decode_ctc(pred)

                    textline = textlines[idx]
                    
                    if confidence < threshold:
                        self.logger.info(f"[FILTERED] prob: {confidence:.3f} < threshold: {threshold} - Text: \"{text}\"")
                        # Keep the textline with empty text for hybrid OCR to retry
                        textline.text = ''  # Empty text for hybrid OCR
                        textline.prob = confidence
                        textline.fg_r = 0
                        textline.fg_g = 0
                        textline.fg_b = 0
                        textline.bg_r = 255
                        textline.bg_g = 255
                        textline.bg_b = 255
                        continue

                    textline.text = text
                    textline.prob = confidence

                    # Estimate colors using 48px model
                    region_idx = valid_indices.index(idx)
                    self._estimate_colors_48px(regions[region_idx], textline)

                    self.logger.info(f'prob: {confidence:.3f} {text} fg: ({textline.fg_r}, {textline.fg_g}, {textline.fg_b}) bg: ({textline.bg_r}, {textline.bg_g}, {textline.bg_b})')

            except Exception as e:
                self.logger.error(f"Inference failed: {e}")

        return textlines

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for PP-OCRv5 recognition.

        Input: BGR image [H, W, 3]
        Output: Normalized tensor [1, 3, 48, W']
        """
        h, w = img.shape[:2]
        imgC, imgH, imgW = 3, 48, 320

        # Resize keeping aspect ratio
        ratio = w / float(h)
        resized_w = int(math.ceil(imgH * ratio))
        if resized_w > imgW:
            resized_w = imgW

        resized_img = cv2.resize(img, (resized_w, imgH))

        # Normalize: (img/255 - 0.5) / 0.5 => range [-1, 1]
        resized_img = resized_img.astype(np.float32)
        resized_img = resized_img.transpose(2, 0, 1)  # HWC -> CHW
        resized_img = resized_img / 255.0
        resized_img = (resized_img - 0.5) / 0.5

        # Pad to fixed width
        padded = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padded[:, :, :resized_w] = resized_img

        return padded[np.newaxis, :]  # Add batch dimension

    def _decode_ctc(self, pred: np.ndarray):
        """
        Decode CTC prediction to text with special character handling.

        Args:
            pred: [seq_len, num_classes]

        Returns:
            (text, confidence)
        """
        # Get most probable character at each time step
        indices = np.argmax(pred, axis=1)
        confidences = np.max(pred, axis=1)

        # Remove blanks and duplicates, handle special characters
        chars = []
        prev_idx = -1

        for idx in indices:
            if idx != 0 and idx != prev_idx:  # 0 is <blank>
                if idx < len(self.char_dict):
                    ch = self.char_dict[idx]
                    
                    # Special character handling (similar to model_48px)
                    if ch == '<S>':      # Start token
                        continue
                    if ch == '</S>':     # End token
                        break
                    if ch == '<SP>':     # Space token
                        ch = ' '
                    
                    chars.append(ch)
            prev_idx = idx

        text = ''.join(chars)
        confidence = float(np.mean(confidences))

        return text, confidence

    def _estimate_colors_48px(self, region: np.ndarray, textline: Quadrilateral):
        """使用 48px 模型预测前景色和背景色"""
        from ..utils.generic import AvgMeter
        
        try:
            # 如果 48px 模型未加载，使用默认颜色
            if self.color_model is None:
                textline.fg_r = textline.fg_g = textline.fg_b = 0
                textline.bg_r = textline.bg_g = textline.bg_b = 255
                return
            
            # 将 BGR 转换为 RGB
            if len(region.shape) == 3 and region.shape[2] == 3:
                region_rgb = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
            else:
                region_rgb = region
            
            # 调整大小到 48px 高度
            text_height = 48
            h, w = region_rgb.shape[:2]
            ratio = w / float(h)
            new_w = int(round(ratio * text_height))
            
            if new_w == 0:
                new_w = 1
            
            region_resized = cv2.resize(region_rgb, (new_w, text_height), interpolation=cv2.INTER_AREA)
            
            # 转换为 tensor
            image_tensor = (torch.from_numpy(region_resized).float() - 127.5) / 127.5
            image_tensor = einops.rearrange(image_tensor, 'H W C -> 1 C H W')
            
            # GPU 加速
            if self.use_gpu:
                image_tensor = image_tensor.to(self.device)
            
            # 使用 48px 模型推理
            with torch.no_grad():
                ret = self.color_model.infer_beam_batch_tensor(image_tensor, [new_w], beams_k=5, max_seq_length=255)
            
            if ret and len(ret) > 0:
                pred_chars_index, prob, fg_pred, bg_pred, fg_ind_pred, bg_ind_pred = ret[0]
                
                # 计算颜色
                has_fg = (fg_ind_pred[:, 1] > fg_ind_pred[:, 0])
                has_bg = (bg_ind_pred[:, 1] > bg_ind_pred[:, 0])
                
                fr = AvgMeter()
                fg = AvgMeter()
                fb = AvgMeter()
                br = AvgMeter()
                bg = AvgMeter()
                bb = AvgMeter()
                
                for chid, c_fg, c_bg, h_fg, h_bg in zip(pred_chars_index, fg_pred, bg_pred, has_fg, has_bg):
                    ch = self.color_model.dictionary[chid]
                    if ch == '<S>':
                        continue
                    if ch == '</S>':
                        break
                    if h_fg.item():
                        fr(int(c_fg[0] * 255))
                        fg(int(c_fg[1] * 255))
                        fb(int(c_fg[2] * 255))
                    if h_bg.item():
                        br(int(c_bg[0] * 255))
                        bg(int(c_bg[1] * 255))
                        bb(int(c_bg[2] * 255))
                    else:
                        br(int(c_fg[0] * 255))
                        bg(int(c_fg[1] * 255))
                        bb(int(c_fg[2] * 255))
                
                textline.fg_r = min(max(int(fr()), 0), 255)
                textline.fg_g = min(max(int(fg()), 0), 255)
                textline.fg_b = min(max(int(fb()), 0), 255)
                textline.bg_r = min(max(int(br()), 0), 255)
                textline.bg_g = min(max(int(bg()), 0), 255)
                textline.bg_b = min(max(int(bb()), 0), 255)
            else:
                # 如果推理失败，设置默认颜色
                textline.fg_r = textline.fg_g = textline.fg_b = 0
                textline.bg_r = textline.bg_g = textline.bg_b = 255
                self.logger.debug("48px color prediction returned no results, using default colors")
                
        except Exception as e:
            # 如果出错，设置默认颜色
            textline.fg_r = textline.fg_g = textline.fg_b = 0
            textline.bg_r = textline.bg_g = textline.bg_b = 255
            self.logger.debug(f"48px color prediction failed: {e}, using default colors")

    def _get_rotate_crop_image(self, img: np.ndarray, points: np.ndarray) -> np.ndarray:
        """
        Extract and rotate text region using perspective transform.
        Based on PaddleOCR's get_rotate_crop_image implementation.

        Automatically rotates vertical text (height/width >= 1.5) to horizontal.

        Args:
            img: RGB image
            points: 4 corner points of text region [4, 2]

        Returns:
            Cropped and rotated BGR image
        """
        try:
            assert len(points) == 4, "points must have 4 corners"

            # Calculate crop dimensions based on edge lengths
            img_crop_width = int(max(
                np.linalg.norm(points[0] - points[1]),
                np.linalg.norm(points[2] - points[3])
            ))
            img_crop_height = int(max(
                np.linalg.norm(points[0] - points[3]),
                np.linalg.norm(points[1] - points[2])
            ))

            # Prevent invalid dimensions
            if img_crop_width <= 0 or img_crop_height <= 0:
                return None

            # Define target rectangle
            pts_std = np.float32([
                [0, 0],
                [img_crop_width, 0],
                [img_crop_width, img_crop_height],
                [0, img_crop_height],
            ])

            # Perspective transform
            M = cv2.getPerspectiveTransform(points.astype(np.float32), pts_std)
            dst_img = cv2.warpPerspective(
                img,
                M,
                (img_crop_width, img_crop_height),
                borderMode=cv2.BORDER_REPLICATE,
                flags=cv2.INTER_CUBIC,
            )

            dst_img_height, dst_img_width = dst_img.shape[0:2]

            # Rotate vertical text (height/width >= 1.5) to horizontal
            if dst_img_height * 1.0 / dst_img_width >= 1.5:
                dst_img = np.rot90(dst_img)

            return dst_img

        except Exception as e:
            self.logger.warning(f"Failed to extract rotated crop: {e}")
            return None


# Alias for backward compatibility
class ModelPaddleOCRChinese(ModelPaddleOCR):
    """Chinese/Japanese/English OCR"""
    def __init__(self, *args, **kwargs):
        super().__init__(model_type='ch', *args, **kwargs)


class ModelPaddleOCRKorean(ModelPaddleOCR):
    """Korean/English OCR"""
    def __init__(self, *args, **kwargs):
        super().__init__(model_type='korean', *args, **kwargs)


class ModelPaddleOCRLatin(ModelPaddleOCR):
    """Latin/English OCR"""
    def __init__(self, *args, **kwargs):
        super().__init__(model_type='latin', *args, **kwargs)
