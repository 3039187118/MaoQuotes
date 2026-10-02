"""路径解析模块。

统一处理三类路径，屏蔽「源码运行」与「PyInstaller 打包运行」的差异：

* 只读资源（assets / 默认数据）    -> :func:`resource_path`
* 可写数据（用户语录、用户配置）    -> :func:`writable_path`
* 日志目录                        -> :func:`log_dir`

打包成单文件 exe 后，只读资源会被解包到临时目录 ``sys._MEIPASS``，
而用户可编辑的 ``data/quotes.json``、``settings/config.json``
则放在 exe 同级目录（若不可写则退回 ``%APPDATA%``），
以保证「用户可以直接修改 JSON 增加语录」这一需求。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "MaoLiveWallpaper"

# 需要在首次运行时从只读资源「播种」到可写目录的文件
_SEED_FILES = (
    "data/quotes.json",
    "settings/config.json",
)


def is_frozen() -> bool:
    """是否运行于 PyInstaller 打包环境。"""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """源码根目录（本文件所在目录）。"""
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    """只读资源根目录。"""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return project_root()


def resource_path(relative: str) -> Path:
    """获取只读资源的绝对路径，例如 ``resource_path("assets/seal.png")``。"""
    return resource_root() / relative


def _appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(base) / APP_NAME


def _dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


_writable_root_cache: Path | None = None


def writable_root() -> Path:
    """用户数据根目录（可写）。"""
    global _writable_root_cache
    if _writable_root_cache is not None:
        return _writable_root_cache

    if is_frozen():
        candidate = Path(sys.executable).resolve().parent
        if not _dir_writable(candidate):
            candidate = _appdata_dir()
            candidate.mkdir(parents=True, exist_ok=True)
    else:
        candidate = project_root()

    _writable_root_cache = candidate
    return candidate


def writable_path(relative: str) -> Path:
    """获取可写文件路径；若文件不存在则尝试从只读资源播种一份。"""
    target = writable_root() / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        seed = resource_path(relative)
        if seed.exists() and seed.resolve() != target.resolve():
            try:
                shutil.copyfile(seed, target)
            except OSError:
                pass
    return target


def ensure_user_files() -> None:
    """首次运行时把默认的语录库与配置复制到可写目录。"""
    for rel in _SEED_FILES:
        writable_path(rel)


def config_path() -> Path:
    return writable_path("settings/config.json")


def quotes_path() -> Path:
    return writable_path("data/quotes.json")


def log_dir() -> Path:
    d = writable_root() / "logs"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        d = _appdata_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
    return d
