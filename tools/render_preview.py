"""离屏渲染效果图。

不弹窗、不占桌面，直接把壁纸窗口画到 PNG，便于快速检查排版与动画中间态：

    python main.py --preview preview --preview-size 1920x1080
"""

from __future__ import annotations

import sys
from pathlib import Path


def _parse_size(text: str) -> tuple[int, int]:
    try:
        w, h = text.lower().split("x")
        return max(320, int(w)), max(240, int(h))
    except (ValueError, AttributeError):
        return 1600, 900


def render_previews(out_dir: str, size_text: str = "1600x900") -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QApplication

    from settings.config_manager import ConfigManager
    from wallpaper.fonts import load_bundled_fonts
    from wallpaper.quotes import QuoteLibrary
    from wallpaper.wallpaper_window import WallpaperWindow, WindowMode

    width, height = _parse_size(size_text)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    load_bundled_fonts()

    config = ConfigManager()
    library = QuoteLibrary()

    window = WallpaperWindow(config, WindowMode.WINDOWED)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(width, height)
    window.show()          # 只做「实例化」，不会真的显示到屏幕上
    app.processEvents()

    def shot(name: str) -> Path:
        pix = QPixmap(window.size())
        window.render(pix)
        path = out / name
        pix.save(str(path))
        print(f"[preview] {path}")
        return path

    total = len(library)

    # 1. 常态：短语录
    window.set_quote(library[0], 0, total)
    window.set_transition(1.0, 0.0)
    app.processEvents()
    shot("01_normal_short.png")

    # 2. 常态：长语录（检查自动缩字号与换行）
    long_index = max(range(total), key=lambda i: len(library[i].cn))
    window.set_quote(library[long_index], long_index, total)
    app.processEvents()
    shot("02_normal_long.png")

    # 3. 淡出中
    window.set_quote(library[1], 1, total)
    window.set_transition(0.30, 0.0)
    app.processEvents()
    shot("03_fade_out.png")

    # 4. 翻页中（页面接近立起）
    window.set_transition(0.0, 0.42)
    app.processEvents()
    shot("04_page_turning.png")

    # 5. 翻页后半程
    window.set_quote(library[2], 2, total)
    window.set_transition(0.0, 0.62)
    app.processEvents()
    shot("05_page_turned.png")

    # 6. 淡入完成
    window.set_transition(1.0, 0.0)
    app.processEvents()
    shot("06_fade_in.png")

    window.close()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    raise SystemExit(render_previews(sys.argv[1] if len(sys.argv) > 1 else "preview"))
