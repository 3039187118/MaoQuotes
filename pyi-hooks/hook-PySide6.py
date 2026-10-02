"""PyInstaller 自定义 hook：PySide6 6.x 的二进制收集。

只收集 shiboken6 的运行时库；Qt 运行库交给 PyInstaller 自带的
``hook-PySide6.QtCore/QtGui/QtWidgets`` 收集——它们会顺着二进制依赖自动带上
真正需要的 DLL，并正确处理 PySide6 ≥ 6.5 的 DLL 布局（DLL 直接放在包根目录）。

⚠️ 不要再用 ``collect_dynamic_libs('PySide6')`` 一把梭收全部 DLL。
原因：PySide6 的 ``__init__.py`` 用 ``_find_all_qt_modules()`` 动态计算 ``__all__``，
会把包目录下所有 ``Qt*.pyd`` 都列出来，配合一把梭会把 **144 个 Qt DLL**
（含 194MB 的 ``Qt6WebEngineCore.dll``）全部塞进 exe：

* exe 体积从 ~90MB 膨胀到 ~178MB；
* 单文件模式退出时要递归删除这个巨大的临时目录（180MB / 2000+ 文件），
  被杀毒软件实时扫描拖到 **两分钟以上**，看起来就像进程卡死。

同理，``qml``（23MB）和 ``translations``（14MB）本项目都用不到：
代码里没有任何 ``QTranslator`` / QML 用法，不要收集。
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

hiddenimports = [
    'shiboken6',
    'inspect',
    'PySide6.support.deprecated',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

# shiboken6 的运行时库（很小，必须显式收）
binaries = []
binaries += collect_dynamic_libs('shiboken6')

# 只留真正用得到的插件：平台、图片格式（png/ico）、系统样式。
# 显式收集是为了兼容旧版 PyInstaller；新版自带的 Qt hook 也会收，重复项会被去重。
datas = []
for subdir in ('plugins/platforms', 'plugins/imageformats', 'plugins/styles'):
    datas += collect_data_files('PySide6', subdir=subdir)
