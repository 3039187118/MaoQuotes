"""壁纸总控。

职责：
* 按显示器数量创建 / 销毁壁纸窗口，默认只在副屏显示；
* 驱动自动切换定时器与过场动画；
* 响应配置变更、语录文件热更新；
* Windows 下把窗口嵌入桌面层，并在 Explorer 重启后自动恢复。
"""

from __future__ import annotations

import logging
import math
import time

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QScreen

from settings.config_manager import ConfigManager

from . import desktop_embed
from .animation import PaperDrift, TransitionController
from .quotes import Quote, QuoteLibrary, QuoteRotator
from .system_wallpaper import SystemWallpaperBackend
from .wallpaper_window import WallpaperWindow, WindowMode

log = logging.getLogger(__name__)

WINDOWED_SIZE = (1280, 760)
QUOTE_WATCH_INTERVAL_MS = 5000
EMBED_WATCH_INTERVAL_MS = 1000
DISPLAY_WATCH_INTERVAL_MS = 2000
DISPLAY_CHANGE_DEBOUNCE_MS = 600


class WallpaperController(QObject):
    """把窗口、动画、语录、配置粘合在一起。"""

    quoteChanged = Signal(object)   # Quote
    pausedChanged = Signal(bool)

    def __init__(self, config: ConfigManager, mode: WindowMode = WindowMode.DESKTOP,
                 library: QuoteLibrary | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._mode = mode
        self._library = library or QuoteLibrary()
        self._rotator = QuoteRotator(self._library, config.get("play_mode"))

        self._windows: list[WallpaperWindow] = []
        self._embedded: dict[int, int] = {}   # hwnd -> WorkerW hwnd
        self._embedded_rects: dict[int, tuple[int, int, int, int]] = {}
        self._system_wallpaper: SystemWallpaperBackend | None = None
        self._desktop_strategy = "windows"
        self._monitor_layout: tuple[tuple[int, int, int, int], ...] = ()
        self._paused = False
        self._pending_direction = "next"
        self._interval_seconds = max(3, int(config.get("time_interval")))
        self._next_switch_at = 0.0

        # 过场动画
        self._transition = TransitionController(self)
        self._transition.set_duration(config.get("animation_duration"))
        self._transition.set_page_turn_enabled(config.get("page_turn_enabled"))
        self._transition.valueChanged.connect(self._on_transition_value)
        self._transition.swapRequested.connect(self._on_swap)
        self._transition.finished.connect(self._on_transition_finished)

        # 纸张漂移
        self._drift = PaperDrift(self)
        self._drift.valueChanged.connect(self._on_drift)

        # 自动切换
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)

        # 语录文件热更新
        self._watch = QTimer(self)
        self._watch.setInterval(QUOTE_WATCH_INTERVAL_MS)
        self._watch.timeout.connect(self._on_watch_quotes)

        # 桌面嵌入守护（Explorer 崩溃/重启后自动恢复）
        self._embed_watch = QTimer(self)
        self._embed_watch.setInterval(EMBED_WATCH_INTERVAL_MS)
        self._embed_watch.timeout.connect(self._on_embed_watch)

        # 显示器拓扑/分辨率守护。只在布局实际变化时处理，不周期性重建。
        self._display_watch = QTimer(self)
        self._display_watch.setInterval(DISPLAY_WATCH_INTERVAL_MS)
        self._display_watch.timeout.connect(self._on_display_watch)

        self._display_change_debounce = QTimer(self)
        self._display_change_debounce.setSingleShot(True)
        self._display_change_debounce.setInterval(DISPLAY_CHANGE_DEBOUNCE_MS)
        self._display_change_debounce.timeout.connect(self._on_display_watch)

        config.changed.connect(self._on_config_changed)

        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)

    # ================================================================ 生命周期
    @property
    def library(self) -> QuoteLibrary:
        return self._library

    @property
    def rotator(self) -> QuoteRotator:
        return self._rotator

    @property
    def paused(self) -> bool:
        return self._paused

    def current_quote(self) -> Quote:
        return self._rotator.current()

    def start(self) -> None:
        """创建窗口并开始播放。"""
        if self._mode is WindowMode.DESKTOP:
            self._monitor_layout = self._physical_monitor_layout()
            self._activate_desktop_strategy(initial=True)
            self._display_watch.start()
        else:
            self._build_windows()
            self._push_quote()
            for win in self._windows:
                win.show()
        self._restart_timer()
        if self._config.get("paper_drift") and self._windows:
            self._drift.start()
        self._watch.start()

    def shutdown(self) -> None:
        """退出前的清理。"""
        self._timer.stop()
        self._watch.stop()
        self._embed_watch.stop()
        self._display_watch.stop()
        self._display_change_debounce.stop()
        self._drift.stop()
        self._transition.cancel()
        self._dispose_windows()
        if self._system_wallpaper is not None:
            self._system_wallpaper.stop(restore=True)
            self._system_wallpaper = None
        desktop_embed.refresh_desktop()

    # ================================================================ 窗口管理
    def _physical_monitor_layout(self) -> tuple[tuple[int, int, int, int], ...]:
        monitors = desktop_embed.enum_physical_monitors()
        if monitors:
            return tuple(sorted(monitors, key=lambda rect: (rect[0], rect[1])))

        app = QGuiApplication.instance()
        if app is None:
            return ()
        return tuple(
            sorted(
                (
                    screen.geometry().x(),
                    screen.geometry().y(),
                    screen.geometry().width(),
                    screen.geometry().height(),
                )
                for screen in app.screens()
            )
        )

    def _dispose_windows(self) -> None:
        """隐藏后再摘除旧窗口，避免重配显示器时出现顶层闪现。"""
        for win in self._windows:
            win.hide()
            try:
                hwnd = int(win.winId())
                if desktop_embed.is_alive(hwnd):
                    desktop_embed.detach(hwnd)
            except RuntimeError:
                pass
            win.deleteLater()
        self._windows.clear()
        self._embedded.clear()
        self._embedded_rects.clear()

    def _activate_desktop_strategy(self, *, initial: bool = False) -> None:
        """单屏使用系统壁纸，双屏使用 WorkerW 动态窗口。"""
        if len(self._monitor_layout) == 1:
            self._desktop_strategy = "system"
            self._embed_watch.stop()
            self._dispose_windows()
            if self._system_wallpaper is None:
                self._system_wallpaper = SystemWallpaperBackend(self._config)
            _, _, width, height = self._monitor_layout[0]
            size = self._effective_size((width, height))
            if size != (width, height):
                log.info("渲染分辨率已手动覆盖：%dx%d（屏幕物理分辨率 %dx%d）",
                         size[0], size[1], width, height)
            self._system_wallpaper.start(size)
            self._push_quote()
            self._drift.stop()
            log.info("桌面策略：单屏系统壁纸（%dx%d）", size[0], size[1])
            return

        self._desktop_strategy = "workerw"
        if self._system_wallpaper is not None:
            self._system_wallpaper.stop(restore=True)
            self._system_wallpaper = None
        self._build_windows()
        self._push_quote()
        for win in self._windows:
            win.show()
        # 窗口显示后立即嵌入，不再暴露 120/200ms 的顶层窗口闪现。
        self._embed_all(force_spawn=not initial)
        self._embed_watch.start()
        if self._config.get("paper_drift") and not self._paused:
            self._configure_drift_rate()
            self._drift.start()
        log.info("桌面策略：双屏 WorkerW（physical=%d qt=%d windows=%d）",
                 len(self._monitor_layout),
                 len(QGuiApplication.instance().screens()
                     if QGuiApplication.instance() else []),
                 len(self._windows))

    def _configure_drift_rate(self) -> None:
        """按最大窗口像素数降低全屏重绘频率，4K 单帧不再高频刷新。"""
        if not self._windows:
            return
        max_pixels = max(max(1, win.width() * win.height()) for win in self._windows)
        if max_pixels >= 7_000_000:
            fps = 4
        elif max_pixels >= 3_000_000:
            fps = 6
        else:
            fps = 10
        self._drift.set_fps(fps)

    def _target_screens(self) -> list[QScreen]:
        app = QGuiApplication.instance()
        if app is None:
            return []
        screens = list(app.screens())
        if not screens:
            return []
        if self._mode is WindowMode.WINDOWED:
            return [screens[0]]
        # all_screens（默认开）覆盖所有显示器；关闭时保持旧行为：
        # 多屏只用副屏，把主屏留给用户自己的壁纸。
        if not self._config.get("all_screens") and len(screens) >= 2:
            primary = app.primaryScreen()
            return [s for s in screens if s is not primary]
        return screens

    # ------------------------------------------------------------ 渲染尺寸
    def _render_size_override(self) -> tuple[int, int] | None:
        """设置里手动指定的渲染分辨率；``None`` 表示跟随屏幕物理分辨率。"""
        return ConfigManager.parse_render_size(self._config.get("render_size"))

    def _effective_size(self, physical: tuple[int, int]) -> tuple[int, int]:
        """把「屏幕物理分辨率」换成实际要渲染的画布尺寸。"""
        return self._render_size_override() or physical

    def _build_windows(self) -> None:
        self._dispose_windows()

        for screen in self._target_screens():
            win = WallpaperWindow(self._config, self._mode)
            win.next_requested = lambda: self.next_quote()
            win.prev_requested = lambda: self.prev_quote()
            geo = screen.geometry()
            if self._mode is WindowMode.WINDOWED:
                win.resize(*WINDOWED_SIZE)
                win.move(geo.center().x() - WINDOWED_SIZE[0] // 2,
                         geo.center().y() - WINDOWED_SIZE[1] // 2)
            else:
                win.setScreen(screen)
                win.setGeometry(geo)
            self._windows.append(win)

        log.info("创建 %d 个壁纸窗口（共 %d 个显示器）",
                 len(self._windows), len(QGuiApplication.instance().screens()
                                          if QGuiApplication.instance() else []))

    def _embed_all(self, force_spawn: bool = False) -> None:
        """把每个壁纸窗口挂到 WorkerW 上。"""
        if self._mode is not WindowMode.DESKTOP or not desktop_embed.is_supported():
            return
        # WorkerW 可能刚被 Explorer 销毁。只有在确实没有可用容器时才
        # force spawn，避免正常运行期间反复创建孤儿 WorkerW。
        if force_spawn and not desktop_embed.find_worker_w_all():
            desktop_embed.spawn_worker_w(force=True)
        else:
            desktop_embed.spawn_worker_w()
        vx, vy = desktop_embed.virtual_screen_origin()
        vsw, vsh = desktop_embed.virtual_screen_size()
        log.info("虚拟桌面 原点=(%d,%d) 尺寸=(%d,%d)，共 %d 个窗口待嵌入",
                 vx, vy, vsw, vsh, len(self._windows))

        for win in self._windows:
            hwnd = int(win.winId())
            x, y, w, h = desktop_embed.window_rect(hwnd)
            if w <= 0 or h <= 0:
                geo = win.geometry()
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            target = desktop_embed.find_worker_w_for_rect(x, y, w, h)
            if not target:
                target = desktop_embed.find_worker_w_with_icons()
            if not target:
                target = desktop_embed.progman_handle()
            if not target:
                log.warning("窗口 0x%X 嵌入失败：找不到桌面容器", hwnd)
                continue
            if not desktop_embed.embed_to(hwnd, target):
                log.warning("窗口 0x%X SetParent 失败", hwnd)
                continue
            desktop_embed.move_physical(hwnd, x - vx, y - vy, w, h)
            self._embedded[hwnd] = target
            self._embedded_rects[hwnd] = (x, y, w, h)
            log.info("窗口 0x%X → WorkerW 0x%X | rect=(%d,%d,%d,%d)",
                     hwnd, target, x, y, w, h)

    def _on_screens_changed(self, *_args) -> None:
        """合并系统连续发出的 screenAdded/screenRemoved 信号。"""
        self._display_change_debounce.start()

    def _on_display_watch(self) -> None:
        if self._mode is not WindowMode.DESKTOP:
            return
        layout = self._physical_monitor_layout()
        if not layout or layout == self._monitor_layout:
            return
        old_layout = self._monitor_layout
        self._monitor_layout = layout
        log.info("显示器布局变化：%s → %s", old_layout, layout)
        self._activate_desktop_strategy()

    def _on_embed_watch(self) -> None:
        """守护嵌入状态，不销毁可见窗口。

        Explorer 重建 WorkerW 时，旧实现会重建并重新 show 所有壁纸窗口，
        这会造成一次明显的全屏闪动。现在只恢复父窗口关系，复用现有窗口。
        """
        if self._mode is not WindowMode.DESKTOP or not desktop_embed.is_supported():
            return

        for win in self._windows:
            hwnd = int(win.winId())
            if not desktop_embed.is_alive(hwnd):
                self._rebuild_after_embed_loss(hwnd)
                return
            current_parent = desktop_embed.get_parent(hwnd)
            cached = self._embedded.get(hwnd)
            if (not cached or current_parent != cached
                    or not desktop_embed.is_alive(cached)):
                self._recover_embedding()
                return

    def _rebuild_after_embed_loss(self, hwnd: int) -> None:
        """WorkerW 销毁并连带销毁壁纸 HWND 后，重建可见窗口。"""
        log.warning("壁纸窗口 0x%X 已失效，重建窗口并恢复桌面嵌入", hwnd)
        self._build_windows()
        self._push_quote()
        for win in self._windows:
            win.show()
        # 目标尺寸来自显示器布局，不再需要延迟等待 Qt 几何稳定。
        self._embed_all(force_spawn=True)

    def _recover_embedding(self) -> None:
        """在 WorkerW 变化后恢复现有窗口的父子关系。

        这里只使用轻量的 ``SetParent``，不改窗口样式、不 hide/show、也不
        重建 QWidget。只有在当前桌面确实没有可用 WorkerW 时才 force spawn。
        """
        vx, vy = desktop_embed.virtual_screen_origin()
        spawn_attempted = False
        recovered = 0

        for win in self._windows:
            hwnd = int(win.winId())
            current_parent = desktop_embed.get_parent(hwnd)
            rect = self._embedded_rects.get(hwnd)
            if rect is None:
                rect = desktop_embed.window_rect(hwnd)
            x, y, w, h = rect
            if w <= 0 or h <= 0:
                geo = win.geometry()
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

            target = desktop_embed.find_worker_w_for_rect(x, y, w, h)
            if not target:
                target = desktop_embed.find_worker_w_with_icons()
            if not target and not spawn_attempted:
                # WorkerW 可能刚被 Explorer 删除，显式请求生成替代容器；
                # 每次恢复最多请求一次，避免制造多个孤儿 WorkerW。
                desktop_embed.spawn_worker_w(force=True)
                spawn_attempted = True
                target = desktop_embed.find_worker_w_for_rect(x, y, w, h)
                if not target:
                    target = desktop_embed.find_worker_w_with_icons()
            if not target:
                target = desktop_embed.progman_handle()

            if not target:
                log.warning("窗口 0x%X 恢复嵌入失败：找不到桌面容器", hwnd)
                continue

            if current_parent != target:
                if not desktop_embed.reparent_only(hwnd, target):
                    log.warning("窗口 0x%X 恢复 SetParent 失败", hwnd)
                    continue
                desktop_embed.move_physical(hwnd, x - vx, y - vy, w, h)

            self._embedded[hwnd] = target
            self._embedded_rects[hwnd] = (x, y, w, h)
            recovered += 1

        if recovered:
            log.info("已复用现有壁纸窗口恢复桌面嵌入（%d/%d）",
                     recovered, len(self._windows))

    # ================================================================ 切换逻辑
    def _restart_timer(self) -> None:
        """从当前时刻开始一个完整、不会提前触发的切换周期。"""
        self._timer.stop()
        if self._paused:
            return
        self._interval_seconds = max(3, int(self._config.get("time_interval")))
        self._next_switch_at = time.monotonic() + self._interval_seconds
        self._arm_timer_to_deadline()
        log.info("自动切换计时已开始：%d 秒", self._interval_seconds)

    def _arm_timer_to_deadline(self) -> None:
        """按单调时钟截止时间启动精确定时器。"""
        remaining = max(0.001, self._next_switch_at - time.monotonic())
        self._timer.start(max(1, math.ceil(remaining * 1000)))

    def _push_quote(self) -> None:
        quote = self._rotator.current()
        total = len(self._library)
        for win in self._windows:
            win.set_quote(quote, self._rotator.index, total)
        if self._system_wallpaper is not None and self._monitor_layout:
            _, _, width, height = self._monitor_layout[0]
            self._system_wallpaper.render(
                quote, self._rotator.index, total,
                self._effective_size((width, height)),
            )
        self.quoteChanged.emit(quote)

    def _on_tick(self) -> None:
        if self._paused:
            return
        # 即使 Qt/系统异常提前投递 timeout，也必须等满配置间隔。
        remaining = self._next_switch_at - time.monotonic()
        if remaining > 0:
            log.warning("忽略提前的切换定时信号，剩余 %.3f 秒", remaining)
            self._arm_timer_to_deadline()
            return
        self._switch("next", None, reason="timer")

    def next_quote(self, animate: bool | None = None, reason: str = "manual") -> None:
        self._switch("next", animate, reason=reason)

    def prev_quote(self, animate: bool | None = None, reason: str = "manual") -> None:
        self._switch("prev", animate, reason=reason)

    def _switch(self, direction: str, animate: bool | None, *, reason: str) -> None:
        if animate is None:
            animate = bool(self._config.get("animation_enabled"))
        if self._paused:
            animate = False
        self._pending_direction = direction
        self._timer.stop()
        log.info("切换语录：direction=%s reason=%s", direction, reason)
        if not animate or not self._windows:
            self._apply_direction()
            self._restart_timer()
            return
        self._transition.start()

    def _apply_direction(self) -> None:
        if self._pending_direction == "prev":
            self._rotator.prev()
        else:
            self._rotator.next()
        self._push_quote()

    # ------------------------------------------------------------ 动画回调
    def _on_transition_value(self) -> None:
        opacity = self._transition.text_opacity
        flip = self._transition.flip_progress
        for win in self._windows:
            win.set_transition(opacity, flip)

    def _on_swap(self) -> None:
        self._apply_direction()

    def _on_transition_finished(self) -> None:
        for win in self._windows:
            win.set_transition(1.0, 0.0)
        if not self._paused:
            # 完整间隔从新内容稳定显示后开始计算，避免动画与定时器重入。
            self._restart_timer()

    def _on_drift(self) -> None:
        dx, dy = self._drift.offset
        for win in self._windows:
            win.set_drift(dx, dy)

    # ================================================================ 暂停
    def set_paused(self, paused: bool) -> None:
        paused = bool(paused)
        if paused == self._paused:
            return
        self._paused = paused
        if paused:
            self._timer.stop()
            self._transition.pause()
            self._drift.stop()
        else:
            self._transition.resume()
            if self._config.get("paper_drift") and self._windows:
                self._configure_drift_rate()
                self._drift.start()
            if not self._transition.is_running():
                self._restart_timer()
        self.pausedChanged.emit(paused)

    def toggle_paused(self) -> None:
        self.set_paused(not self._paused)

    # ================================================================ 配置 / 数据
    def _on_config_changed(self, cfg: dict) -> None:
        new_interval = max(3, int(cfg.get("time_interval", self._interval_seconds)))
        interval_changed = new_interval != self._interval_seconds
        self._interval_seconds = new_interval
        self._rotator.set_mode(cfg.get("play_mode", "random"))
        self._transition.set_duration(cfg.get("animation_duration", 3.0))
        self._transition.set_page_turn_enabled(cfg.get("page_turn_enabled", True))
        for win in self._windows:
            win.refresh_config()
        if self._system_wallpaper is not None:
            self._system_wallpaper.refresh_config()
            self._push_quote()
        if cfg.get("paper_drift") and not self._paused and self._windows:
            self._configure_drift_rate()
            self._drift.start()
        else:
            self._drift.stop()
            for win in self._windows:
                win.set_drift(0.0, 0.0)
        if self._desktop_strategy == "workerw":
            expected = len(self._target_screens())
            if expected != len(self._windows):
                # 例如切换「覆盖所有显示器」后窗口数量需要跟着变。
                # 不能走 _on_screens_changed：显示器布局没变，那条路径会提前返回。
                self._activate_desktop_strategy()
        # 修改显示内容、字体等配置不应扰乱切换时间；
        # 只有切换间隔本身变化时才重新开始计时。
        if interval_changed and not self._paused and not self._transition.is_running():
            self._restart_timer()

    def _on_watch_quotes(self) -> None:
        if self._library.reload_if_modified():
            log.info("语录文件已更新，重新载入 %d 条", len(self._library))
            self._rotator.clamp()
            self._push_quote()

    def reload_quotes(self) -> None:
        self._library.reload()
        self._rotator.clamp()
        self._push_quote()
