"""配置读写管理。

配置文件位于 ``settings/config.json``（打包后位于 exe 同级目录）。
任何模块都通过 :class:`ConfigManager` 读写配置，
配置变化时通过 ``changed`` 信号广播，壁纸窗口会即时刷新。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from PySide6.QtCore import QObject, Signal

import paths

log = logging.getLogger(__name__)

# 所有可配置项的默认值（同时充当类型与合法性校验的参照）
DEFAULT_CONFIG: dict[str, Any] = {
    # 切换
    "time_interval": 30,            # 自动切换间隔（秒）
    "play_mode": "random",          # random | sequential
    # 显示内容
    "show_cn": True,
    "show_en": True,
    "show_source": True,
    "show_seal": True,
    "show_page_number": True,
    # 动画
    "animation_enabled": True,
    "animation_duration": 3.0,      # 一次完整过场的秒数
    "page_turn_enabled": True,      # 关闭后只做淡入淡出
    "paper_drift": True,            # 纸张纹理缓慢移动
    # 外观
    "background_color": [245, 240, 225],
    "text_color": [38, 34, 30],
    "seal_color": [150, 42, 36],
    "font_cn": "",
    "font_en": "",
    "cn_size_ratio": 0.062,         # 中文字号 = 屏幕高度 * 该比例
    # 铺满方式
    "wallpaper_fit": "fill",        # fill | fit | stretch | center | tile
    "render_size": "auto",          # auto = 跟随屏幕物理分辨率；也可写 "1920x1080"
    # 运行方式
    "embed_desktop": True,          # 嵌入 Windows 桌面层
    "all_screens": True,            # 覆盖所有显示器
    "autostart": False,
}

_VALID_MODES = ("random", "sequential")
_VALID_FITS = ("fill", "fit", "stretch", "center", "tile")

# "1920x1080" / "1920 × 1080" / "1920*1080" 都接受
_RENDER_SIZE_RE = re.compile(r"^(\d{2,5})\s*[x×*]\s*(\d{2,5})$", re.IGNORECASE)
RENDER_SIZE_MIN = (640, 480)
RENDER_SIZE_MAX = (15360, 8640)


class ConfigManager(QObject):
    """配置容器：加载 / 校验 / 保存 / 变更通知。"""

    changed = Signal(dict)  # 发出变更后的完整配置

    def __init__(self, path=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path or paths.config_path()
        self._data: dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    # ------------------------------------------------------------------ 读写
    def load(self) -> dict[str, Any]:
        data = dict(DEFAULT_CONFIG)
        try:
            with open(self._path, "r", encoding="utf-8") as fp:
                user = json.load(fp)
            if isinstance(user, dict):
                data.update({k: v for k, v in user.items() if k in DEFAULT_CONFIG})
        except FileNotFoundError:
            log.info("未找到配置文件，使用默认配置：%s", self._path)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("配置文件解析失败，回退默认配置：%s", exc)

        self._data = self._sanitize(data)
        return self._data

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fp:
                json.dump(self._data, fp, ensure_ascii=False, indent=2)
        except OSError as exc:
            log.warning("配置保存失败：%s", exc)

    # ------------------------------------------------------------------ 访问
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULT_CONFIG.get(key, default))

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def set(self, key: str, value: Any, *, save: bool = True, notify: bool = True) -> None:
        self.update({key: value}, save=save, notify=notify)

    def update(self, values: dict[str, Any], *, save: bool = True, notify: bool = True) -> None:
        merged = dict(self._data)
        merged.update({k: v for k, v in values.items() if k in DEFAULT_CONFIG})
        merged = self._sanitize(merged)
        if merged == self._data:
            return
        self._data = merged
        if save:
            self.save()
        if notify:
            self.changed.emit(self.as_dict())

    # ------------------------------------------------------------------ 校验
    @staticmethod
    def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
        out = dict(DEFAULT_CONFIG)
        out.update(data)

        # 数值范围
        try:
            out["time_interval"] = max(3, int(out["time_interval"]))
        except (TypeError, ValueError):
            out["time_interval"] = DEFAULT_CONFIG["time_interval"]

        try:
            out["animation_duration"] = min(10.0, max(0.4, float(out["animation_duration"])))
        except (TypeError, ValueError):
            out["animation_duration"] = DEFAULT_CONFIG["animation_duration"]

        try:
            out["cn_size_ratio"] = min(0.16, max(0.02, float(out["cn_size_ratio"])))
        except (TypeError, ValueError):
            out["cn_size_ratio"] = DEFAULT_CONFIG["cn_size_ratio"]

        # 枚举
        if out.get("play_mode") not in _VALID_MODES:
            out["play_mode"] = DEFAULT_CONFIG["play_mode"]

        if out.get("wallpaper_fit") not in _VALID_FITS:
            out["wallpaper_fit"] = DEFAULT_CONFIG["wallpaper_fit"]

        out["render_size"] = ConfigManager.normalize_render_size(out.get("render_size"))

        # 布尔
        for key, default in DEFAULT_CONFIG.items():
            if isinstance(default, bool):
                out[key] = bool(out.get(key, default))

        # 颜色
        for key in ("background_color", "text_color", "seal_color"):
            out[key] = ConfigManager._sanitize_color(out.get(key), DEFAULT_CONFIG[key])

        # 至少显示一项正文
        if not out["show_cn"] and not out["show_en"]:
            out["show_cn"] = True

        return out

    @staticmethod
    def _sanitize_color(value: Any, fallback: list[int]) -> list[int]:
        try:
            rgb = [int(v) for v in value][:3]
            if len(rgb) != 3:
                raise ValueError
            return [min(255, max(0, v)) for v in rgb]
        except (TypeError, ValueError):
            return list(fallback)

    # ------------------------------------------------------------ 渲染分辨率
    @staticmethod
    def normalize_render_size(value: Any) -> str:
        """把 render_size 规范成 ``"auto"`` 或 ``"宽x高"``。

        任何解析不出来的值都退回 ``"auto"``，保证配置永远不会把程序卡死。
        """
        if not isinstance(value, str):
            return "auto"
        text = value.strip().lower().replace(" ", "")
        if text in ("", "auto", "自动", "默认"):
            return "auto"
        match = _RENDER_SIZE_RE.match(text)
        if not match:
            return "auto"
        width = min(RENDER_SIZE_MAX[0], max(RENDER_SIZE_MIN[0], int(match.group(1))))
        height = min(RENDER_SIZE_MAX[1], max(RENDER_SIZE_MIN[1], int(match.group(2))))
        return f"{width}x{height}"

    @staticmethod
    def parse_render_size(value: Any) -> tuple[int, int] | None:
        """返回手动指定的 ``(宽, 高)``；``auto`` 或非法值返回 ``None``。"""
        text = ConfigManager.normalize_render_size(value)
        if text == "auto":
            return None
        width, height = text.split("x")
        return int(width), int(height)
