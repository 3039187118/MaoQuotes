"""单显示器下的 Windows 系统壁纸后端。

部分 Windows 11 单屏桌面使用 DirectComposition 合成桌面背景，
普通 Qt 子窗口即使成功挂入 WorkerW，也可能被系统壁纸表面遮挡。
单屏时改为把当前语录离屏渲染为与物理分辨率一致的 PNG，再通过
``SystemParametersInfoW`` 设置为系统壁纸，可保留桌面图标并避免持续重绘。
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

import paths
from settings.config_manager import ConfigManager

from .quotes import Quote
from .wallpaper_window import WallpaperWindow, WindowMode

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

SPI_SETDESKWALLPAPER = 0x0014
SPI_GETDESKWALLPAPER = 0x0073
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002

DESKTOP_KEY = r"Control Panel\Desktop"

# 显示方式 → (WallpaperStyle, TileWallpaper) 注册表值
#   0=居中  2=拉伸  6=适应  10=铺满  22=跨屏(平铺用 0+TileWallpaper=1)
FIT_STYLES: dict[str, tuple[str, str]] = {
    "fill": ("10", "0"),
    "fit": ("6", "0"),
    "stretch": ("2", "0"),
    "center": ("0", "0"),
    "tile": ("0", "1"),
}


class SystemWallpaperBackend:
    """把语录渲染成静态系统壁纸；停止时恢复用户原壁纸。"""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._renderer: WallpaperWindow | None = None
        self._size = (0, 0)
        self._output = paths.writable_root() / "cache" / "mao_current_wallpaper.png"
        self._metadata = paths.writable_root() / "cache" / "original_wallpaper.json"
        self._original_path = ""
        self._original_style = ("10", "0")
        self._active = False
        self._applied_fit: str | None = None

        if IS_WINDOWS:
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            self._user32.SystemParametersInfoW.restype = wintypes.BOOL
            self._user32.SystemParametersInfoW.argtypes = [
                wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT,
            ]
        else:
            self._user32 = None

    def start(self, size: tuple[int, int]) -> None:
        if not self._active:
            current = self._get_current_wallpaper()
            saved = self._load_saved_original()
            if self._same_path(current, str(self._output)) and saved is not None:
                self._original_path, self._original_style = saved
            else:
                self._original_path = current
                self._original_style = self._read_style()
                self._save_original()
            self._active = True
        self._size = self._valid_size(size)

    def render(self, quote: Quote, index: int, total: int,
               size: tuple[int, int] | None = None) -> bool:
        if not IS_WINDOWS or self._user32 is None:
            return False
        if size is not None:
            self._size = self._valid_size(size)
        width, height = self._size
        if width <= 0 or height <= 0:
            return False

        app = QApplication.instance()
        if app is None:
            return False

        if self._renderer is None:
            self._renderer = WallpaperWindow(self._config, WindowMode.WINDOWED)
            self._renderer.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            self._renderer.show()

        self._renderer.resize(width, height)
        self._renderer.set_quote(quote, index, total)
        self._renderer.set_transition(1.0, 0.0)
        self._renderer.set_drift(0.0, 0.0)
        app.processEvents()

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.black)
        self._renderer.render(pixmap)

        self._output.parent.mkdir(parents=True, exist_ok=True)
        if not pixmap.save(str(self._output), "PNG"):
            log.warning("单屏壁纸渲染保存失败：%s", self._output)
            return False

        # 先落样式再设壁纸：样式写不进去的话，系统会沿用用户旧样式
        # （常见是「居中」），表现就是四周留白、看起来没铺满。
        self._apply_style(str(self._config.get("wallpaper_fit", "fill")))
        ok = bool(self._user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            str(self._output),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        ))
        if ok:
            log.info("单屏系统壁纸已更新：%dx%d | %s", width, height, self._output)
        else:
            log.warning("设置单屏系统壁纸失败，错误码 %s", ctypes.get_last_error())
        return ok

    def _apply_style(self, fit: str) -> None:
        """写入显示方式并读回校验；失败时留下明确日志。

        只在显示方式真的变化时写注册表，避免每次切语录都做一次无谓的写入。
        """
        if fit == self._applied_fit:
            return
        self._applied_fit = fit
        style, tile = FIT_STYLES.get(fit, FIT_STYLES["fill"])
        if not self._write_style(style, tile):
            log.warning("壁纸显示方式写入失败，系统会沿用旧样式（屏幕四周可能留白）")
            return
        actual = self._read_style()
        if actual != (style, tile):
            log.warning("壁纸显示方式未生效：期望 %s，实际 %s（可能被其他壁纸软件接管）",
                        (style, tile), actual)

    def refresh_config(self) -> None:
        if self._renderer is not None:
            self._renderer.refresh_config()

    def stop(self, *, restore: bool = True) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer.deleteLater()
            self._renderer = None

        if restore and self._active and self._original_path and self._user32 is not None:
            self._write_style(*self._original_style)
            self._user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                self._original_path,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
            log.info("已恢复用户原系统壁纸")
        self._active = False
        self._applied_fit = None

    @staticmethod
    def _valid_size(size: tuple[int, int]) -> tuple[int, int]:
        width, height = size
        return max(320, int(width)), max(240, int(height))

    def _get_current_wallpaper(self) -> str:
        if self._user32 is None:
            return ""
        buffer = ctypes.create_unicode_buffer(32768)
        if self._user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER, len(buffer), buffer, 0
        ):
            return buffer.value
        return ""

    @staticmethod
    def _same_path(left: str, right: str) -> bool:
        if not left or not right:
            return False
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )

    def _save_original(self) -> None:
        try:
            self._metadata.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "path": self._original_path,
                "style": self._original_style[0],
                "tile": self._original_style[1],
            }
            self._metadata.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            log.debug("保存原壁纸元数据失败：%s", exc)

    def _load_saved_original(self) -> tuple[str, tuple[str, str]] | None:
        try:
            payload = json.loads(self._metadata.read_text(encoding="utf-8"))
            path = str(payload.get("path", ""))
            if not path:
                return None
            return path, (
                str(payload.get("style", "10")),
                str(payload.get("tile", "0")),
            )
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _read_style() -> tuple[str, str]:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DESKTOP_KEY) as key:
                style = str(winreg.QueryValueEx(key, "WallpaperStyle")[0])
                tile = str(winreg.QueryValueEx(key, "TileWallpaper")[0])
                return style, tile
        except (ImportError, FileNotFoundError, OSError):
            return "10", "0"

    @staticmethod
    def _write_style(style: str, tile: str) -> bool:
        try:
            import winreg

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, DESKTOP_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, style)
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile)
            return True
        except (ImportError, OSError) as exc:
            log.debug("写入系统壁纸样式失败：%s", exc)
            return False
