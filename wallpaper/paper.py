"""纸张背景生成。

优先读取 ``assets/paper_texture.jpg``；文件缺失时用 numpy 现场生成
（噪点 + 纤维 + 云斑），保证程序永远有一张像样的旧纸底。

生成结果按尺寸缓存，避免每帧重绘造成 CPU 占用。
"""

from __future__ import annotations

import logging
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRadialGradient,
)

import paths

log = logging.getLogger(__name__)

TEXTURE_REL = "assets/paper_texture.jpg"

# 纹理向外多画一圈，供缓慢漂移时取样，避免露边
DRIFT_MARGIN = 48


def _numpy_texture(width: int, height: int, base: QColor) -> QImage:
    """无贴图时的程序化纸纹。"""
    import numpy as np

    rng = np.random.default_rng(20260803)

    # 低频云斑：叠加几层不同尺度的随机噪声并做双线性放大
    field = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    for scale in (6, 14, 32, 80):
        h = max(2, height // scale)
        w = max(2, width // scale)
        small = rng.random((h, w), dtype=np.float32)
        ys = np.linspace(0, h - 1, height, dtype=np.float32)
        xs = np.linspace(0, w - 1, width, dtype=np.float32)
        y0 = np.floor(ys).astype(np.int32)
        x0 = np.floor(xs).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, h - 1)
        x1 = np.clip(x0 + 1, 0, w - 1)
        wy = (ys - y0)[:, None]
        wx = (xs - x0)[None, :]
        top = small[y0][:, x0] * (1 - wx) + small[y0][:, x1] * wx
        bottom = small[y1][:, x0] * (1 - wx) + small[y1][:, x1] * wx
        field += (top * (1 - wy) + bottom * wy) * amplitude
        amplitude *= 0.55

    field -= field.min()
    field /= max(1e-6, field.max())
    field = field * 2.0 - 1.0

    # 高频颗粒
    grain = rng.normal(0.0, 1.0, (height, width)).astype(np.float32)

    # 横向纤维
    fibre = np.sin(np.linspace(0, math.pi * 60, width, dtype=np.float32))[None, :]
    fibre = fibre * rng.normal(0.0, 1.0, (height, 1)).astype(np.float32)

    delta = field * 7.0 + grain * 3.2 + fibre * 1.6

    r = np.clip(base.red() + delta * 1.00, 0, 255)
    g = np.clip(base.green() + delta * 0.94, 0, 255)
    b = np.clip(base.blue() + delta * 0.82, 0, 255)

    rgb = np.dstack([r, g, b]).astype(np.uint8)
    rgba = np.dstack([rgb, np.full((height, width, 1), 255, dtype=np.uint8)])
    buffer = np.ascontiguousarray(rgba)

    image = QImage(buffer.data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return image.copy()  # 复制一份，脱离 numpy 缓冲区生命周期


def _load_texture_pixmap(size: QSize, base: QColor) -> QPixmap:
    """加载贴图并缩放到覆盖尺寸；失败则程序化生成。"""
    texture_file = paths.resource_path(TEXTURE_REL)
    if texture_file.is_file():
        pix = QPixmap(str(texture_file))
        if not pix.isNull():
            return pix.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
    try:
        return QPixmap.fromImage(_numpy_texture(size.width(), size.height(), base))
    except Exception as exc:  # numpy 缺失等极端情况
        log.warning("纸纹生成失败，改用纯色底：%s", exc)
        pix = QPixmap(size)
        pix.fill(base)
        return pix


class PaperBackground:
    """纸张背景绘制器（带尺寸缓存）。"""

    def __init__(self) -> None:
        self._pixmap: QPixmap | None = None
        self._key: tuple | None = None

    def pixmap(self, size: QSize, base_color: QColor) -> QPixmap:
        target = QSize(size.width() + DRIFT_MARGIN * 2, size.height() + DRIFT_MARGIN * 2)
        key = (target.width(), target.height(), base_color.rgb())
        if self._pixmap is not None and self._key == key:
            return self._pixmap

        canvas = QPixmap(target)
        canvas.fill(base_color)

        texture = _load_texture_pixmap(target, base_color)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # 贴图居中铺满
        x = (target.width() - texture.width()) // 2
        y = (target.height() - texture.height()) // 2
        painter.drawPixmap(x, y, texture)

        # 用基础色轻微回染，保证「米白旧纸」的统一色调
        tint = QColor(base_color)
        tint.setAlpha(70)
        painter.fillRect(canvas.rect(), tint)

        # 顶部到底部的极淡明暗，模拟纸张受光
        grad = QLinearGradient(0, 0, 0, target.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, 26))
        grad.setColorAt(0.55, QColor(255, 255, 255, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 18))
        painter.fillRect(canvas.rect(), grad)
        painter.end()

        self._pixmap = canvas
        self._key = key
        return canvas

    def invalidate(self) -> None:
        self._pixmap = None
        self._key = None


def draw_vignette(painter: QPainter, rect: QRectF, strength: float = 0.30) -> None:
    """四角压暗，让视线收拢到中间文字。"""
    if strength <= 0:
        return
    center = QPointF(rect.center())
    radius = math.hypot(rect.width(), rect.height()) * 0.62
    grad = QRadialGradient(center, radius)
    grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    grad.setColorAt(0.62, QColor(0, 0, 0, int(18 * strength / 0.30)))
    grad.setColorAt(1.0, QColor(60, 46, 30, int(120 * strength / 0.30)))
    painter.fillRect(rect, grad)


def draw_book_gutter(painter: QPainter, rect: QRectF, strength: float = 1.0) -> None:
    """在页面外侧画一点书脊/装订的暗部，强化「摊开的书」感觉。"""
    if strength <= 0:
        return
    w = rect.width()
    edge = w * 0.06

    left = QLinearGradient(rect.left(), 0, rect.left() + edge, 0)
    left.setColorAt(0.0, QColor(120, 100, 70, int(52 * strength)))
    left.setColorAt(1.0, QColor(120, 100, 70, 0))
    painter.fillRect(QRectF(rect.left(), rect.top(), edge, rect.height()), left)

    right = QLinearGradient(rect.right() - edge, 0, rect.right(), 0)
    right.setColorAt(0.0, QColor(120, 100, 70, 0))
    right.setColorAt(1.0, QColor(120, 100, 70, int(52 * strength)))
    painter.fillRect(QRectF(rect.right() - edge, rect.top(), edge, rect.height()), right)
