# Mao Quotes Live Wallpaper

《毛泽东选集》语录动态桌面壁纸 —— Windows 本地程序。

## 效果

- 米白旧纸背景 + 纸张纹理 + 缓慢漂移
- 屏幕中心展示中英文对照语录，带书页翻阅感
- 暗红色印章、中文页码、来源标注
- 每 30 秒自动切换（可配置），带淡入淡出 + 翻页动画
- 嵌入 Windows 桌面层（类似 Wallpaper Engine），不影响桌面图标与正常使用
- 系统托盘常驻：下一条 / 上一条 / 暂停 / 设置 / 退出

## 快速开始

### 开发运行

```bash
pip install -r requirements.txt
python main.py --windowed          # 调试窗口模式
python main.py                     # 正式模式（嵌入桌面 + 托盘）
python main.py --preview preview   # 离屏渲染效果图到 preview/ 目录
```

### 打包 exe

```bash
pip install -r requirements.txt
python -m PyInstaller MaoLiveWallpaper.spec --noconfirm --distpath dist --workpath build
```

产物：`dist/MaoLiveWallpaper.exe`（单文件，约 48 MB，双击即可运行）。

## 分辨率与铺满

程序默认**自动读取屏幕物理分辨率**，换电脑不需要任何设置：

- **单屏**：按物理分辨率离屏渲染 PNG，再设为系统壁纸。
- **多屏**：每屏一个窗口贴到桌面层（WorkerW）。取消勾选「覆盖所有显示器」则只在副屏显示。

设置里的「显示与分辨率」用于兜底：

| 项 | 说明 |
|----|------|
| `wallpaper_fit` | `fill` 铺满（默认）/ `fit` 适应 / `stretch` 拉伸 / `center` 居中 / `tile` 平铺 |
| `render_size` | `auto` 跟随屏幕（默认），或 `1920x1080` 这类手动尺寸 |
| `all_screens` | `true` 覆盖所有显示器；`false` 只在副屏显示 |

> 手动指定 `render_size` 只在自动识别不准、或需要给别的机器预先出图时使用。
> 尺寸与屏幕比例不一致时，「铺满」会裁掉边缘。

## 自定义语录

编辑 `data/quotes.json`（exe 同级目录），保存后数秒内自动生效。

格式：

```json
[
  {
    "id": 1,
    "cn": "没有调查，没有发言权",
    "en": "No investigation, no right to speak.",
    "source_cn": "《毛泽东选集》·反对本本主义",
    "source_en": "Selected Works of Mao Zedong",
    "tags": ["work", "morning"]
  }
]
```

`tags` 字段用于预留的「时段感知」选择器（morning / afternoon / evening / night）。



## 依赖

见 `requirements.txt`。

核心：PySide6, Pillow, numpy, pywin32, PyInstaller。
