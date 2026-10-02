"""生成 assets 里的静态素材（纸张纹理 / 印章 / 图标）。

只在开发阶段跑一次，产物会随程序一起打包：

    python tools/generate_assets.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

PAPER_SIZE = (1920, 1200)
PAPER_BASE = (245, 240, 225)
SEAL_SIZE = 512
SEAL_COLOR = (150, 42, 36)
SEAL_TEXT = "实事求是"

# Windows 常见中文字体，按「像书法/印章」的顺序尝试
CN_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/STZHONGS.TTF", 0),
    ("C:/Windows/Fonts/STKAITI.TTF", 0),
    ("C:/Windows/Fonts/simsun.ttc", 0),
    ("C:/Windows/Fonts/msyh.ttc", 0),
    ("C:/Windows/Fonts/simhei.ttf", 0),
]


def _load_cn_font(size: int) -> ImageFont.FreeTypeFont | None:
    for path, index in CN_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    return None


# ------------------------------------------------------------------ 纸张纹理
def _value_noise(shape: tuple[int, int], scale: int, rng) -> np.ndarray:
    """低频值噪声（随机小图 + 双线性放大）。"""
    h, w = shape
    sh, sw = max(2, h // scale), max(2, w // scale)
    small = rng.random((sh, sw), dtype=np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8), mode="L")
    img = img.resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def generate_paper(path: Path) -> None:
    w, h = PAPER_SIZE
    rng = np.random.default_rng(19490101)

    # 多倍频云斑
    field = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    for scale in (5, 11, 27, 64, 140):
        field += _value_noise((h, w), scale, rng) * amp
        amp *= 0.55
    field = (field - field.min()) / max(1e-6, float(np.ptp(field)))
    field = field * 2.0 - 1.0

    # 高频颗粒 + 横向纤维
    grain = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    fibre = np.sin(np.linspace(0, math.pi * 90, w, dtype=np.float32))[None, :]
    fibre = fibre * rng.normal(0.0, 1.0, (h, 1)).astype(np.float32)

    delta = field * 8.0 + grain * 3.0 + fibre * 1.8

    # 几处淡淡的陈年水渍
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for _ in range(7):
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, h)
        radius = rng.uniform(w * 0.06, w * 0.22)
        strength = rng.uniform(2.0, 5.5)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
        delta -= np.exp(-dist ** 2) * strength

    r = np.clip(PAPER_BASE[0] + delta * 1.00, 0, 255)
    g = np.clip(PAPER_BASE[1] + delta * 0.93, 0, 255)
    b = np.clip(PAPER_BASE[2] + delta * 0.80, 0, 255)
    rgb = np.dstack([r, g, b]).astype(np.uint8)

    img = Image.fromarray(rgb, mode="RGB").filter(ImageFilter.SMOOTH)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=92, optimize=True)
    print(f"[paper] {path}  {img.size}")


# ------------------------------------------------------------------ 印章
def generate_seal(path: Path) -> None:
    size = SEAL_SIZE
    ss = 2  # 超采样倍数
    canvas = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    border = int(size * ss * 0.055)
    margin = int(size * ss * 0.04)
    box = (margin, margin, size * ss - margin, size * ss - margin)
    draw.rounded_rectangle(box, radius=int(size * ss * 0.05),
                           outline=SEAL_COLOR + (255,), width=border)

    font = _load_cn_font(int(size * ss * 0.34))
    if font is not None:
        inner = (box[0] + border * 2, box[1] + border * 2,
                 box[2] - border * 2, box[3] - border * 2)
        cw = (inner[2] - inner[0]) / 2
        ch = (inner[3] - inner[1]) / 2
        # 印文读序：右上 → 右下 → 左上 → 左下
        positions = [(1, 0), (1, 1), (0, 0), (0, 1)]
        for ch_text, (col, row) in zip(SEAL_TEXT, positions):
            cx = inner[0] + cw * col + cw / 2
            cy = inner[1] + ch * row + ch / 2
            draw.text((cx, cy), ch_text, font=font,
                      fill=SEAL_COLOR + (255,), anchor="mm")
    else:
        print("[seal] 未找到中文字体，只画边框")

    canvas = canvas.resize((size, size), Image.LANCZOS)

    # 做旧：随机剥蚀，模拟印泥不均
    rng = np.random.default_rng(1893)
    arr = np.array(canvas)
    noise = rng.random((size, size)).astype(np.float32)
    noise_img = Image.fromarray((noise * 255).astype(np.uint8), mode="L")
    noise_img = noise_img.filter(ImageFilter.GaussianBlur(1.2))
    mask = np.asarray(noise_img, dtype=np.float32) / 255.0
    erosion = np.clip((mask - 0.28) / 0.5, 0.0, 1.0)
    arr[..., 3] = (arr[..., 3].astype(np.float32) * (0.55 + 0.45 * erosion)).astype(np.uint8)

    Image.fromarray(arr, mode="RGBA").save(path)
    print(f"[seal]  {path}  {size}x{size}")


# ------------------------------------------------------------------ 图标
def generate_icon(png_path: Path, ico_path: Path) -> None:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((10, 10, size - 10, size - 10),
                           radius=34, fill=SEAL_COLOR + (255,))
    font = _load_cn_font(int(size * 0.58))
    if font is not None:
        draw.text((size / 2, size / 2 - 4), "毛", font=font,
                  fill=(250, 245, 235, 255), anchor="mm")
    img.save(png_path)
    img.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                              (128, 128), (256, 256)])
    print(f"[icon]  {png_path} / {ico_path}")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "fonts").mkdir(parents=True, exist_ok=True)
    generate_paper(ASSETS / "paper_texture.jpg")
    generate_seal(ASSETS / "seal.png")
    generate_icon(ASSETS / "icon.png", ASSETS / "icon.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
