"""字体加载与选择。

* 自动加载 ``assets/fonts/`` 下的所有 ttf/otf（用户放进去即可生效）；
* 中文优先宋体系（书籍感），英文优先衬线体；
* 找不到时逐级回退到系统可用字体，保证任何机器都不会变成方框。
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase

import paths

log = logging.getLogger(__name__)

FONT_DIR = "assets/fonts"

# 中文候选（从「最想要」到「最保底」）
CN_CANDIDATES = (
    "Source Han Serif SC",
    "Noto Serif CJK SC",
    "思源宋体",
    "方正书宋简体",
    "STSong",
    "SimSun",
    "NSimSun",
    "FangSong",
    "KaiTi",
    "Microsoft YaHei",
    "微软雅黑",
)

# 英文候选
EN_CANDIDATES = (
    "EB Garamond",
    "Source Serif 4",
    "Georgia",
    "Cambria",
    "Palatino Linotype",
    "Book Antiqua",
    "Times New Roman",
    "Segoe UI",
)

_loaded = False
_bundled_families: list[str] = []


def load_bundled_fonts() -> list[str]:
    """把 assets/fonts 下的字体注册进 Qt 字体库，返回新增的字体族名。"""
    global _loaded, _bundled_families
    if _loaded:
        return list(_bundled_families)
    _loaded = True

    font_dir = paths.resource_path(FONT_DIR)
    if not font_dir.is_dir():
        return []

    families: list[str] = []
    for file in sorted(font_dir.iterdir()):
        if file.suffix.lower() not in (".ttf", ".otf", ".ttc"):
            continue
        font_id = QFontDatabase.addApplicationFont(str(file))
        if font_id < 0:
            log.warning("字体加载失败：%s", file.name)
            continue
        for fam in QFontDatabase.applicationFontFamilies(font_id):
            if fam not in families:
                families.append(fam)
    _bundled_families = families
    if families:
        log.info("已加载内置字体：%s", "、".join(families))
    return list(families)


def _available(family: str) -> bool:
    if not family:
        return False
    return family in QFontDatabase.families()


def pick_family(preferred: str, candidates: tuple[str, ...]) -> str:
    """按优先级挑一个系统里真实存在的字体族。"""
    load_bundled_fonts()
    order: list[str] = []
    if preferred:
        order.append(preferred)
    order.extend(_bundled_families)
    order.extend(candidates)
    for fam in order:
        if _available(fam):
            return fam
    return QFont().defaultFamily()


def cn_font(size: float, preferred: str = "", weight: QFont.Weight = QFont.Weight.Normal,
            letter_spacing: float = 0.0) -> QFont:
    font = QFont(pick_family(preferred, CN_CANDIDATES))
    font.setPixelSize(max(8, int(round(size))))
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return font


def en_font(size: float, preferred: str = "", italic: bool = False,
            letter_spacing: float = 0.0) -> QFont:
    font = QFont(pick_family(preferred, EN_CANDIDATES))
    font.setPixelSize(max(8, int(round(size))))
    font.setItalic(italic)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return font
