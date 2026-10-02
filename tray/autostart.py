"""开机自启动（Windows 注册表 Run 项）。

只写 ``HKEY_CURRENT_USER``，不需要管理员权限，卸载也只是删一个键值。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MaoLiveWallpaper"

try:  # 非 Windows 平台直接降级
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore[assignment]


def is_supported() -> bool:
    return winreg is not None and sys.platform == "win32"


def _launch_command() -> str:
    """生成开机启动要执行的命令行。"""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'

    # 源码运行：优先用 pythonw.exe，避免弹出黑色控制台
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else exe
    entry = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{interpreter}" "{entry}"'


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.debug("读取自启动项失败：%s", exc)
        return False


def set_enabled(enabled: bool) -> bool:
    """写入 / 删除自启动项，返回是否操作成功。"""
    if not is_supported():
        return False
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        log.warning("设置自启动失败：%s", exc)
        return False
