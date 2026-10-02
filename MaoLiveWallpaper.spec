# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

用法::

    pyinstaller MaoLiveWallpaper.spec

产物：dist/MaoLiveWallpaper.exe（单文件，无控制台窗口）
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)

# 本项目只用到 QtCore / QtGui / QtWidgets，其余 Qt 模块必须显式排除。
#
# 原因：PySide6 的 __init__.py 用 _find_all_qt_modules() 动态计算 __all__，
# 会把包目录下所有 Qt*.pyd 都列出来，PyInstaller 于是把它们全部当成隐式导入，
# 连带收集全部 Qt DLL（含 194MB 的 Qt6WebEngineCore.dll），exe 从 ~90MB 涨到 ~178MB。
# 单文件模式下这个巨大的临时目录在退出时还要被逐个删除，会被杀毒软件扫描拖到
# 两分钟以上，看起来像进程卡死。
_QT_EXCLUDES = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtBluetooth", "PySide6.QtCharts", "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization", "PySide6.QtDBus", "PySide6.QtDesigner",
    "PySide6.QtGraphs", "PySide6.QtGraphsWidgets", "PySide6.QtHelp",
    "PySide6.QtHttpServer", "PySide6.QtLocation", "PySide6.QtLottie",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtNetwork",
    "PySide6.QtNetworkAuth", "PySide6.QtNfc", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtTest",
    "PySide6.QtTextToSpeech", "PySide6.QtUiTools", "PySide6.QtVirtualKeyboard",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.QtXml",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "data"), "data"),
        (str(ROOT / "assets"), "assets"),
        (str(ROOT / "settings"), "settings"),
    ],
    hiddenimports=[
        "wallpaper",
        "wallpaper.quotes",
        "wallpaper.fonts",
        "wallpaper.paper",
        "wallpaper.animation",
        "wallpaper.wallpaper_window",
        "wallpaper.desktop_embed",
        "wallpaper.controller",
        "wallpaper.system_wallpaper",
        "settings",
        "settings.config_manager",
        "tray",
        "tray.tray_menu",
        "tray.settings_dialog",
        "tray.autostart",
        "tools",
        "tools.render_preview",
        "tools.generate_assets",
        "numpy",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageFilter",
    ],
    hookspath=[str(ROOT / "pyi-hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不需要的重型模块，减小体积
        "matplotlib", "scipy", "pandas", "tkinter",
        "IPython", "jupyter", "notebook",
        "pytest", "setuptools", "pip",
    ] + _QT_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,         # 关键修正：传 a.binaries 而不是 []
    a.zipfiles,
    a.datas,
    exclude_binaries=False,   # 单文件模式：所有二进制 / 数据全部内嵌
    name="MaoLiveWallpaper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # 先不用 UPX，确保单文件正确生成
    console=False,          # 无控制台窗口
    icon=str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").exists() else None,
)
