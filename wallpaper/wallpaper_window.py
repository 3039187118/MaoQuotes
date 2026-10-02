"""壁纸窗口：负责把一条语录画成「一页旧书」。

窗口本身不管切换逻辑，只暴露三个输入：

* :meth:`set_quote`      —— 当前显示哪条语录
* :meth:`set_transition` —— 文字透明度 / 翻页进度（由动画控制器推送）
* :meth:`set_drift`      —— 纸张纹理偏移

绘制顺序：纸底 → 书脊暗部 → 书页卡片（含翻页变换）→ 暗角。
"""

from __future__ import annotations

import math
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

import paths
from settings.config_manager import ConfigManager

from . import fonts as font_utils
from .paper import PaperBackground, draw_book_gutter, draw_vignette
from .quotes import Quote

SEAL_REL = "assets/seal.png"

_CN_DIGITS = "〇一二三四五六七八九"


def _cn_number(value: int) -> str:
    """把页码转成中文数字，纯粹为了书卷气（1 -> 一，23 -> 二十三）。"""
    if value <= 0:
        return "〇"
    if value < 10:
        return _CN_DIGITS[value]
    if value < 20:
        return "十" + (_CN_DIGITS[value % 10] if value % 10 else "")
    if value < 100:
        tens, ones = divmod(value, 10)
        return _CN_DIGITS[tens] + "十" + (_CN_DIGITS[ones] if ones else "")
    return str(value)


class WindowMode(Enum):
    """窗口形态。"""

    WINDOWED = "windowed"       # 普通窗口（第一阶段调试用）
    FULLSCREEN = "fullscreen"   # 全屏置底，但不嵌入桌面
    DESKTOP = "desktop"         # 嵌入 Explorer 桌面层（正式壁纸模式）


class _Layout:
    """一次排版的计算结果，随语录 / 尺寸 / 配置变化重算。"""

    __slots__ = (
        "key", "card", "cn_font", "en_font", "src_font", "page_font",
        "cn_rect", "en_rect", "rule_y", "src_cn_rect", "src_en_rect",
        "seal_rect", "page_rect", "cn_size",
    )


class WallpaperWindow(QWidget):
    """单个屏幕上的壁纸窗口。"""

    def __init__(self, config: ConfigManager, mode: WindowMode = WindowMode.WINDOWED,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._mode = mode

        self._quote: Quote | None = None
        self._page_index = 0
        self._page_total = 0

        self._text_opacity = 1.0
        self._flip = 0.0
        self._drift = (0.0, 0.0)

        self._paper = PaperBackground()
        self._seal: QPixmap | None = None
        self._layout: _Layout | None = None
        self._config_version = 0

        self.setObjectName("MaoWallpaperWindow")
        self.setWindowTitle("Mao Quotes Live Wallpaper")
        self._apply_window_flags()

    # ================================================================ 外部接口
    @property
    def mode(self) -> WindowMode:
        return self._mode

    def set_mode(self, mode: WindowMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._apply_window_flags()

    def set_quote(self, quote: Quote, index: int = 0, total: int = 0) -> None:
        self._quote = quote
        self._page_index = index
        self._page_total = total
        self._layout = None
        self.update()

    def set_transition(self, text_opacity: float, flip: float) -> None:
        self._text_opacity = text_opacity
        self._flip = flip
        self.update()

    def set_drift(self, dx: float, dy: float) -> None:
        self._drift = (dx, dy)
        self.update()

    def refresh_config(self) -> None:
        """配置变更后调用：丢弃缓存并重绘。"""
        self._config_version += 1
        self._paper.invalidate()
        self._layout = None
        self.update()

    # ================================================================ 窗口属性
    def _apply_window_flags(self) -> None:
        visible = self.isVisible()
        if self._mode is WindowMode.WINDOWED:
            flags = Qt.WindowType.Window
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        else:
            flags = (
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool                    # 不出现在任务栏 / Alt+Tab
                | Qt.WindowType.WindowStaysOnBottomHint  # 压在所有窗口之下
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus if self._mode is WindowMode.WINDOWED
            else Qt.FocusPolicy.NoFocus
        )
        if visible:
            self.show()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt 命名)
        self._layout = None
        super().resizeEvent(event)

    # ================================================================ 颜色工具
    def _color(self, key: str, alpha: int = 255) -> QColor:
        r, g, b = self._config.get(key)
        c = QColor(r, g, b)
        c.setAlpha(alpha)
        return c

    # ================================================================ 排版计算
    def _ensure_layout(self) -> _Layout | None:
        if self._quote is None:
            return None

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return None

        key = (w, h, self._quote.id, self._quote.cn, self._quote.en, self._config_version)
        if self._layout is not None and self._layout.key == key:
            return self._layout

        cfg = self._config
        show_cn = cfg.get("show_cn") and bool(self._quote.cn)
        show_en = cfg.get("show_en") and bool(self._quote.en)
        show_src = cfg.get("show_source")

        cn_size = min(150.0, max(20.0, h * float(cfg.get("cn_size_ratio"))))
        content_w = min(w * 0.70, cn_size * 15.0)

        # 中文：超过 3 行就自动缩字号，保证版心不被撑破
        cn_font = font_utils.cn_font(cn_size, cfg.get("font_cn"),
                                     letter_spacing=cn_size * 0.05)
        if show_cn:
            for _ in range(14):
                fm = QFontMetricsF(cn_font)
                rect = fm.boundingRect(
                    QRectF(0, 0, content_w, 1e5),
                    int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignHCenter),
                    self._quote.cn,
                )
                if rect.height() <= fm.lineSpacing() * 3 + 2:
                    break
                cn_size *= 0.92
                cn_font = font_utils.cn_font(cn_size, cfg.get("font_cn"),
                                             letter_spacing=cn_size * 0.05)

        en_size = cn_size * 0.345
        src_size = cn_size * 0.255
        page_size = cn_size * 0.22

        en_font = font_utils.en_font(en_size, cfg.get("font_en"),
                                     letter_spacing=en_size * 0.02)
        src_font = font_utils.cn_font(src_size, cfg.get("font_cn"),
                                      letter_spacing=src_size * 0.10)
        page_font = font_utils.cn_font(page_size, cfg.get("font_cn"),
                                       letter_spacing=page_size * 0.20)

        def block_height(font: QFont, text: str) -> float:
            fm = QFontMetricsF(font)
            r = fm.boundingRect(
                QRectF(0, 0, content_w, 1e5),
                int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignHCenter),
                text,
            )
            return max(fm.lineSpacing(), r.height())

        gap_cn_en = cn_size * 0.62
        gap_en_rule = cn_size * 0.85
        gap_rule_src = cn_size * 0.50

        total = 0.0
        cn_h = block_height(cn_font, self._quote.cn) if show_cn else 0.0
        en_h = block_height(en_font, self._quote.en) if show_en else 0.0
        src_cn_h = QFontMetricsF(src_font).lineSpacing() if show_src else 0.0
        src_en_h = QFontMetricsF(en_font).lineSpacing() * 0.62 if show_src else 0.0
        src_en_font = font_utils.en_font(src_size * 0.82, cfg.get("font_en"),
                                         letter_spacing=src_size * 0.06)
        if show_src:
            src_en_h = QFontMetricsF(src_en_font).lineSpacing()

        total += cn_h
        if show_cn and show_en:
            total += gap_cn_en
        total += en_h
        if show_src:
            total += gap_en_rule + gap_rule_src + src_cn_h + src_en_h * 1.15

        pad_x = cn_size * 1.55
        pad_y = cn_size * 1.35
        card_w = content_w + pad_x * 2
        card_h = total + pad_y * 2
        card_h = max(card_h, h * 0.32)

        cx = w / 2.0
        cy = h * 0.485  # 略高于几何中心，视觉更稳
        card = QRectF(cx - card_w / 2.0, cy - card_h / 2.0, card_w, card_h)

        # 逐块落位
        y = card.top() + (card.height() - total) / 2.0
        left = cx - content_w / 2.0

        lay = _Layout()
        lay.key = key
        lay.card = card
        lay.cn_size = cn_size
        lay.cn_font = cn_font
        lay.en_font = en_font
        lay.src_font = src_font
        lay.page_font = page_font

        lay.cn_rect = QRectF(left, y, content_w, cn_h)
        if show_cn:
            y += cn_h + (gap_cn_en if show_en else 0.0)
        lay.en_rect = QRectF(left, y, content_w, en_h)
        if show_en:
            y += en_h

        if show_src:
            y += gap_en_rule
            lay.rule_y = y
            y += gap_rule_src
            lay.src_cn_rect = QRectF(left, y, content_w, src_cn_h)
            y += src_cn_h
            lay.src_en_rect = QRectF(left, y, content_w, src_en_h * 1.15)
        else:
            lay.rule_y = 0.0
            lay.src_cn_rect = QRectF()
            lay.src_en_rect = QRectF()

        # 印章：右下角，压在版心外沿
        seal_size = cn_size * 1.45
        lay.seal_rect = QRectF(
            card.right() - pad_x * 0.55 - seal_size,
            card.bottom() - pad_y * 0.55 - seal_size,
            seal_size,
            seal_size,
        )

        # 页码：卡片底部居中
        lay.page_rect = QRectF(left, card.bottom() - pad_y * 0.72,
                               content_w, page_size * 2.0)

        # 英文出处单独用小一号的西文字体
        lay.en_font.setPixelSize(max(8, int(round(en_size))))
        self._src_en_font = src_en_font
        self._layout = lay
        return lay

    # ================================================================ 绘制
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        rect = QRectF(self.rect())

        self._draw_paper(painter, rect)
        draw_book_gutter(painter, rect)

        lay = self._ensure_layout()
        if lay is not None:
            self._draw_page_with_flip(painter, lay)

        draw_vignette(painter, rect)
        painter.end()

    # ------------------------------------------------------------ 纸底
    def _draw_paper(self, painter: QPainter, rect: QRectF) -> None:
        base = self._color("background_color")
        pixmap = self._paper.pixmap(self.size(), base)
        from .paper import DRIFT_MARGIN

        dx, dy = self._drift
        painter.drawPixmap(
            QPointF(-DRIFT_MARGIN + dx, -DRIFT_MARGIN + dy),
            pixmap,
        )

    # ------------------------------------------------------------ 翻页变换
    def _draw_page_with_flip(self, painter: QPainter, lay: _Layout) -> None:
        flip = self._flip
        if flip <= 1e-4:
            self._draw_page(painter, lay, shade=0.0)
            return

        angle = flip * math.pi
        cosv = math.cos(angle)
        scale_x = max(abs(cosv), 0.012)
        scale_y = 1.0 - 0.085 * (1.0 - abs(cosv))   # 轻微的透视压缩
        center = lay.card.center()

        # 翻起来时在纸面上投一道柔和阴影
        self._draw_flip_shadow(painter, lay, 1.0 - abs(cosv), cosv)

        painter.save()
        painter.translate(center)
        painter.scale(scale_x, scale_y)
        painter.translate(-center)
        self._draw_page(painter, lay, shade=1.0 - abs(cosv))
        painter.restore()

    def _draw_flip_shadow(self, painter: QPainter, lay: _Layout,
                          amount: float, cosv: float) -> None:
        if amount <= 0.02:
            return
        card = lay.card
        width = card.width() * 0.55 * amount
        if cosv >= 0:
            band = QRectF(card.center().x(), card.top(), width, card.height())
            grad = QLinearGradient(band.left(), 0, band.right(), 0)
            grad.setColorAt(0.0, QColor(90, 72, 48, int(70 * amount)))
            grad.setColorAt(1.0, QColor(90, 72, 48, 0))
        else:
            band = QRectF(card.center().x() - width, card.top(), width, card.height())
            grad = QLinearGradient(band.left(), 0, band.right(), 0)
            grad.setColorAt(0.0, QColor(90, 72, 48, 0))
            grad.setColorAt(1.0, QColor(90, 72, 48, int(70 * amount)))
        painter.fillRect(band, grad)

    # ------------------------------------------------------------ 页面内容
    def _draw_page(self, painter: QPainter, lay: _Layout, shade: float) -> None:
        cfg = self._config
        quote = self._quote
        if quote is None:
            return

        card = lay.card
        ink = self._color("text_color")
        seal_color = self._color("seal_color")

        # 页面本体：比底纸略亮一点，四边给一点点投影
        page_fill = self._color("background_color").lighter(103)
        page_fill.setAlpha(120)
        painter.fillRect(card, page_fill)

        edge = QLinearGradient(card.left(), card.top(), card.left(), card.bottom())
        edge.setColorAt(0.0, QColor(255, 255, 255, 40))
        edge.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(card, edge)

        # 正文（受淡入淡出控制）
        painter.save()
        painter.setOpacity(self._text_opacity)

        flags_center = int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignHCenter
                           | Qt.AlignmentFlag.AlignTop)

        if cfg.get("show_cn") and quote.cn:
            painter.setFont(lay.cn_font)
            painter.setPen(ink)
            painter.drawText(lay.cn_rect, flags_center, quote.cn)

        if cfg.get("show_en") and quote.en:
            en_ink = QColor(ink)
            en_ink.setAlpha(185)
            painter.setFont(lay.en_font)
            painter.setPen(en_ink)
            painter.drawText(lay.en_rect, flags_center, quote.en)

        if cfg.get("show_source"):
            # 细分隔线
            rule_w = lay.cn_rect.width() * 0.20
            rule_x = lay.cn_rect.center().x() - rule_w / 2.0
            rule_color = QColor(ink)
            rule_color.setAlpha(70)
            painter.fillRect(QRectF(rule_x, lay.rule_y, rule_w, 1.0), rule_color)

            src_ink = QColor(ink)
            src_ink.setAlpha(160)
            painter.setFont(lay.src_font)
            painter.setPen(src_ink)
            painter.drawText(lay.src_cn_rect, flags_center, f"——{quote.source_cn}")

            src_ink.setAlpha(125)
            painter.setFont(getattr(self, "_src_en_font", lay.en_font))
            painter.setPen(src_ink)
            painter.drawText(lay.src_en_rect, flags_center, quote.source_en)

        if cfg.get("show_page_number") and self._page_total:
            page_ink = QColor(seal_color)
            page_ink.setAlpha(120)
            painter.setFont(lay.page_font)
            painter.setPen(page_ink)
            painter.drawText(
                lay.page_rect,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                f"·  {_cn_number(self._page_index + 1)}  ·",
            )

        if cfg.get("show_seal"):
            self._draw_seal(painter, lay.seal_rect, seal_color)

        painter.restore()

        # 翻页时整页压暗
        if shade > 0.01:
            painter.fillRect(card, QColor(60, 48, 32, int(150 * shade)))

    # ------------------------------------------------------------ 印章
    def _draw_seal(self, painter: QPainter, rect: QRectF, color: QColor) -> None:
        if self._seal is None:
            seal_file = paths.resource_path(SEAL_REL)
            self._seal = QPixmap(str(seal_file)) if seal_file.is_file() else QPixmap()

        painter.save()
        painter.setOpacity(painter.opacity() * 0.82)
        if not self._seal.isNull():
            painter.drawPixmap(rect, self._seal, QRectF(self._seal.rect()))
        else:
            # 没有素材时手绘一个极简方印
            pen_w = max(1.5, rect.width() * 0.055)
            painter.setPen(QColor(color.red(), color.green(), color.blue(), 190))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inner = rect.adjusted(pen_w, pen_w, -pen_w, -pen_w)
            painter.drawRect(inner)
            font = font_utils.cn_font(rect.height() * 0.34)
            painter.setFont(font)
            painter.drawText(inner, int(Qt.AlignmentFlag.AlignCenter), "实事\n求是")
        painter.restore()

    # ================================================================ 交互
    def keyPressEvent(self, event) -> None:  # noqa: N802
        """仅调试窗口模式下生效。"""
        if self._mode is not WindowMode.WINDOWED:
            return super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Space):
            self.next_requested()
        elif key == Qt.Key.Key_Left:
            self.prev_requested()
        else:
            super().keyPressEvent(event)

    # 由控制器在构造后注入的回调（避免窗口反向依赖控制器）
    def next_requested(self) -> None:
        pass

    def prev_requested(self) -> None:
        pass
