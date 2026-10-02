"""过场动画控制。

一次完整过场（默认 3 秒）分三段，与需求文档一致：

===========  ==========================================
0.0 ~ 1.0s   当前文字淡出          text_opacity 1 -> 0
1.0 ~ 2.0s   页面水平翻转          flip 0 -> 1（0.5 为立起来的瞬间）
2.0 ~ 3.0s   新文字淡入            text_opacity 0 -> 1
===========  ==========================================

控制器只负责「产生数值 + 在合适时机通知换内容」，
具体怎么画由 :mod:`wallpaper.wallpaper_window` 决定，
两者通过 ``valueChanged`` / ``swapRequested`` 信号解耦。
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Signal,
)


class TransitionController(QObject):
    """驱动淡出 → 翻页 → 淡入的动画状态机。"""

    valueChanged = Signal()      # 任一数值变化，窗口据此重绘
    swapRequested = Signal()     # 该换下一条语录了（翻页中点）
    finished = Signal()          # 整段过场结束

    #: 三段时长占比
    PHASE_RATIO = (0.34, 0.32, 0.34)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._text_opacity = 1.0
        self._flip = 0.0
        self._swapped = True
        self._page_turn = True

        self._fade_out = QPropertyAnimation(self, b"textOpacity", self)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)

        self._turn = QPropertyAnimation(self, b"flip", self)
        self._turn.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._turn.setStartValue(0.0)
        self._turn.setEndValue(1.0)
        self._turn.valueChanged.connect(self._on_turn_value)

        self._fade_in = QPropertyAnimation(self, b"textOpacity", self)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._group = QSequentialAnimationGroup(self)
        self._group.addAnimation(self._fade_out)
        self._group.addAnimation(self._turn)
        self._group.addAnimation(self._fade_in)
        self._group.finished.connect(self._on_finished)

        self.set_duration(3.0)

    # ------------------------------------------------------------ Qt 属性
    def _get_text_opacity(self) -> float:
        return self._text_opacity

    def _set_text_opacity(self, value: float) -> None:
        value = min(1.0, max(0.0, float(value)))
        if abs(value - self._text_opacity) < 1e-4:
            return
        self._text_opacity = value
        self.valueChanged.emit()

    def _get_flip(self) -> float:
        return self._flip

    def _set_flip(self, value: float) -> None:
        value = min(1.0, max(0.0, float(value)))
        if abs(value - self._flip) < 1e-4:
            return
        self._flip = value
        self.valueChanged.emit()

    textOpacity = Property(float, _get_text_opacity, _set_text_opacity)
    flip = Property(float, _get_flip, _set_flip)

    # ------------------------------------------------------------ 只读状态
    @property
    def text_opacity(self) -> float:
        return self._text_opacity

    @property
    def flip_progress(self) -> float:
        """0 ~ 1；0.5 表示页面正好立起（宽度压到 0）。"""
        return self._flip

    def is_running(self) -> bool:
        return self._group.state() == QSequentialAnimationGroup.State.Running

    def is_paused(self) -> bool:
        return self._group.state() == QSequentialAnimationGroup.State.Paused

    # ------------------------------------------------------------ 参数设置
    def set_duration(self, seconds: float) -> None:
        seconds = min(10.0, max(0.4, float(seconds)))
        total_ms = int(seconds * 1000)
        r1, r2, r3 = self.PHASE_RATIO
        self._fade_out.setDuration(int(total_ms * r1))
        self._turn.setDuration(int(total_ms * r2))
        self._fade_in.setDuration(int(total_ms * r3))

    def set_page_turn_enabled(self, enabled: bool) -> None:
        """关闭后只保留淡入淡出（翻页段压缩为极短的空转）。"""
        self._page_turn = bool(enabled)

    # ------------------------------------------------------------ 播放控制
    def start(self) -> None:
        """开始一次过场；若正在播放则先结束当前的。"""
        if self._group.state() != QSequentialAnimationGroup.State.Stopped:
            self._group.stop()
        self._swapped = False
        self._set_text_opacity(1.0)
        self._set_flip(0.0)
        if not self._page_turn:
            self._turn.setDuration(1)
        self._group.start()

    def stop(self) -> None:
        self._group.stop()
        self._request_swap()
        self._set_flip(0.0)
        self._set_text_opacity(1.0)

    def cancel(self) -> None:
        """取消过场且不提交尚未发生的语录切换，用于程序退出。"""
        self._group.stop()
        self._swapped = True
        self._set_flip(0.0)
        self._set_text_opacity(1.0)

    def pause(self) -> None:
        if self.is_running():
            self._group.pause()

    def resume(self) -> None:
        if self.is_paused():
            self._group.resume()

    # ------------------------------------------------------------ 内部回调
    def _on_turn_value(self, value: float) -> None:
        # 页面立起的瞬间换内容，视觉上就是「翻过去看到新的一页」
        if not self._swapped and float(value) >= 0.5:
            self._request_swap()

    def _request_swap(self) -> None:
        if not self._swapped:
            self._swapped = True
            self.swapRequested.emit()

    def _on_finished(self) -> None:
        self._request_swap()
        self._set_flip(0.0)
        self._set_text_opacity(1.0)
        self.finished.emit()


class PaperDrift(QObject):
    """纸张纹理的极缓慢漂移，让静止画面「活」一点点。

    用低频定时器 + 正弦位移，CPU 占用几乎可以忽略。
    """

    valueChanged = Signal()

    FPS = 12
    PERIOD_X = 97.0   # 秒
    PERIOD_Y = 61.0
    AMPLITUDE = 18.0  # 像素

    def __init__(self, parent: QObject | None = None) -> None:
        from PySide6.QtCore import QTimer

        super().__init__(parent)
        self._t = 0.0
        self._dx = 0.0
        self._dy = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / self.FPS))
        self._timer.timeout.connect(self._tick)

    @property
    def offset(self) -> tuple[float, float]:
        return self._dx, self._dy

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def set_fps(self, fps: int) -> None:
        """按屏幕像素量调整重绘频率，降低 4K 全屏合成压力。"""
        fps = min(30, max(1, int(fps)))
        if fps == self.FPS and self._timer.interval() == int(1000 / fps):
            return
        self.FPS = fps
        was_active = self._timer.isActive()
        self._timer.setInterval(max(1, int(1000 / fps)))
        if was_active:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        import math

        self._t += 1.0 / self.FPS
        self._dx = math.sin(self._t / self.PERIOD_X * 2 * math.pi) * self.AMPLITUDE
        self._dy = math.cos(self._t / self.PERIOD_Y * 2 * math.pi) * self.AMPLITUDE * 0.6
        self.valueChanged.emit()
