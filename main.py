"""Mao Quotes Live Wallpaper —— 程序入口。

用法::

    python main.py                 # 正式模式：嵌入桌面 + 托盘常驻
    python main.py --windowed      # 调试模式：普通窗口（空格/←→ 切换，Esc 退出）
    python main.py --no-embed      # 全屏置底但不嵌入桌面层
    python main.py --preview out   # 离屏渲染若干张效果图后退出（不显示窗口）

入口只做「装配」：解析参数 → 建配置 → 建控制器 → 建托盘 → 跑事件循环。
具体逻辑都在各自模块里。
"""

from __future__ import annotations

import argparse
import ctypes
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 让「双击 exe / 任意目录运行」都能正确 import 本项目的包
sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths  # noqa: E402

APP_NAME = "Mao Quotes Live Wallpaper"
MUTEX_NAME = "Global\\MaoLiveWallpaperSingleInstance"

log = logging.getLogger("mao")


# ==================================================================== 基础设施
def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                            datefmt="%H:%M:%S")

    try:
        file_handler = RotatingFileHandler(
            paths.log_dir() / "wallpaper.log", maxBytes=512 * 1024,
            backupCount=2, encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        pass

    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(fmt)
        root.addHandler(stream)


def ensure_dpi_awareness() -> None:
    """确保进程按物理像素取尺寸（必须在 QApplication 之前调用）。

    Qt6 默认已声明 Per-Monitor V2，正常情况下这里什么都不做。只有极少数
    机器（被启动器/父进程改过 DPI 上下文）会报告成「未感知」，此时
    ``EnumDisplayMonitors`` 返回的是缩放后的假分辨率，渲染出来的壁纸会被
    系统放大，表现为发糊、边缘对不上。这里只在这种情况补一刀。
    """
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    except (OSError, AttributeError):
        return

    context = user32.GetThreadDpiAwarenessContext()
    awareness = user32.GetAwarenessFromDpiAwarenessContext(context) if context else -1
    if awareness >= 1:  # 1=系统感知 2=每屏感知
        log.info("DPI 感知已就绪（awareness=%d）", awareness)
        return

    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
    if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
        log.info("已补设 Per-Monitor V2 DPI 感知")
    else:
        log.warning("补设 DPI 感知失败（错误码 %s），尺寸探测可能不准",
                    ctypes.get_last_error())


def acquire_single_instance() -> bool:
    """用具名互斥体保证只跑一个实例。非 Windows 平台直接放行。"""
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return True
    ERROR_ALREADY_EXISTS = 183
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return False
    # 故意不释放句柄：进程存活期间持有互斥体
    globals()["_instance_mutex"] = handle
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME, add_help=True)
    parser.add_argument("--windowed", action="store_true",
                        help="以普通窗口运行（调试用）")
    parser.add_argument("--no-embed", action="store_true",
                        help="全屏但不嵌入桌面层")
    parser.add_argument("--no-tray", action="store_true", help="不显示系统托盘")
    parser.add_argument("--interval", type=int, default=None,
                        help="覆盖自动切换间隔（秒）")
    parser.add_argument("--preview", metavar="DIR", default=None,
                        help="离屏渲染效果图到指定目录后退出")
    parser.add_argument("--preview-size", default="1600x900",
                        help="效果图尺寸，如 1920x1080")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


# ==================================================================== 主流程
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    paths.ensure_user_files()
    setup_logging(args.log_level)
    ensure_dpi_awareness()
    log.info("启动 %s", APP_NAME)

    # 离屏预览：不进事件循环，渲染完就退出
    if args.preview:
        from tools.render_preview import render_previews

        return render_previews(args.preview, args.preview_size)

    if not args.windowed and not acquire_single_instance():
        log.warning("已有实例在运行，退出")
        return 0

    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    from settings.config_manager import ConfigManager
    from wallpaper.controller import WallpaperController
    from wallpaper.fonts import load_bundled_fonts
    from wallpaper.wallpaper_window import WindowMode

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("MaoLiveWallpaper")
    app.setQuitOnLastWindowClosed(args.windowed)

    # 统一设置应用图标，否则独立顶层的设置对话框可能回退到
    # Windows 默认的空白窗口图标。
    icon_path = paths.resource_path("assets/icon.png")
    if icon_path.is_file():
        app_icon = QIcon(str(icon_path))
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)

    load_bundled_fonts()

    config = ConfigManager()
    if args.interval:
        # 命令行覆盖只作用于本次运行，不写回配置文件
        config.update({"time_interval": args.interval}, save=False, notify=False)

    # 决定窗口形态
    if args.windowed:
        mode = WindowMode.WINDOWED
    elif args.no_embed or not config.get("embed_desktop"):
        mode = WindowMode.FULLSCREEN
    else:
        mode = WindowMode.DESKTOP

    controller = WallpaperController(config, mode)
    controller.start()
    log.info("已载入 %d 条语录，模式 = %s", len(controller.library), mode.value)

    tray = None
    if not args.no_tray and not args.windowed:
        from PySide6.QtWidgets import QSystemTrayIcon

        from tray.tray_menu import TrayMenu

        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = TrayMenu(controller, config)
            tray.exitRequested.connect(app.quit)
            tray.show()
        else:
            QMessageBox.warning(None, APP_NAME,
                                "系统托盘不可用，程序将在无托盘状态下运行。")

    # 退出清理
    def _cleanup() -> None:
        log.info("正在退出…")
        if tray is not None:
            tray.hide()
        controller.shutdown()

    app.aboutToQuit.connect(_cleanup)

    # 让 Ctrl+C 在控制台里也能结束进程
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    heartbeat = QTimer()
    heartbeat.start(500)
    heartbeat.timeout.connect(lambda: None)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
