import logging
import math
import os
import re
import threading
from types import SimpleNamespace
from typing import List, Optional, Tuple

import cv2
import numpy as np
from hyphen import Hyphenator
from hyphen.dictools import LANGUAGES as HYPHENATOR_LANGUAGES
from langcodes import standardize_tag
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QRawFont,
    QTextLayout,
)

from ..utils import BASE_PATH

try:
    HYPHENATOR_LANGUAGES.remove('fr')
    HYPHENATOR_LANGUAGES.append('fr_FR')
except Exception:
    pass

CJK_H2V = {
    "‥": "︰",
    "─": "│",
    "━": "┃",
    "═": "║",
    "—": "︱",
    "―": "|",
    "–": "︲",
    "_": "︴",
    "(": "︵",
    ")": "︶",
    "（": "︵",
    "）": "︶",
    "{": "︷",
    "}": "︸",
    "〔": "︹",
    "〕": "︺",
    "【": "︻",
    "】": "︼",
    "《": "︽",
    "》": "︾",
    "〈": "︿",
    "〉": "﹀",
    "⟨": "︿",   
    "⟩": "﹀",   
    "⟪": "︿",   
    "⟫": "﹀",       
    "「": "﹁",
    "」": "﹂",
    "『": "﹃",
    "』": "﹄",
    "﹑": "﹅",
    "﹆": "﹆",
    "[": "﹇",
    "]": "﹈",
    "⦅": "︵",   
    "⦆": "︶",   
    "❨": "︵",          
    "❩": "︶",   
    "❪": "︷",   
    "❫": "︸",   
    "❬": "﹇",   
    "❭": "﹈",   
    "❮": "︿",   
    "❯": "﹀",    
    "﹉": "﹉",
    "﹊": "﹊",
    "﹋": "﹋",
    "﹌": "﹌",
    "﹍": "﹍",
    "﹎": "﹎",
    "﹏": "﹏",
    "…": "⋮",
    "⋯": "︙", 
    "⋰": "⋮",    
    "⋱": "⋮",           
    "\"": "﹂",   
    "'": "﹂",   
    "″": "﹂",   
    "‴": "﹂",   
    "‶": "﹁",   
    "ⷷ": "﹁",   
    "〜": "︴",   
    "～": "︴",   
    "~": "≀",
    "〰": "︴",
    "!": "︕",    
    "?": "︖",    
    "؟": "︖",    
    "¿": "︖",    
    "¡": "︕",    
    ".": "︒",
    "。": "︒",   
    ";": "︔",    
    "；": "︔",   
    ":": "︓",    
    "：": "︓",  
    ",": "︐",
    "，": "︐",   
    # "､": "︐",    
    "‚": "︐",    
    "„": "︐",    
    # "、": "︑",    
    "-": "︲",    
    "−": "︲",
    "・": "·",
}

CJK_V2H = {
    **{v: k for k, v in CJK_H2V.items()},
}

logger = logging.getLogger(__name__)  
logger.addHandler(logging.NullHandler())  

DEFAULT_FONT = os.path.join(BASE_PATH, 'fonts', 'Arial-Unicode-Regular.ttf')
_HORIZONTAL_SYMBOL_HALFWIDTH_MAP = str.maketrans({
    '！': '!',
    '？': '?',
})
_VERTICAL_OPEN_BRACKETS = {
    '「', '『', '（', '《', '〈', '【', '〔', '［', '｛', '(', '“', '‘',
    '﹁', '﹃', '︵', '︷', '︹', '︻', '︽', '︿', '﹇',
}
_VERTICAL_CLOSE_BRACKETS = {
    '」', '』', '）', '》', '〉', '】', '〕', '］', '｝', ')', '”', '’',
    '﹂', '﹄', '︶', '︸', '︺', '︼', '︾', '﹀', '﹈',
}
_VERTICAL_PUNCT_UP = {
    '。', '．', '，', '、', '·', '：', '；', '！', '？',
    '︒', '︐', '︑', '︓', '︔', '︕', '︖', '﹅', '﹆',
}
_VERTICAL_COMPACT_SLOT = _VERTICAL_OPEN_BRACKETS | _VERTICAL_CLOSE_BRACKETS | _VERTICAL_PUNCT_UP

def CJK_Compatibility_Forms_translate(cdpt: str, direction: int):
    """direction: 0 - horizontal, 1 - vertical"""

    if cdpt == 'ー' and direction == 1:
        return 'ー', 90
    if cdpt in CJK_V2H:
        if direction == 0:
            # translate
            return CJK_V2H[cdpt], 0
        else:
            return cdpt, 0
    elif cdpt in CJK_H2V:
        if direction == 1:
            # translate
            return CJK_H2V[cdpt], 0
        else:
            return cdpt, 0
    return cdpt, 0

def compact_special_symbols(text: str) -> str:
    # 替换半角省略号
    text = text.replace('...', '…')
    text = text.replace('..', '…')
    # 仅合并 3 个及以上连续省略号，保留标准六点省略号（两个“…“）
    text = re.sub(r'…{3,}', '……', text)
    # 将西文省略号(U+2026,贴底)替换为居中省略号(U+22EF)，解决横排省略号位置偏下的问题
    text = text.replace('…', '⋯')
    # Remove half-width and full-width spaces after each punctuation mark
    # 只删除标点符号后的空格，不删除字母/数字后的空格
    # 匹配常见的标点符号：。，、！？；：…等
    pattern = r'([。，、！？；：…—～「」『』【】（）《》〈〉.,!?;:\-])[ 　]+'
    text = re.sub(pattern, r'\1', text)
    return text

def auto_add_horizontal_tags(text: str) -> str:
    """自动为竖排文本中的短英文单词或连续符号添加<H>标签，使其横向显示。

    处理规则：
    - 整段文本统一处理，不按 [BR]/\n 分段
    - 多词英文词组（如 "Tek Tok"）：整体横排显示
    - 独立的短英文单词：添加<H>标签
    - 符号（!?）2-3个：横排显示，4个以上不包裹

    渲染规则：
    - 字母/数字块：旋转90度显示
    - 其他情况（含符号）：保持横排显示
    """
    # 如果文本中已有<H>标签，则不进行处理，以尊重手动设置
    if '<H>' in text or '<h>' in text.lower():
        return text

    # 先保护 BR 标记与换行，避免被步骤1/2直接匹配吞掉。
    br_pattern = re.compile(r'(\[BR\]|<br\s*/?>|【BR】|\r\n|\r|\n)', flags=re.IGNORECASE)
    br_tokens = []

    def _mask_br(match):
        idx = len(br_tokens)
        br_tokens.append(match.group(0))
        # 使用不会被英文/数字正则命中的私有区字符占位
        return chr(0xE000 + idx)

    seg = br_pattern.sub(_mask_br, text)

    # 步骤1：为多词英文词组添加<H>标签（至少2个单词，用空格分隔）
    multi_word_pattern = r'[a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-]+(?:\s+[a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-]+)+'
    seg = re.sub(multi_word_pattern, r'<H>\g<0></H>', seg)

    # 步骤2：对剩余的独立英文单词添加<H>标签
    word_pattern = r'(?<![a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-])([a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-]{2,})(?![a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-])'

    # 用闭包捕获当前 seg 的值
    def _make_replace_word(current_seg):
        def replace_word(match):
            start_pos = match.start()
            text_before = current_seg[:start_pos]
            last_open = text_before.rfind('<H>')
            last_close = text_before.rfind('</H>')
            if last_open > last_close:
                return match.group(0)
            return f'<H>{match.group(1)}</H>'
        return replace_word

    seg = re.sub(word_pattern, _make_replace_word(seg), seg)

    # 步骤3：匹配符号（2-4个，同时支持半角和全角，5个以上不包裹）
    symbol_pattern = r'[!?！？]{2,4}'
    seg = re.sub(symbol_pattern, r'<H>\g<0></H>', seg)

    # 还原 BR/换行 标记
    for idx, original in enumerate(br_tokens):
        seg = seg.replace(chr(0xE000 + idx), original)

    # 跨 BR/换行的纯符号块一律不打标（两边都去掉 <H>）
    # 例：
    # - <H>!?</H>[BR]<H>!?</H> -> !?[BR]!?
    # - <H>!!!</H>[BR]<H>!!</H> -> !!![BR]!!
    symbol_pair_on_br_pattern = re.compile(
        r'<H>([!?！？]{2,4})</H>\s*(\r\n|\r|\n|\[BR\]|<br\s*/?>|【BR】)\s*<H>([!?！？]{2,4})</H>',
        flags=re.IGNORECASE
    )

    def _unwrap_symbol_pair(match):
        left, sep, right = match.group(1), match.group(2), match.group(3)
        return f"{left}{sep}{right}"

    while True:
        updated = symbol_pair_on_br_pattern.sub(_unwrap_symbol_pair, seg)
        if updated == seg:
            break
        seg = updated

    # 将被 BR/换行分隔的纯字母数字横排块合并为一个块：
    # <H>abc</H>[BR]<H>def</H> -> <H>abc[BR]def</H>
    merge_pattern = re.compile(
        r'<H>([a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19]+)</H>\s*(?:\r\n|\r|\n|\[BR\]|<br\s*/?>|【BR】)\s*<H>([a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19]+)</H>',
        flags=re.IGNORECASE
    )
    while True:
        merged = merge_pattern.sub(r'<H>\1[BR]\2</H>', seg)
        if merged == seg:
            break
        seg = merged

    # 跨 BR/换行的单字母/数字对也打成一个横排块：
    # a[BR]c -> <H>a[BR]c</H>
    single_pair_pattern = re.compile(
        r'(?<![a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19])'
        r'([a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19])'
        r'\s*(?:\r\n|\r|\n|\[BR\]|<br\s*/?>|【BR】)\s*'
        r'([a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19])'
        r'(?![a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19])',
        flags=re.IGNORECASE
    )
    seg = single_pair_pattern.sub(r'<H>\1[BR]\2</H>', seg)

    # 横排块内部若有换行，统一规范为 [BR]
    seg = re.sub(
        r'<H>(.*?)</H>',
        lambda m: (
            "<H>"
            + m.group(1).replace('\r\n', '[BR]').replace('\r', '[BR]').replace('\n', '[BR]')
            + "</H>"
        ),
        seg,
        flags=re.IGNORECASE | re.DOTALL
    )

    return seg


def _normalize_horizontal_block_content(content: str) -> str:
    """Normalize content inside <H>...</H> for rotation/measurement/rendering."""
    if not content:
        return ""
    content = re.sub(r'\s*(\[BR\]|<br\s*/?>|【BR】)\s*', '', content, flags=re.IGNORECASE)
    content = content.replace('\r', '').replace('\n', '')
    if re.fullmatch(r'[!?！？]+', content):
        content = content.translate(_HORIZONTAL_SYMBOL_HALFWIDTH_MAP)
    return content


def prepare_text_for_direction_rendering(text: str, is_horizontal: bool, auto_rotate_symbols: bool = False) -> str:
    """Render-stage normalization only.

    渲染链路不再自行补 <H>，这里只处理既有标记的方向适配。
    """
    text = text or ""
    if is_horizontal:
        return re.sub(r'<H>(.*?)</H>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    _ = auto_rotate_symbols
    return text

def _convert_br_outside_h_tags(text: str) -> str:
    """Convert BR markers to '\\n' outside <H>, and split BR inside <H> into per-line <H> blocks."""
    parts = re.split(r'(<H>.*?</H>)', text, flags=re.IGNORECASE | re.DOTALL)
    converted = []
    for part in parts:
        if not part:
            continue
        is_horizontal_block = part.lower().startswith('<h>') and part.lower().endswith('</h>')
        if is_horizontal_block:
            content = part[3:-4]
            # BR inside one <H> block: split into multiple lines
            chunks = re.split(r'\s*(?:\[BR\]|<br\s*/?>|【BR】|\r\n|\r|\n)\s*', content, flags=re.IGNORECASE)
            chunks = [c for c in chunks if c]
            if len(chunks) <= 1:
                converted.append(part)
                continue

            split_blocks = []
            for chunk in chunks:
                chunk_clean = _normalize_horizontal_block_content(chunk)
                if not chunk_clean:
                    continue
                split_blocks.append(f'<H>{chunk_clean}</H>')
            converted.append('\n'.join(split_blocks))
        else:
            converted.append(re.sub(r'\s*(\[BR\]|<br>|【BR】)\s*', '\n', part, flags=re.IGNORECASE))
    return ''.join(converted)

def should_rotate_horizontal_block_90(content: str) -> bool:
    """Rotate 90 degrees for alphanumeric <H> blocks in vertical layout.

    Supports multi-word Latin phrases such as "Blue Box".
    """
    if not content:
        return False
    content = _normalize_horizontal_block_content(content).strip()
    if not content:
        return False
    # 字母/数字块（允许词间空格）一律旋转90度；符号块保持横排
    latin_phrase = re.fullmatch(
        r'[a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-]+'
        r'(?:[ \t]+[a-zA-Z0-9\uff21-\uff3a\uff41-\uff5a\uff10-\uff19_-]+)*',
        content,
    )
    return bool(latin_phrase)

def add_color(bw_char_map, color, stroke_char_map, stroke_color):
    if bw_char_map.size == 0:
        fg = np.zeros((bw_char_map.shape[0], bw_char_map.shape[1], 4), dtype = np.uint8)
        return fg
    
    if stroke_color is None :
        x, y, w, h = cv2.boundingRect(bw_char_map)
    else :
        x, y, w, h = cv2.boundingRect(stroke_char_map)

    # 检查 boundingRect 返回的尺寸是否有效
    if w == 0 or h == 0:
        fg = np.zeros((bw_char_map.shape[0], bw_char_map.shape[1], 4), dtype = np.uint8)
        return fg

    fg = np.zeros((h, w, 4), dtype = np.uint8)
    fg[:,:,0] = color[0]
    fg[:,:,1] = color[1]
    fg[:,:,2] = color[2]
    fg[:,:,3] = bw_char_map[y:y+h, x:x+w]

    if stroke_color is None :
        stroke_color = color
    bg = np.zeros((stroke_char_map.shape[0], stroke_char_map.shape[1], 4), dtype = np.uint8)
    bg[:,:,0] = stroke_color[0]
    bg[:,:,1] = stroke_color[1]
    bg[:,:,2] = stroke_color[2]
    bg[:,:,3] = stroke_char_map

    fg_alpha = fg[:, :, 3] / 255.0
    bg_alpha = 1.0 - fg_alpha
    bg[y:y+h, x:x+w, :] = (fg_alpha[:, :, np.newaxis] * fg[:, :, :] + bg_alpha[:, :, np.newaxis] * bg[y:y+h, x:x+w, :])

    return bg

FALLBACK_FONTS = [
    os.path.join(BASE_PATH, 'fonts/Arial-Unicode-Regular.ttf'),
    os.path.join(BASE_PATH, 'fonts/msyh.ttc'),
    os.path.join(BASE_PATH, 'fonts/msgothic.ttc'),
]
_thread_font_state = threading.local()
_qt_runtime_lock = threading.Lock()
_qt_runtime_app = None
_QT_FONT_PROBE_SIZE = 32.0
_font_family_cache = {}


def _normalize_font_path(path: str) -> str:
    return path.replace('\\', '/')


def _ensure_qt_runtime():
    global _qt_runtime_app

    app = QGuiApplication.instance()
    if app is not None:
        return app

    with _qt_runtime_lock:
        app = QGuiApplication.instance()
        if app is not None:
            return app
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        _qt_runtime_app = QGuiApplication([])
        return _qt_runtime_app


def _new_font_state() -> dict:
    return {
        'font': None,
        'font_selection': [],
        'font_cache': {},
        'layout_font_cache': {},
        'glyph_cache': {},
        'border_cache': {},
        'measure_cache': {},
        'vertical_char_base_cache': {},
        'vertical_border_bitmap_cache': {},
    }


def _cache_small_dict(cache: dict, key, value, limit: int = 4096):
    if len(cache) >= limit:
        cache.clear()
    cache[key] = value
    return value


def _cache_glyph(state: dict, key: Tuple, glyph: SimpleNamespace) -> SimpleNamespace:
    return _cache_small_dict(state['glyph_cache'], key, glyph)


def _normalize_cache_float(value: float) -> float:
    return round(float(value), 4)


def _clear_glyph_cache(state: Optional[dict] = None):
    if state is None:
        state = _get_thread_font_state()
    state['glyph_cache'].clear()
    state['border_cache'].clear()
    state['measure_cache'].clear()
    state['vertical_char_base_cache'].clear()
    state['vertical_border_bitmap_cache'].clear()


def _get_thread_font_state() -> dict:
    state = getattr(_thread_font_state, 'value', None)
    if state is None:
        state = _new_font_state()
        _thread_font_state.value = state
        try:
            state['font'] = _load_font_for_state(state, DEFAULT_FONT)
        except Exception as e:
            logger.error(f"Failed to initialize default font: {e}")
            state['font'] = None
        _refresh_font_selection(state)
    return state


def _resolve_existing_font_path(path: str) -> str:
    if not path:
        return ''

    normalized_path = _normalize_font_path(path)
    candidates = [normalized_path]
    if not os.path.isabs(normalized_path):
        candidates.extend(
            [
                _normalize_font_path(os.path.join(BASE_PATH, 'fonts', os.path.basename(normalized_path))),
                _normalize_font_path(os.path.join(BASE_PATH, normalized_path)),
            ]
        )

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ''


def _get_raw_font_for_state(state: dict, path: str, pixel_size: float) -> QRawFont:
    _ensure_qt_runtime()
    key = (_normalize_font_path(path), float(max(pixel_size, 1.0)))
    raw_font = state['font_cache'].get(key)
    if raw_font is None:
        raw_font = QRawFont(key[0], key[1])
        if not raw_font.isValid():
            raise RuntimeError(f'Could not load Qt font: {key[0]}')
        state['font_cache'][key] = raw_font
    return raw_font


def _get_qfont_family_for_path(path: str) -> str:
    _ensure_qt_runtime()
    normalized_path = _normalize_font_path(path)
    family = _font_family_cache.get(normalized_path)
    if family:
        return family

    font_id = QFontDatabase.addApplicationFont(normalized_path)
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family = families[0]

    if not family:
        raw_font = QRawFont(normalized_path, _QT_FONT_PROBE_SIZE)
        if raw_font.isValid():
            family = raw_font.familyName()

    if not family:
        raise RuntimeError(f'Could not resolve Qt font family: {path}')

    _font_family_cache[normalized_path] = family
    return family


def _get_layout_font_for_state(state: dict, path: str, pixel_size: float) -> QFont:
    cache = state.setdefault('layout_font_cache', {})
    key = (_normalize_font_path(path), int(max(pixel_size, 1)))
    qfont = cache.get(key)
    if qfont is None:
        family = _get_qfont_family_for_path(key[0])
        qfont = QFont(family)
        qfont.setPixelSize(key[1])
        qfont.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        qfont.setStyleStrategy(QFont.StyleStrategy.PreferOutline)
        cache[key] = qfont
    return QFont(qfont)


def _load_font_for_state(state: dict, path: str) -> str:
    resolved_path = _resolve_existing_font_path(path)
    if not resolved_path:
        raise RuntimeError(f'Could not resolve font path: {path}')
    _get_raw_font_for_state(state, resolved_path, _QT_FONT_PROBE_SIZE)
    return resolved_path


def _refresh_font_selection(state: Optional[dict] = None):
    if state is None:
        state = _get_thread_font_state()
    font_selection = []
    if state['font'] is not None:
        font_selection.append(state['font'])
    for font_path in FALLBACK_FONTS:
        try:
            resolved_path = _load_font_for_state(state, font_path)
            if resolved_path not in font_selection:
                font_selection.append(resolved_path)
        except Exception as e:
            logger.error(f"Failed to load fallback font: {font_path} - {e}")
    state['font_selection'] = font_selection
    return font_selection


def get_cached_font(path: str) -> str:
    state = _get_thread_font_state()
    return _load_font_for_state(state, path)


def update_font_selection():
    return _refresh_font_selection()


def set_font(path: str):
    state = _get_thread_font_state()
    try:
        state['font'] = get_cached_font(path)
    except Exception:
        if path:
            logger.error(f'Could not load font: {path}')
        try:
            state['font'] = get_cached_font(DEFAULT_FONT)
        except Exception:
            logger.critical("Default font could not be loaded. Please check your installation.")
            state['font'] = None
    _refresh_font_selection(state)
    _clear_glyph_cache(state)

def _resolve_stroke_ratio(config=None, stroke_width: Optional[float] = None) -> float:
    if stroke_width is not None:
        return float(stroke_width)
    render_config = getattr(config, 'render', None)
    return float(getattr(render_config, 'stroke_width', 0.07))


def _qimage_alpha_to_array(image: QImage) -> np.ndarray:
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((image.height(), image.bytesPerLine() // 4, 4))
    return arr[:, :image.width(), 3].copy()


def _rasterize_path_to_alpha(path) -> Tuple[np.ndarray, int, int]:
    if path.isEmpty():
        return np.zeros((0, 0), dtype=np.uint8), 0, 0

    rect = path.boundingRect()
    left = math.floor(rect.left())
    top = math.floor(rect.top())
    width = max(0, math.ceil(rect.right()) - left)
    height = max(0, math.ceil(rect.bottom()) - top)
    if width <= 0 or height <= 0:
        return np.zeros((0, 0), dtype=np.uint8), left, top

    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 255))
    painter.translate(-left, -top)
    painter.drawPath(path)
    painter.end()

    return _qimage_alpha_to_array(image), left, top


def _bitmap_from_alpha(alpha: np.ndarray) -> SimpleNamespace:
    return SimpleNamespace(
        rows=int(alpha.shape[0]),
        width=int(alpha.shape[1]),
        buffer=alpha.reshape(-1).copy(),
    )


def _create_stroke_path(path: QPainterPath, stroke_px: int) -> QPainterPath:
    if path.isEmpty() or stroke_px <= 0:
        return QPainterPath()
    stroker = QPainterPathStroker()
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroker.setWidth(float(stroke_px) * 2.0)
    return stroker.createStroke(path).subtracted(path)


def _make_glyph_slot(
    alpha: np.ndarray,
    *,
    advance_x: int,
    advance_y: int,
    bitmap_left: int,
    bitmap_top: int,
    metrics_width: int,
    metrics_height: int,
    vert_bearing_y: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        bitmap=_bitmap_from_alpha(alpha),
        advance=SimpleNamespace(
            x=int(advance_x) << 6,
            y=int(advance_y) << 6,
        ),
        bitmap_left=int(bitmap_left),
        bitmap_top=int(bitmap_top),
        metrics=SimpleNamespace(
            vertBearingX=0,
            vertBearingY=int(vert_bearing_y) << 6,
            horiBearingX=int(bitmap_left) << 6,
            horiBearingY=int(bitmap_top) << 6,
            horiAdvance=int(advance_x) << 6,
            vertAdvance=int(advance_y) << 6,
            width=int(metrics_width) << 6,
            height=int(metrics_height) << 6,
        ),
    )


def _build_glyph_from_path(font_path: str, glyph_id: int, font_size: int):
    state = _get_thread_font_state()
    cache_key = ('glyph-id', font_path, int(glyph_id), int(font_size))
    cached = state['glyph_cache'].get(cache_key)
    if cached is not None:
        return cached

    raw_font = _get_raw_font_for_state(state, font_path, font_size)
    path = raw_font.pathForGlyph(glyph_id)
    alpha, left, top = _rasterize_path_to_alpha(path)
    advances = raw_font.advancesForGlyphIndexes([glyph_id]) if glyph_id else []
    advance_x = int(round(advances[0].x())) if advances else 0
    rect = path.boundingRect()
    metrics_width = max(alpha.shape[1], int(math.ceil(rect.width())))
    metrics_height = max(alpha.shape[0], int(math.ceil(rect.height())))
    if advance_x <= 0 and metrics_width > 0:
        advance_x = metrics_width
    advance_y = max(1, font_size)
    if metrics_height > 0:
        advance_y = max(advance_y, metrics_height)

    glyph = _make_glyph_slot(
        alpha,
        advance_x=advance_x,
        advance_y=advance_y,
        bitmap_left=left,
        bitmap_top=-top,
        metrics_width=max(metrics_width, advance_x),
        metrics_height=max(metrics_height, advance_y),
        vert_bearing_y=top,
    )
    return _cache_glyph(state, cache_key, glyph)


def _build_stroked_glyph_bitmap(font_path: str, glyph_id: int, font_size: int, stroke_ratio: float):
    state = _get_thread_font_state()
    stroke_px = max(int(stroke_ratio * font_size), 1)
    cache_key = ('stroke', font_path, int(glyph_id), int(font_size), stroke_px)
    cached = state['border_cache'].get(cache_key)
    if cached is not None:
        return cached

    raw_font = _get_raw_font_for_state(state, font_path, font_size)
    path = raw_font.pathForGlyph(glyph_id)
    if path.isEmpty():
        border = SimpleNamespace()
        border.bitmap = _bitmap_from_alpha(np.zeros((0, 0), dtype=np.uint8))
        border.left = 0
        border.top = 0
        state['border_cache'][cache_key] = border
        return border

    stroke_path = _create_stroke_path(path, stroke_px)
    alpha, left, top = _rasterize_path_to_alpha(stroke_path)
    border = SimpleNamespace()
    border.bitmap = _bitmap_from_alpha(alpha)
    border.left = left
    border.top = -top
    state['border_cache'][cache_key] = border
    return border


def _paste_bitmap(canvas: np.ndarray, bitmap_arr: np.ndarray, x: int, y: int, mode: str = 'max'):
    x = int(round(x))
    y = int(round(y))
    rows, width = bitmap_arr.shape
    paste_y_start = max(0, y)
    paste_x_start = max(0, x)
    paste_y_end = min(canvas.shape[0], y + rows)
    paste_x_end = min(canvas.shape[1], x + width)
    if paste_y_start >= paste_y_end or paste_x_start >= paste_x_end:
        return
    bitmap_slice = bitmap_arr[
        paste_y_start - y: paste_y_end - y,
        paste_x_start - x: paste_x_end - x
    ]
    target = canvas[paste_y_start:paste_y_end, paste_x_start:paste_x_end]
    if mode == 'add':
        canvas[paste_y_start:paste_y_end, paste_x_start:paste_x_end] = cv2.add(target, bitmap_slice)
    else:
        canvas[paste_y_start:paste_y_end, paste_x_start:paste_x_end] = np.maximum(target, bitmap_slice)


def _bitmap_to_array(bitmap) -> Optional[np.ndarray]:
    rows = int(getattr(bitmap, 'rows', 0))
    width = int(getattr(bitmap, 'width', 0))
    buffer = getattr(bitmap, 'buffer', None)
    if rows <= 0 or width <= 0 or buffer is None or len(buffer) != rows * width:
        return None
    return np.asarray(buffer, dtype=np.uint8).reshape((rows, width))


def _paste_glyph_bitmaps(
    canvas_text: np.ndarray,
    canvas_border: np.ndarray,
    bitmap_char: np.ndarray,
    char_place_x: int,
    char_place_y: int,
    bitmap_border: Optional[np.ndarray] = None,
):
    _paste_bitmap(canvas_text, bitmap_char, char_place_x, char_place_y, mode='max')
    if bitmap_border is None:
        return
    border_place_x = char_place_x - round((bitmap_border.shape[1] - bitmap_char.shape[1]) / 2.0)
    border_place_y = char_place_y - round((bitmap_border.shape[0] - bitmap_char.shape[0]) / 2.0)
    _paste_bitmap(canvas_border, bitmap_border, border_place_x, border_place_y, mode='add')


def _paste_surface(canvas_text: np.ndarray, canvas_border: np.ndarray, surface: dict, paste_x: int, paste_y: int):
    _paste_bitmap(canvas_text, surface['text'], paste_x, paste_y, mode='max')
    _paste_bitmap(canvas_border, surface['border'], paste_x, paste_y, mode='add')


def _normalize_horizontal_measure_text(text: str) -> str:
    if not text:
        return ''
    normalized_chars = []
    for char in text:
        if char in '\r\n':
            normalized_chars.append(char)
            continue
        translated, _ = CJK_Compatibility_Forms_translate(char, 0)
        normalized_chars.append(translated)
    return ''.join(normalized_chars)


def _create_horizontal_text_layout(line_text: str, font_size: int, letter_spacing: float = 1.0):
    normalized_text = _normalize_horizontal_measure_text(line_text)

    state = _get_thread_font_state()
    font_path = state['font'] or DEFAULT_FONT
    qfont = _get_layout_font_for_state(state, font_path, font_size)
    qfont.setKerning(True)
    qfont.setLetterSpacing(QFont.SpacingType.PercentageSpacing, float(letter_spacing) * 100.0)

    if not normalized_text:
        return normalized_text, qfont, None, None

    layout = QTextLayout(normalized_text, qfont)
    layout.beginLayout()
    line = layout.createLine()
    if not line.isValid():
        layout.endLayout()
        return normalized_text, qfont, None, None
    line.setLineWidth(1_000_000.0)
    line.setPosition(QPointF(0.0, 0.0))
    layout.endLayout()
    return normalized_text, qfont, layout, line


def _get_horizontal_line_frame_metrics(line_text: str, font_size: int, letter_spacing: float = 1.0) -> dict:
    normalized_text, qfont, _, line = _create_horizontal_text_layout(line_text, font_size, letter_spacing=letter_spacing)
    font_metrics = QFontMetricsF(qfont)
    if line is None:
        return {
            'text': normalized_text,
            'logical_width': 0.0,
            'ascent': float(font_metrics.ascent()),
            'height': float(font_metrics.height()),
            'descent': float(font_metrics.descent()),
        }
    return {
        'text': normalized_text,
        'logical_width': _get_horizontal_line_logical_width(line, len(normalized_text)),
        'ascent': float(line.ascent()),
        'height': float(line.height()),
        'descent': float(line.descent()),
    }


def _get_horizontal_line_logical_width(line, text_length: int) -> float:
    cursor_x = line.cursorToX(text_length)
    if isinstance(cursor_x, tuple):
        cursor_x = cursor_x[0]
    return float(cursor_x)


def _crop_bitmap_pair(text_canvas: np.ndarray, border_canvas: np.ndarray):
    combined = cv2.add(text_canvas, border_canvas)
    if not np.any(combined):
        return None
    x, y, w, h = cv2.boundingRect(combined)
    if w == 0 or h == 0:
        return None
    return text_canvas[y:y+h, x:x+w], border_canvas[y:y+h, x:x+w], x, y, w, h


def _render_horizontal_line_surface(
    line_text: str,
    font_size: int,
    border_size: int,
    stroke_ratio: float = 0.07,
    reversed_direction: bool = False,
    letter_spacing: float = 1.0,
):
    if not line_text:
        return None

    normalized_text, _, layout, line = _create_horizontal_text_layout(line_text, font_size, letter_spacing=letter_spacing)
    if line is None:
        return None

    path = QPainterPath()
    for glyph_run in layout.glyphRuns():
        raw_font = glyph_run.rawFont()
        glyph_indexes = glyph_run.glyphIndexes()
        positions = glyph_run.positions()
        for glyph_index, pos in zip(glyph_indexes, positions):
            glyph_path = raw_font.pathForGlyph(glyph_index)
            if glyph_path.isEmpty():
                continue
            glyph_path.translate(pos.x(), pos.y())
            path.addPath(glyph_path)

    if path.isEmpty():
        return None

    fill_alpha, fill_left, fill_top = _rasterize_path_to_alpha(path)
    if fill_alpha.size == 0:
        return None

    if border_size > 0:
        stroke_path = _create_stroke_path(path, max(int(stroke_ratio * font_size), 1))
        border_alpha, border_left, border_top = _rasterize_path_to_alpha(stroke_path)
        left = min(fill_left, border_left)
        top = min(fill_top, border_top)
        right = max(fill_left + fill_alpha.shape[1], border_left + border_alpha.shape[1])
        bottom = max(fill_top + fill_alpha.shape[0], border_top + border_alpha.shape[0])
        text_canvas = np.zeros((bottom - top, right - left), dtype=np.uint8)
        border_canvas = np.zeros((bottom - top, right - left), dtype=np.uint8)
        _paste_bitmap(text_canvas, fill_alpha, fill_left - left, fill_top - top, mode='max')
        _paste_bitmap(border_canvas, border_alpha, border_left - left, border_top - top, mode='max')
    else:
        left, top = fill_left, fill_top
        text_canvas = fill_alpha
        border_canvas = np.zeros_like(fill_alpha)

    cropped = _crop_bitmap_pair(text_canvas, border_canvas)
    if cropped is None:
        return None

    text_bitmap, border_bitmap, x, y, w, h = cropped
    logical_width = _get_horizontal_line_logical_width(line, len(normalized_text))
    origin_x = 0.0 if not reversed_direction else -logical_width
    line_ascent = float(line.ascent())
    line_height = float(line.height())
    baseline_y = line_ascent
    ink_top = float(top + y)
    ink_bottom = float(top + y + h)
    return {
        'text': text_bitmap,
        'border': border_bitmap,
        'left_rel': left + x - origin_x,
        'right_rel': left + x - origin_x + w,
        'top_rel': top + y - baseline_y,
        'width': w,
        'height': h,
        'line_ascent': line_ascent,
        'line_descent': float(line.descent()),
        'line_height': line_height,
        'ink_top': ink_top,
        'ink_bottom': ink_bottom,
    }


def _render_horizontal_block_surface(
    font_size: int,
    content: str,
    border_size: int,
    stroke_ratio: float = 0.07,
    rotate_90: bool = False,
    letter_spacing: float = 1.0,
):
    content = _normalize_horizontal_block_content(content)
    if not content:
        return None

    surface = _render_horizontal_line_surface(
        content,
        font_size,
        border_size,
        stroke_ratio=stroke_ratio,
        reversed_direction=False,
        letter_spacing=letter_spacing,
    )
    if surface is None:
        return None

    text_bitmap = surface['text']
    border_bitmap = surface['border']
    if rotate_90:
        text_bitmap = cv2.rotate(text_bitmap, cv2.ROTATE_90_CLOCKWISE)
        border_bitmap = cv2.rotate(border_bitmap, cv2.ROTATE_90_CLOCKWISE)
        cropped = _crop_bitmap_pair(text_bitmap, border_bitmap)
        if cropped is None:
            return None
        text_bitmap, border_bitmap, _, _, w, h = cropped
    else:
        h, w = text_bitmap.shape

    return {
        'text': text_bitmap,
        'border': border_bitmap,
        'width': w,
        'height': h,
    }


def _clamp_surface_origin(canvas_shape, paste_x: int, paste_y: int, width: int, height: int):
    canvas_h, canvas_w = canvas_shape
    if width <= 0 or height <= 0:
        return None
    paste_x = max(0, min(int(paste_x), canvas_w - width))
    paste_y = max(0, min(int(paste_y), canvas_h - height))
    if paste_x < 0 or paste_y < 0 or paste_x + width > canvas_w or paste_y + height > canvas_h:
        return None
    return paste_x, paste_y


def _normalize_letter_spacing(letter_spacing: float) -> float:
    try:
        value = float(letter_spacing)
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


def _scale_advance(advance: int, letter_spacing: float) -> int:
    if advance <= 0:
        return int(advance)
    multiplier = _normalize_letter_spacing(letter_spacing)
    if multiplier == 1.0:
        return int(advance)
    return max(1, int(round(advance * multiplier)))


def _resolve_vertical_char_offset(slot, cdpt: str, font_size: int, letter_spacing: float = 1.0) -> int:
    char_offset_y = font_size
    metrics = getattr(slot, 'metrics', None)
    if metrics:
        if getattr(metrics, 'vertAdvance', 0):
            char_offset_y = metrics.vertAdvance >> 6
        elif getattr(metrics, 'height', 0):
            char_offset_y = metrics.height >> 6

        if _is_vertical_ellipsis_char(cdpt):
            bitmap_char = _bitmap_to_array(slot.bitmap)
            bitmap_rows = 0 if bitmap_char is None else bitmap_char.shape[0]
            char_offset_y = _smart_vertical_ellipsis_advance(slot, font_size, bitmap_rows, bitmap_char)

    advance = getattr(getattr(slot, 'advance', None), 'y', 0)
    if char_offset_y == font_size and advance:
        char_offset_y = advance >> 6
    return _scale_advance(char_offset_y, letter_spacing)


def _compute_vertical_cell_offset(bitmap_char: np.ndarray, advance_y: int) -> int:
    if bitmap_char is None or bitmap_char.size == 0:
        return 0

    rows = bitmap_char.shape[0]
    return round((advance_y - rows) / 2.0)


def _get_bitmap_ink_rect(bitmap_char: Optional[np.ndarray]) -> Optional[Tuple[int, int, int, int]]:
    if bitmap_char is None or bitmap_char.size == 0:
        return None
    rows, width = bitmap_char.shape
    if rows <= 0 or width <= 0:
        return None
    nz = cv2.findNonZero(bitmap_char)
    if nz is None:
        return None
    x, y, w, h = cv2.boundingRect(nz)
    return int(x), int(y), int(w), int(h)


def _resolve_vertical_slot_height(font_size: int, cdpt: str, advance_y: int) -> int:
    if cdpt in _VERTICAL_COMPACT_SLOT:
        compact_height = max(1, int(round(font_size * 0.55)))
        return max(1, min(advance_y, compact_height))
    return max(1, advance_y)


def _get_vertical_char_render_base(font_size: int, cdpt: str, letter_spacing: float = 1.0) -> dict:
    state = _get_thread_font_state()
    cache_key = (int(font_size), cdpt, _normalize_cache_float(_normalize_letter_spacing(letter_spacing)))
    cached = state['vertical_char_base_cache'].get(cache_key)
    if cached is not None:
        return cached

    translated, rot_degree = CJK_Compatibility_Forms_translate(cdpt, 1)
    slot = get_char_glyph(translated, font_size, 1)
    bitmap_char = _bitmap_to_array(slot.bitmap)
    advance_y = _resolve_vertical_char_offset(slot, translated, font_size, letter_spacing=letter_spacing)
    slot_height = _resolve_vertical_slot_height(font_size, translated, advance_y)
    metrics = getattr(slot, 'metrics', None)
    frame_width = font_size
    if metrics and getattr(metrics, 'horiAdvance', 0):
        frame_width = max(frame_width, metrics.horiAdvance >> 6)
    if bitmap_char is None:
        return _cache_small_dict(state['vertical_char_base_cache'], cache_key, {
            'translated': translated,
            'rot_degree': rot_degree,
            'bitmap': None,
            'advance_y': advance_y,
            'y': 0,
            'ink_x': 0.0,
            'ink_w': 0.0,
            'frame_width': max(1, int(frame_width)),
        })

    if rot_degree == 90:
        bitmap_char = cv2.rotate(bitmap_char, cv2.ROTATE_90_CLOCKWISE)
    _, char_bitmap_width = bitmap_char.shape
    ink_rect = _get_bitmap_ink_rect(bitmap_char)
    ink_x = 0.0
    ink_w = float(char_bitmap_width)
    if ink_rect is not None:
        ink_x, _, ink_w, _ = ink_rect
    frame_width = max(frame_width, int(round(ink_w)))
    slot_origin_y = max(0, int(round((advance_y - slot_height) / 2.0)))
    base_y = slot_origin_y + _compute_vertical_cell_offset(bitmap_char, slot_height)
    return _cache_small_dict(state['vertical_char_base_cache'], cache_key, {
        'translated': translated,
        'rot_degree': rot_degree,
        'bitmap': bitmap_char,
        'advance_y': advance_y,
        'ink_x': ink_x,
        'ink_w': ink_w,
        'y': base_y,
        'frame_width': max(1, int(frame_width)),
    })


def _get_vertical_char_draw_state(font_size: int, cdpt: str, line_width: int, letter_spacing: float = 1.0) -> dict:
    base = _get_vertical_char_render_base(font_size, cdpt, letter_spacing=letter_spacing)
    return {
        'translated': base['translated'],
        'rot_degree': base['rot_degree'],
        'bitmap': base['bitmap'],
        'advance_y': base['advance_y'],
        'x': round((line_width - base['ink_w']) / 2.0) - base['ink_x'],
        'y': base['y'],
    }


def _get_vertical_border_bitmap(translated: str, font_size: int, stroke_ratio: float, rot_degree: int):
    state = _get_thread_font_state()
    cache_key = (
        translated,
        int(font_size),
        _normalize_cache_float(stroke_ratio),
        int(rot_degree),
    )
    cached = state['vertical_border_bitmap_cache'].get(cache_key)
    if cached is not None:
        return cached

    bitmap_border = _bitmap_to_array(get_char_border(translated, font_size, 1, stroke_ratio=stroke_ratio).bitmap)
    if bitmap_border is not None and rot_degree == 90:
        bitmap_border = cv2.rotate(bitmap_border, cv2.ROTATE_90_CLOCKWISE)
    return _cache_small_dict(state['vertical_border_bitmap_cache'], cache_key, bitmap_border, limit=2048)


def _get_vertical_block_surface(
    font_size: int,
    raw_content: str,
    border_size: int,
    stroke_ratio: float,
    letter_spacing: float,
    cache: dict,
):
    rotate_90 = should_rotate_horizontal_block_90(raw_content)
    content = _normalize_horizontal_block_content(raw_content)
    if not content:
        return None
    cache_key = (font_size, content, border_size, round(float(stroke_ratio), 4), rotate_90, round(_normalize_letter_spacing(letter_spacing), 4))
    if cache_key in cache:
        return cache[cache_key]
    cache[cache_key] = _render_horizontal_block_surface(
        font_size,
        content,
        border_size,
        stroke_ratio=stroke_ratio,
        rotate_90=rotate_90,
        letter_spacing=letter_spacing,
    )
    return cache[cache_key]


def _build_vertical_line_layout(
    font_size: int,
    line_text: str,
    border_size: int,
    stroke_ratio: float,
    letter_spacing: float,
    block_surface_cache: dict,
) -> dict:
    line_width = font_size
    items = []
    parts = re.split(r'(<H>.*?</H>)', line_text, flags=re.IGNORECASE | re.DOTALL)
    for part in parts:
        if not part:
            continue
        is_horizontal_block = part.lower().startswith('<h>') and part.lower().endswith('</h>')
        if is_horizontal_block:
            surface = _get_vertical_block_surface(font_size, part[3:-4], border_size, stroke_ratio, letter_spacing, block_surface_cache)
            if surface is not None:
                item_width = int(surface['width'])
                line_width = max(line_width, item_width)
                items.append({
                    'kind': 'block',
                    'surface': surface,
                    'width': item_width,
                    'height': int(surface['height']),
                })
            continue
        for c in part:
            if c == '＿':
                items.append({
                    'kind': 'placeholder',
                    'advance_y': _scale_advance(font_size, letter_spacing),
                })
                continue
            base = _get_vertical_char_render_base(font_size, c, letter_spacing=letter_spacing)
            line_width = max(line_width, int(base['frame_width']))
            items.append({
                'kind': 'char',
                'base': base,
            })

    cursor_y = 0
    laid_out_items = []
    for item in items:
        kind = item['kind']
        if kind == 'block':
            block_top = cursor_y
            block_bottom = cursor_y + item['height']
            laid_out_items.append({
                **item,
                'cursor_y': cursor_y,
            })
            cursor_y = block_bottom
            continue

        if kind == 'placeholder':
            laid_out_items.append({
                **item,
                'cursor_y': cursor_y,
            })
            cursor_y += int(item['advance_y'])
            continue

        base = item['base']
        advance_y = int(base['advance_y'])
        bitmap_char = base['bitmap']
        x = round((line_width - base['ink_w']) / 2.0) - base['ink_x']
        y = int(base['y'])
        laid_out_items.append({
            'kind': 'char',
            'translated': base['translated'],
            'rot_degree': base['rot_degree'],
            'bitmap': bitmap_char,
            'advance_y': advance_y,
            'x': x,
            'y': y,
            'cursor_y': cursor_y,
        })
        cursor_y += advance_y
    return {
        'width': line_width,
        'min_y': 0,
        'max_y': max(0, cursor_y),
        'height': max(0, cursor_y),
        'items': laid_out_items,
    }


def _normalize_line_spacing(line_spacing: float) -> float:
    try:
        value = float(line_spacing)
    except (TypeError, ValueError):
        return 1.0
    return value if value > 0 else 1.0


def resolve_horizontal_line_spacing_multiplier(line_spacing: float) -> float:
    value = _normalize_line_spacing(line_spacing)
    if value > 1.0:
        # Keep 1.0 as the legacy baseline, but ramp extra spacing faster once the user raises it.
        return 1.0 + (value - 1.0) * 10.0
    return value


def calc_horizontal_line_spacing_px(font_size: int, line_spacing: float) -> int:
    return int(font_size * 0.01 * resolve_horizontal_line_spacing_multiplier(line_spacing))


def _resolve_glyph_spec(cdpt: str, font_size: int) -> Tuple[str, int]:
    state = _get_thread_font_state()
    font_selection = state['font_selection']
    for i, font_path in enumerate(font_selection):
        raw_font = _get_raw_font_for_state(state, font_path, font_size)
        glyph_indexes = raw_font.glyphIndexesForString(cdpt)
        glyph_id = glyph_indexes[0] if glyph_indexes else 0
        if glyph_id != 0:
            return font_path, int(glyph_id)

        if i == 0:
            try:
                logger.debug(f"Character '{cdpt}' not found in primary font '{font_path}'. Trying fallbacks.")
            except Exception:
                pass

    logger.error(f"FATAL: Character '{cdpt}' (U+{ord(cdpt):04X}) not found in any of the available fonts. Substituting with a placeholder.")
    if cdpt in (' ', '?', '□'):
        raise RuntimeError(f"Catastrophic failure: Placeholder character '{cdpt}' not found in any font.")
    for placeholder in ('?', '□', ' '):
        if placeholder == cdpt:
            continue
        try:
            return _resolve_glyph_spec(placeholder, font_size)
        except RuntimeError:
            continue
    raise RuntimeError("Catastrophic failure: No placeholder character found in any font.")


def get_char_glyph(cdpt: str, font_size: int, direction: int) -> SimpleNamespace:
    font_path, glyph_id = _resolve_glyph_spec(cdpt, font_size)
    return _build_glyph_from_path(font_path, glyph_id, font_size)


# 缓存 glyph border 对象，避免重复创建导致内存泄漏
# Qt 版直接缓存最终描边 bitmap 结果。
def get_char_border(cdpt: str, font_size: int, direction: int, stroke_ratio: float = 0.07):
    font_path, glyph_id = _resolve_glyph_spec(cdpt, font_size)
    return _build_stroked_glyph_bitmap(font_path, glyph_id, font_size, stroke_ratio)

def _is_vertical_ellipsis_char(cdpt: str) -> bool:
    # Support all common ellipsis forms that may appear in vertical flow.
    return cdpt in ('︙', '⋯', '…')

def _estimate_ellipsis_center_gap(bitmap_char: np.ndarray) -> Optional[float]:
    """Estimate center-to-center vertical gap of the 3 dots inside one vertical ellipsis glyph."""
    if bitmap_char is None or bitmap_char.size == 0:
        return None
    mask = (bitmap_char > 0).astype(np.uint8)
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels <= 1:
        return None
    # Skip label 0 (background), keep visible components.
    ys = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area <= 0:
            continue
        ys.append(float(centroids[i][1]))
    if len(ys) < 3:
        return None
    ys.sort()
    # Use the first 3 dots (for standard vertical ellipsis).
    y1, y2, y3 = ys[0], ys[1], ys[2]
    g1 = y2 - y1
    g2 = y3 - y2
    if g1 <= 0 or g2 <= 0:
        return None
    return (g1 + g2) / 2.0

def _smart_vertical_ellipsis_advance(slot, font_size: int, char_bitmap_rows: int, bitmap_char: Optional[np.ndarray] = None) -> int:
    """Make the seam between two vertical ellipsis glyphs close to internal dot spacing."""
    vert_bearing_y = 0
    vert_advance = 0
    if hasattr(slot, 'metrics') and slot.metrics:
        if hasattr(slot.metrics, 'vertBearingY') and slot.metrics.vertBearingY:
            vert_bearing_y = slot.metrics.vertBearingY >> 6
        if hasattr(slot.metrics, 'vertAdvance') and slot.metrics.vertAdvance:
            vert_advance = slot.metrics.vertAdvance >> 6

    # Prefer ink-height + bearing, then fallback to font advance.
    raw = 0
    if char_bitmap_rows > 0:
        raw = char_bitmap_rows + vert_bearing_y
    if raw <= 0:
        raw = vert_advance
    if raw <= 0 and hasattr(slot, 'advance') and slot.advance and hasattr(slot.advance, 'y') and slot.advance.y:
        raw = slot.advance.y >> 6
    if raw <= 0:
        raw = font_size

    # If we can read the 3-dot centers, compute advance so seam gap ~= internal gap.
    # For centers [c1, c2, c3] with gap g, seam-equal advance is about 3g.
    g = _estimate_ellipsis_center_gap(bitmap_char)
    if g is not None and g > 0:
        raw = int(round(3.0 * g))

    return max(1, raw)

def _get_vertical_column_char_width(font_size: int, cdpt: str) -> int:
    """Column frame width for vertical layout (Ballons-style: frame + ink), in pixels."""
    base = _get_vertical_char_render_base(font_size, cdpt)
    return max(1, int(base['frame_width']))

def _measure_horizontal_text_width(text: str, font_size: int, letter_spacing: float = 1.0) -> int:
    if not text:
        return 0

    normalized_text = _normalize_horizontal_measure_text(text)
    if '\n' in normalized_text or '\r' in normalized_text:
        return max(
            (_measure_horizontal_text_width(part, font_size, letter_spacing=letter_spacing) for part in normalized_text.splitlines()),
            default=0,
        )

    state = _get_thread_font_state()
    cache_key = (
        'logical_width',
        state.get('font') or DEFAULT_FONT,
        int(max(font_size, 1)),
        round(_normalize_letter_spacing(letter_spacing), 4),
        normalized_text,
    )
    cached = state['measure_cache'].get(cache_key)
    if cached is not None:
        return cached

    _, _, _, line = _create_horizontal_text_layout(normalized_text, font_size, letter_spacing=letter_spacing)
    width = 0 if line is None else int(round(_get_horizontal_line_logical_width(line, len(normalized_text))))
    if len(state['measure_cache']) >= 4096:
        state['measure_cache'].clear()
    state['measure_cache'][cache_key] = width
    return width

def calc_horizontal_block_height(font_size: int, content: str, letter_spacing: float = 1.0) -> int:
    """
    预先计算横排块在竖排文本中的实际渲染高度
    用于准确计算竖排文本的总高度，特别是在智能缩放模式下

    注意：需要与 put_text_vertical 中的渲染逻辑保持一致
    - 字母/数字块：旋转90度，返回旋转后的实际高度
    - 其他情况（含符号）：横排显示，返回横排块的实际高度
    """
    rotate_90 = should_rotate_horizontal_block_90(content)
    content = _normalize_horizontal_block_content(content)
    if not content:
        return font_size

    surface = _render_horizontal_block_surface(
        font_size,
        content,
        border_size=0,
        stroke_ratio=0.0,
        rotate_90=rotate_90,
        letter_spacing=letter_spacing,
    )
    if surface is None:
        return font_size
    return int(surface['height']) if surface['height'] > 0 else font_size

def calc_vertical(font_size: int, text: str, max_height: int, config=None, letter_spacing: float = 1.0):
    """
    Line breaking logic for vertical text.
    Handles forced newlines (\\n) and is aware of <H> horizontal blocks.
    """
    # 统一处理所有类型的AI换行符（仅转换 <H> 外部）
    text = _convert_br_outside_h_tags(text)
    # 与 put_text_vertical 保持一致：竖排计算前先将省略号转换为竖排符号
    text = text.replace('…', '︙')

    line_text_list = []
    line_height_list = []

    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        if not paragraph:
            line_text_list.append('')
            line_height_list.append(0)
            continue

        current_line_text = ""
        current_line_height = 0

        parts = re.split(r'(<H>.*?</H>)', paragraph, flags=re.IGNORECASE | re.DOTALL)

        for part in parts:
            if not part:
                continue

            is_horizontal_block = part.lower().startswith('<h>') and part.lower().endswith('</h>')

            if is_horizontal_block:
                content = part[3:-4]
                if not content:
                    continue
                # 使用实际渲染高度而不是固定的 font_size
                # 这对于智能缩放模式下准确计算文本框拉伸比例至关重要
                block_height = calc_horizontal_block_height(font_size, content, letter_spacing=letter_spacing)

                if current_line_height + block_height > max_height and current_line_text:
                    line_text_list.append(current_line_text)
                    line_height_list.append(current_line_height)
                    current_line_text = part
                    current_line_height = block_height
                else:
                    current_line_text += part
                    current_line_height += block_height
            else:  # It's a vertical part, process character by character
                for cdpt in part:
                    if not cdpt:
                        continue
                    
                    char_offset_y = get_char_offset_y(font_size, cdpt, letter_spacing=letter_spacing)

                    should_wrap = current_line_height + char_offset_y > max_height

                    if should_wrap and current_line_text:
                        line_text_list.append(current_line_text)
                        line_height_list.append(current_line_height)
                        current_line_text = cdpt
                        current_line_height = char_offset_y
                    else:
                        current_line_text += cdpt
                        current_line_height += char_offset_y

        if current_line_text:
            line_text_list.append(current_line_text)
            line_height_list.append(current_line_height)

    if not line_text_list:
        line_text_list.append("")
        line_height_list.append(0)

    return line_text_list, line_height_list

def put_char_vertical(font_size: int, cdpt: str, pen_l: Tuple[int, int], canvas_text: np.ndarray, canvas_border: np.ndarray, border_size: int, config=None, line_width: int = 0, stroke_width: float = None, letter_spacing: float = 1.0):
    if cdpt == '＿':
        # For the placeholder, just advance the pen vertically and do nothing else.
        return _scale_advance(font_size, letter_spacing)

    pen = pen_l.copy()
    if line_width <= 0:
        line_width = font_size
    state = _get_vertical_char_draw_state(font_size, cdpt, line_width, letter_spacing=letter_spacing)
    bitmap_char = state['bitmap']
    char_offset_y = int(state['advance_y'])
    if bitmap_char is None:
        return char_offset_y
    line_start_x = pen[0] - line_width
    char_place_x = line_start_x + int(state['x'])
    char_place_y = pen[1] + int(state['y'])
    bitmap_border = None
    if border_size > 0:
        stroke_ratio = _resolve_stroke_ratio(config, stroke_width)
        bitmap_border = _get_vertical_border_bitmap(state['translated'], font_size, stroke_ratio, state['rot_degree'])
    _paste_glyph_bitmaps(canvas_text, canvas_border, bitmap_char, char_place_x, char_place_y, bitmap_border)
    return char_offset_y  

def put_text_vertical(font_size: int, text: str, h: int, alignment: str, fg: Tuple[int, int, int], bg: Optional[Tuple[int, int, int]], line_spacing: int, config=None, region_count: int = 1, stroke_width: float = None, letter_spacing: float = 1.0):
    text = compact_special_symbols(text)
    # 在竖排文本中，将省略号替换为单个竖排省略号符号（两个小点竖排）
    text = text.replace('…', '︙')
    if not text:
        return

    stroke_ratio = _resolve_stroke_ratio(config, stroke_width)
    bg_size = int(max(font_size * stroke_ratio, 1)) if bg is not None else 0
    # line_spacing 是基本间距的倍率
    # 竖排基本间距: 0.2
    spacing_x = int(font_size * 0.2 * (line_spacing or 1.0))

    # 固定为大高度以禁用自动换行（仅由显式换行符控制分段）
    effective_max_height = 99999
    logger.debug(f"[VERTICAL DEBUG] effective_max_height={effective_max_height}")

    # Use original font size for line breaking calculation
    line_text_list, line_height_list = calc_vertical(font_size, text, effective_max_height, config=config, letter_spacing=letter_spacing)
    if not line_height_list:
        return

    block_surface_cache = {}
    line_layouts = [
        _build_vertical_line_layout(
            font_size,
            line_text,
            bg_size,
            stroke_ratio,
            letter_spacing,
            block_surface_cache,
        )
        for line_text in line_text_list
    ]
    line_widths = [layout['width'] for layout in line_layouts]
    max_render_height = max((layout['height'] for layout in line_layouts), default=0)

    content_width = sum(line_widths) + spacing_x * max(0, len(line_widths) - 1)
    canvas_x = content_width + (font_size + bg_size) * 2
    canvas_y = max_render_height + (font_size + bg_size) * 2

    canvas_text = np.zeros((canvas_y, canvas_x), dtype=np.uint8)
    canvas_border = canvas_text.copy()
    content_left = font_size + bg_size
    current_edge = content_left + content_width
    column_layouts = []
    for line_width in line_widths:
        center_x = current_edge - line_width / 2.0
        column_layouts.append({
            'width': line_width,
            'center_x': center_x,
            'right_edge': current_edge,
        })
        current_edge -= line_width + spacing_x

    for line_idx, line_text in enumerate(line_text_list):
        layout = line_layouts[line_idx]
        line_width = layout['width']
        column_layout = column_layouts[line_idx]
        line_right_edge = int(round(column_layout['right_edge']))
        line_origin_y = font_size + bg_size
        render_height = layout['height']
        min_y = layout['min_y']
        if alignment == 'center':
            line_origin_y += round((max_render_height - render_height) / 2.0) - min_y
        elif alignment == 'right': # In vertical, right means bottom
            line_origin_y += max_render_height - render_height - min_y
        else:
            line_origin_y += -min_y

        line_start_x = int(round(column_layout['center_x'] - line_width / 2.0))
        for item in layout['items']:
            if item['kind'] == 'block':
                surface = item['surface']
                rh = item['height']
                rw = item['width']
                paste_x = line_start_x + round((line_width - rw) / 2.0)
                paste_y = line_origin_y + item['cursor_y']
                clamped_pos = _clamp_surface_origin(canvas_text.shape, paste_x, paste_y, rw, rh)
                if clamped_pos is None:
                    logger.warning(f"Text block too large for canvas, skipping. Size: {rw}x{rh}, Canvas: {canvas_text.shape[1]}x{canvas_text.shape[0]}")
                    continue
                paste_x, paste_y = clamped_pos

                target_text_roi = canvas_text[paste_y:paste_y+rh, paste_x:paste_x+rw]
                canvas_text[paste_y:paste_y+rh, paste_x:paste_x+rw] = np.maximum(target_text_roi, surface['text'])

                target_border_roi = canvas_border[paste_y:paste_y+rh, paste_x:paste_x+rw]
                canvas_border[paste_y:paste_y+rh, paste_x:paste_x+rw] = np.maximum(target_border_roi, surface['border'])
                continue

            if item['kind'] != 'char' or item['bitmap'] is None:
                continue

            bitmap_border = None
            if bg_size > 0:
                bitmap_border = _get_vertical_border_bitmap(item['translated'], font_size, stroke_ratio, item['rot_degree'])
            char_place_x = line_start_x + int(item['x'])
            char_place_y = line_origin_y + item['cursor_y'] + int(item['y'])
            _paste_glyph_bitmaps(canvas_text, canvas_border, item['bitmap'], char_place_x, char_place_y, bitmap_border)

    canvas_border = np.clip(canvas_border, 0, 255)
    line_box = add_color(canvas_text, fg, canvas_border, bg)
    combined_canvas = cv2.add(canvas_text, canvas_border)
    x, y, w, h = cv2.boundingRect(combined_canvas)

    if w == 0 or h == 0:
        logger.warning(f"[RENDER SKIPPED] Vertical text rendered with zero width or height. Width: {w}, Height: {h}, Text: {text[:50]}...")
        return None

    result = line_box[y:y+h, x:x+w]

    return result

_hyphenator_cache = {}

def select_hyphenator(lang: str):
    # 处理空字符串或None的情况，使用英文作为默认值
    if not lang or not lang.strip():
        lang = 'en_US'
    
    lang = standardize_tag(lang)
    if lang not in HYPHENATOR_LANGUAGES:
        for avail_lang in reversed(HYPHENATOR_LANGUAGES):
            if avail_lang.startswith(lang):
                lang = avail_lang
                break
        else:
            return None
    
    if lang in _hyphenator_cache:
        return _hyphenator_cache[lang]
    
    try:
        h = Hyphenator(lang)
        _hyphenator_cache[lang] = h
        return h
    except Exception:
        _hyphenator_cache[lang] = None
        return None

def get_char_offset_x(font_size: int, cdpt: str, letter_spacing: float = 1.0):
    if cdpt == '＿':
        # Return the width of a full-width space for the placeholder
        return get_char_offset_x(font_size, '　', letter_spacing=letter_spacing)
    return _measure_horizontal_text_width(cdpt, font_size, letter_spacing=letter_spacing)

def get_string_width(font_size: int, text: str, letter_spacing: float = 1.0):
    return _measure_horizontal_text_width(text, font_size, letter_spacing=letter_spacing)

def get_char_offset_y(font_size: int, cdpt: str, letter_spacing: float = 1.0):
    """获取单个字符的竖排高度（像素）"""
    if cdpt == '＿':
        return get_char_offset_y(font_size, '　', letter_spacing=letter_spacing)

    cdpt_trans, _ = CJK_Compatibility_Forms_translate(cdpt, 1)
    slot = get_char_glyph(cdpt_trans, font_size, 1)
    return _resolve_vertical_char_offset(slot, cdpt_trans, font_size, letter_spacing=letter_spacing)

def get_string_height(font_size: int, text: str, letter_spacing: float = 1.0):
    """获取字符串的竖排总高度（像素），考虑<H>横排块"""
    # 处理 BR 标记（不换行时当作连续文本）
    text_clean = re.sub(r'\s*(\[BR\]|<br>|【BR】)\s*', '', text, flags=re.IGNORECASE)

    total_height = 0

    # 分割 <H> 块
    parts = re.split(r'(<H>.*?</H>)', text_clean, flags=re.IGNORECASE | re.DOTALL)

    for part in parts:
        if not part:
            continue

        is_horizontal_block = part.lower().startswith('<h>') and part.lower().endswith('</h>')

        if is_horizontal_block:
            content = part[3:-4]
            if content:
                # 用精确的横排块高度计算
                total_height += calc_horizontal_block_height(font_size, content, letter_spacing=letter_spacing)
        else:
            # 普通竖排字符
            total_height += sum([get_char_offset_y(font_size, c, letter_spacing=letter_spacing) for c in part])

    return total_height

def calc_horizontal_cjk(font_size: int, text: str, max_width: int, letter_spacing: float = 1.0) -> Tuple[List[str], List[int]]:
    """
    Line breaking logic for CJK languages with punctuation rules.
    Handles forced newlines (\n) and invisible placeholders (＿).
    """
    # 统一处理所有类型的AI换行符
    text = re.sub(r'\s*(\[BR\]|<br>|【BR】)\s*', '\n', text, flags=re.IGNORECASE)

    lines = []
    no_start_chars = "》，。．」』】）！；：？"
    no_end_chars = "《「『【（"

    paragraphs = text.split('\n')

    for para_idx, paragraph in enumerate(paragraphs):
        if not paragraph:
            lines.append(("", 0))
            continue

        current_line = ""
        current_width = 0
        for char_idx, char in enumerate(paragraph):
            char_width = get_char_offset_x(font_size, char, letter_spacing=letter_spacing)

            if current_width + char_width > max_width and current_line:
                if current_line and current_line[-1] in no_end_chars:
                    last_char = current_line[-1]
                    current_line = current_line[:-1]
                    lines.append((current_line, get_string_width(font_size, current_line, letter_spacing=letter_spacing)))
                    current_line = last_char + char
                else:
                    lines.append((current_line, current_width))
                    current_line = char
                current_width = get_string_width(font_size, current_line, letter_spacing=letter_spacing)
            elif not current_line and char in no_start_chars:
                if lines:
                    prev_line_text, prev_line_width = lines[-1]
                    lines[-1] = (prev_line_text + char, prev_line_width + char_width)
                else:
                    current_line += char
                    current_width += char_width
            else:
                current_line += char
                current_width += char_width

        if current_line:
            lines.append((current_line, current_width))

    line_text_list = [line[0] for line in lines]
    line_width_list = [line[1] for line in lines]

    return line_text_list, line_width_list

def calc_horizontal(font_size: int, text: str, max_width: int, max_height: int, language: str = 'en_US', hyphenate: bool = True, letter_spacing: float = 1.0) -> Tuple[List[str], List[int]]:

    # 统一处理所有类型的AI换行符
    text = re.sub(r'\s*(\[BR\]|<br>|【BR】)\s*', '\n', text, flags=re.IGNORECASE)

    max_width = max(max_width, 2 * font_size)

    whitespace_offset_x = get_char_offset_x(font_size, ' ', letter_spacing=letter_spacing)
    hyphen_offset_x = get_char_offset_x(font_size, '-', letter_spacing=letter_spacing)

    # 先按换行符分割段落，然后对每段分割单词
    # 使用特殊标记来保留换行位置
    paragraphs = text.split('\n')
    words = []
    newline_positions = set()  # 记录哪些位置是段落结束（需要强制换行）

    for para_idx, paragraph in enumerate(paragraphs):
        if paragraph.strip():  # 非空段落
            para_words = re.split(r'[ \t]+', paragraph)  # 只按空格和制表符分割，不包括 \n
            words.extend(para_words)
            if para_idx < len(paragraphs) - 1:  # 不是最后一段
                newline_positions.add(len(words) - 1)  # 标记这个单词后面需要换行
        elif para_idx < len(paragraphs) - 1:  # 空段落但不是最后一个
            # 空行也需要保留
            words.append('')
            newline_positions.add(len(words) - 1)

    # 如果没有单词，返回空结果
    if not words:
        return [], []

    word_widths = []
    for i, word in enumerate(words):
        width = get_string_width(font_size, word, letter_spacing=letter_spacing)
        word_widths.append(width)

    while True:
        max_lines = max_height // font_size + 1
        expected_size = sum(word_widths) + max((len(word_widths) - 1) * whitespace_offset_x - (max_lines - 1) * hyphen_offset_x, 0)
        max_size = max_width * max_lines

        if max_size < expected_size:
            multiplier = np.sqrt(expected_size / max_size)
            max_width *= max(multiplier, 1.05)
            max_height *= multiplier
        else:
            break

    syllables = []
    hyphenator = select_hyphenator(language)

    for i, word in enumerate(words):
        new_syls = []
        if hyphenator and len(word) <= 100:
            try:
                new_syls = hyphenator.syllables(word)
            except Exception:
                new_syls = []

        if len(new_syls) == 0:
            if len(word) <= 3:
                new_syls = [word]
            else:
                new_syls = list(word)

        normalized_syls = []
        for syl in new_syls:
            syl_width = get_string_width(font_size, syl, letter_spacing=letter_spacing)
            if syl_width > max_width:
                normalized_syls.extend(list(syl))
            else:
                normalized_syls.append(syl)
        syllables.append(normalized_syls)

    line_words_list = []
    line_width_list = []
    hyphenation_idx_list = []
    line_words = []
    line_width = 0
    hyphenation_idx = 0

    def break_line():
        nonlocal line_words, line_width, hyphenation_idx
        line_words_list.append(line_words)
        line_width_list.append(line_width)
        hyphenation_idx_list.append(hyphenation_idx)
        line_words = []
        line_width = 0
        hyphenation_idx = 0

    def get_present_syllables_range(line_idx, word_pos):
        while word_pos < 0:
            word_pos += len(line_words_list[line_idx])
        word_idx = line_words_list[line_idx][word_pos]
        syl_start_idx = 0
        syl_end_idx = len(syllables[word_idx])
        if line_idx > 0 and word_pos == 0 and line_words_list[line_idx - 1][-1] == word_idx:
            syl_start_idx = hyphenation_idx_list[line_idx - 1]
        if line_idx < len(line_words_list) - 1 and word_pos == len(line_words_list[line_idx]) - 1 and line_words_list[line_idx + 1][0] == word_idx:
            syl_end_idx = hyphenation_idx_list[line_idx]
        return syl_start_idx, syl_end_idx

    def get_present_syllables(line_idx, word_pos):
        syl_start_idx, syl_end_idx = get_present_syllables_range(line_idx, word_pos)
        return syllables[line_words_list[line_idx][word_pos]][syl_start_idx:syl_end_idx]

    i = 0
    while True:
        if i >= len(words):
            if line_width > 0:
                break_line()
            break

        current_width = whitespace_offset_x if line_width > 0 else 0

        if line_width + current_width + word_widths[i] <= max_width + hyphen_offset_x:
            line_words.append(i)
            line_width += current_width + word_widths[i]
            i += 1
            # 检查是否需要强制换行（AI 断句）
            if (i - 1) in newline_positions:
                break_line()
        elif word_widths[i] > max_width:
            j = 0
            hyphenation_idx = 0
            while j < len(syllables[i]):
                syl = syllables[i][j]
                syl_width = get_string_width(font_size, syl, letter_spacing=letter_spacing)

                if line_width + current_width + syl_width <= max_width:
                    current_width += syl_width
                    j += 1
                    hyphenation_idx = j
                else:
                    if hyphenation_idx > 0:
                        line_words.append(i)
                        line_width += current_width
                    current_width = 0
                    break_line()
            line_words.append(i)
            line_width += current_width
            i += 1
            # 检查是否需要强制换行（AI 断句）
            if (i - 1) in newline_positions:
                break_line()
        else:
            if hyphenate:
                break_line()
            else:
                line_words.append(i)
                line_width += current_width + word_widths[i]
                i += 1
                if (i - 1) in newline_positions:
                    break_line()


    # 连字符优化阶段
    if hyphenate and len(line_words_list) > max_lines:
        line_idx = 0
        while line_idx < len(line_words_list) - 1:
            line_words1 = line_words_list[line_idx]
            line_words2 = line_words_list[line_idx + 1]
            left_space = max_width - line_width_list[line_idx]
            first_word = True
            while len(line_words2) != 0:
                word_idx = line_words2[0]
                if first_word and word_idx == line_words1[-1]:
                    syl_start_idx = hyphenation_idx_list[line_idx]
                    if line_idx < len(line_width_list) - 2 and word_idx == line_words_list[line_idx + 2][0]:
                        syl_end_idx = hyphenation_idx_list[line_idx + 1]
                    else:
                        syl_end_idx = len(syllables[word_idx])
                else:
                    left_space -= whitespace_offset_x
                    syl_start_idx = 0
                    syl_end_idx = len(syllables[word_idx]) if len(line_words2) > 1 else hyphenation_idx_list[line_idx + 1]
                first_word = False
                current_width = 0
                for i in range(syl_start_idx, syl_end_idx):
                    syl = syllables[word_idx][i]
                    syl_width = get_string_width(font_size, syl, letter_spacing=letter_spacing)
                    if left_space > current_width + syl_width:
                        current_width += syl_width
                    else:
                        if current_width > 0:
                            left_space -= current_width
                            line_width_list[line_idx] = max_width - left_space
                            hyphenation_idx_list[line_idx] = i
                            line_words1.append(word_idx)
                        break
                else:
                    left_space -= current_width
                    line_width_list[line_idx] = max_width - left_space
                    line_words1.append(word_idx)
                    line_words2.pop(0)
                    continue
                break
            if len(line_words2) == 0:
                line_words_list.pop(line_idx + 1)
                line_width_list.pop(line_idx + 1)
                hyphenation_idx_list.pop(line_idx)
            else:
                line_idx += 1

    # 行合并优化阶段
    line_idx = 0
    while line_idx < len(line_words_list) - 1:
        line_words1 = line_words_list[line_idx]
        line_words2 = line_words_list[line_idx + 1]
        merged_word_idx = -1
        if line_words1[-1] == line_words2[0]:
            word1_text = ''.join(get_present_syllables(line_idx, -1))
            word2_text = ''.join(get_present_syllables(line_idx + 1, 0))
            word1_width = get_string_width(font_size, word1_text, letter_spacing=letter_spacing)
            word2_width = get_string_width(font_size, word2_text, letter_spacing=letter_spacing)
            if len(word2_text) == 1 or word2_width < font_size:
                merged_word_idx = line_words1[-1]
                line_words2.pop(0)
                line_width_list[line_idx] += word2_width
                line_width_list[line_idx + 1] -= word2_width + whitespace_offset_x
            elif len(word1_text) == 1 or word1_width < font_size:
                merged_word_idx = line_words1[-1]
                line_words1.pop(-1)
                line_width_list[line_idx] -= word1_width + whitespace_offset_x
                line_width_list[line_idx + 1] += word1_width
        if len(line_words1) == 0:
            line_words_list.pop(line_idx)
            line_width_list.pop(line_idx)
            hyphenation_idx_list.pop(line_idx)
        elif len(line_words2) == 0:
            line_words_list.pop(line_idx + 1)
            line_width_list.pop(line_idx + 1)
            hyphenation_idx_list.pop(line_idx)
        elif line_idx >= len(line_words_list) - 1 or line_words_list[line_idx + 1] != merged_word_idx:
            line_idx += 1

    use_hyphen_chars = hyphenate and hyphenator and max_width > 1.5 * font_size and len(words) > 1

    line_text_list = []
    for i, line in enumerate(line_words_list):
        line_text = ''
        for j, word_idx in enumerate(line):
            syl_start_idx, syl_end_idx = get_present_syllables_range(i, j)
            current_syllables = syllables[word_idx][syl_start_idx:syl_end_idx]
            line_text += ''.join(current_syllables)
            if len(line_text) == 0:
                continue
            if j == 0 and i > 0 and len(line_text_list[-1]) > 0 and line_text_list[-1][-1] == '-' and line_text[0] == '-':
                line_text = line_text[1:]
                line_width_list[i] -= hyphen_offset_x
            if j < len(line) - 1 and len(line_text) > 0:
                line_text += ' '
            elif use_hyphen_chars and syl_end_idx != len(syllables[word_idx]) and len(words[word_idx]) > 3 and line_text[-1] != '-' and not (syl_end_idx < len(syllables[word_idx]) and not re.search(r'\w', syllables[word_idx][syl_end_idx][0])):
                line_text += '-'
                line_width_list[i] += hyphen_offset_x
        line_width_list[i] = get_string_width(font_size, line_text, letter_spacing=letter_spacing)
        line_text_list.append(line_text)

    return line_text_list, line_width_list

def put_char_horizontal(font_size: int, cdpt: str, pen_l: Tuple[int, int], canvas_text: np.ndarray, canvas_border: np.ndarray, border_size: int, config=None, stroke_width: float = None, letter_spacing: float = 1.0):
    if cdpt == '＿':
        # For the placeholder, just advance the pen and do nothing else.
        return get_char_offset_x(font_size, '＿', letter_spacing=letter_spacing)

    cdpt, _ = CJK_Compatibility_Forms_translate(cdpt, 0)
    char_offset_x = get_char_offset_x(font_size, cdpt, letter_spacing=letter_spacing)
    stroke_ratio = _resolve_stroke_ratio(config, stroke_width)
    surface = _render_horizontal_line_surface(
        cdpt,
        font_size,
        border_size,
        stroke_ratio=stroke_ratio,
        reversed_direction=False,
        letter_spacing=letter_spacing,
    )
    if surface is None:
        return char_offset_x
    pen = list(pen_l)
    paste_x = pen[0] + surface['left_rel']
    paste_y = pen[1] + surface['top_rel']
    _paste_surface(canvas_text, canvas_border, surface, paste_x, paste_y)
    return char_offset_x

def is_cjk_lang(lang: str):
    lang = lang.lower()
    # Check for common language codes for Chinese, Japanese, Korean
    return lang in ['chs', 'cht', 'jpn', 'kor', 'zh', 'ja', 'ko']

def put_text_horizontal(font_size: int, text: str, width: int, height: int, alignment: str,
                        reversed_direction: bool, fg: Tuple[int, int, int], bg: Tuple[int, int, int],
                        lang: str = 'en_US', hyphenate: bool = True, line_spacing: int = 0, config=None, region_count: int = 1, stroke_width: float = None, letter_spacing: float = 1.0):
    text = compact_special_symbols(text)
    if not text :
        logger.warning("[RENDER SKIPPED] Horizontal text is empty after processing")
        return

    layout_mode = 'default'
    if config:
        layout_mode = config.render.layout_mode

    stroke_ratio = _resolve_stroke_ratio(config, stroke_width)

    # 简化逻辑：统一处理BR标记，有BR就按它换行，没有就不换行
    text = re.sub(r'\s*(\[BR\]|<br>|【BR】)\s*', '\n', text, flags=re.IGNORECASE)

    # 统一使用无限宽度：换行完全由BR/\n决定，不自动断行
    # 有BR时按BR换行，无BR时不换行（都是单行or多行由BR控制）
    width = 99999
    has_newline = '\n' in text
    logger.debug(f"[HORIZONTAL DEBUG] width=99999, has_newline={has_newline}")

    bg_size = int(max(font_size * stroke_ratio, 1)) if bg is not None else 0
    # line_spacing 是基本间距的倍率
    # 横排基准间距仍是 0.01，但大于 1 时按线性规则放大
    spacing_y = calc_horizontal_line_spacing_px(font_size, line_spacing)
    if layout_mode != 'default' and is_cjk_lang(lang):
        line_text_list, line_width_list = calc_horizontal_cjk(font_size, text, width, letter_spacing=letter_spacing)
    else:
        line_text_list, line_width_list = calc_horizontal(font_size, text, width, height, lang, hyphenate, letter_spacing=letter_spacing)

    line_surfaces = []
    line_visual_extents_x = []
    line_visual_widths = []
    line_frame_metrics = []
    logical_line_tops = []
    logical_cursor_y = 0.0
    min_ink_top = 0.0
    max_ink_bottom = 0.0
    for line_idx, line_text in enumerate(line_text_list):
        surface = _render_horizontal_line_surface(
            line_text,
            font_size,
            bg_size,
            stroke_ratio=stroke_ratio,
            reversed_direction=reversed_direction,
            letter_spacing=letter_spacing,
        )
        if surface is not None:
            metrics = {
                'ascent': surface['line_ascent'],
                'height': surface['line_height'],
                'descent': surface['line_descent'],
            }
        else:
            metrics = _get_horizontal_line_frame_metrics(line_text, font_size, letter_spacing=letter_spacing)
        line_surfaces.append(surface)
        line_frame_metrics.append(metrics)
        logical_line_tops.append(logical_cursor_y)
        if surface is not None:
            line_left = surface['left_rel']
            line_right = surface['right_rel']
            min_ink_top = min(min_ink_top, logical_cursor_y + surface['ink_top'])
            max_ink_bottom = max(max_ink_bottom, logical_cursor_y + surface['ink_bottom'])
        else:
            line_left, line_right = 0.0, 0.0
        line_visual_extents_x.append((line_left, line_right))
        line_visual_widths.append(max(0, line_right - line_left))
        logical_cursor_y += metrics['height']
        if line_idx < len(line_text_list) - 1:
            logical_cursor_y += spacing_y
    max_visual_width = max(line_visual_widths) if line_visual_widths else 0
    logical_total_height = logical_cursor_y
    extra_top = max(0.0, -min_ink_top)
    extra_bottom = max(0.0, max_ink_bottom - logical_total_height)

    canvas_w = int(math.ceil(max(max(line_width_list), max_visual_width) + (font_size + bg_size) * 2))
    canvas_h = int(math.ceil(logical_total_height + extra_top + extra_bottom + bg_size * 2))

    canvas_text = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    canvas_border = canvas_text.copy()
    pen_orig = [font_size + bg_size, bg_size + extra_top]

    if reversed_direction:
        pen_orig[0] = canvas_w - bg_size - 10

    for line_idx, line_text in enumerate(line_text_list):
        pen_line = pen_orig.copy()
        line_left, line_right = line_visual_extents_x[line_idx]
        line_visual_width = max(0, line_right - line_left)

        if not reversed_direction:
            slot_left = pen_orig[0]
            if alignment == 'center':
                target_left = slot_left + round((max_visual_width - line_visual_width) / 2.0)
            elif alignment == 'right':
                target_left = slot_left + (max_visual_width - line_visual_width)
            else:
                target_left = slot_left
            pen_line[0] = round(target_left - line_left)
        else:
            slot_right = pen_orig[0]
            slot_left = slot_right - max_visual_width
            if alignment == 'left':
                target_left = slot_left
            elif alignment == 'center':
                target_left = slot_left + round((max_visual_width - line_visual_width) / 2.0)
            else:
                target_left = slot_right - line_visual_width
            target_right = target_left + line_visual_width
            pen_line[0] = round(target_right - line_right)

        surface = line_surfaces[line_idx]
        if surface is not None:
            paste_x = pen_line[0] + surface['left_rel']
            baseline_y = pen_line[1] + logical_line_tops[line_idx] + line_frame_metrics[line_idx]['ascent']
            paste_y = baseline_y + surface['top_rel']
            _paste_surface(canvas_text, canvas_border, surface, paste_x, paste_y)

    canvas_border = np.clip(canvas_border, 0, 255)
    line_box = add_color(canvas_text, fg, canvas_border, bg)
    combined_canvas = cv2.add(canvas_text, canvas_border)
    x, y, w, h = cv2.boundingRect(combined_canvas)
    
    if w == 0 or h == 0:
        logger.warning(f"[RENDER SKIPPED] Horizontal text rendered with zero width or height. Width: {w}, Height: {h}, Text: {text[:50]}...")
        return None
    
    result = line_box[y:y+h, x:x+w]
    return result

