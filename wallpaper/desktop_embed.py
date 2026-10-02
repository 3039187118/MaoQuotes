"""Windows 桌面层嵌入。

原理（Wallpaper Engine 同款做法）：

1. 向 ``Progman`` 发送未公开消息 ``0x052C``，
   促使 Explorer 在桌面图标层（``SHELLDLL_DefView``）之外
   再生成一个或多个 ``WorkerW`` 窗口；
2. 枚举所有顶层 ``WorkerW`` 窗口（跳过含图标层的那个），
   让每个显示器上的壁纸窗口挂到真正覆盖它的 ``WorkerW`` 上；
3. ``SetParent`` 把我们的窗口挂到该 ``WorkerW`` 上。

每个显示器在多显示器场景下可能对应独立的 WorkerW，所以
「每次按窗口位置找最匹配的 WorkerW」是支持多显示器的关键。
``spawn_worker_w`` 故意只在启动时调用一次，反复发送会越造越多孤儿窗口。

全部使用 ctypes 调用 user32，不依赖 pywin32。
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------- Win32 常量
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

SMTO_NORMAL = 0x0000
WM_SPAWN_WORKER = 0x052C

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

HWND_BOTTOM = 1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004

_CLASS_NAME_BUF = 64

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]

    user32.FindWindowExW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND,
                                     wintypes.LPCWSTR, wintypes.LPCWSTR]

    user32.EnumWindows.restype = wintypes.BOOL
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]

    user32.EnumChildWindows.restype = wintypes.BOOL
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]

    user32.SetParent.restype = wintypes.HWND
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]

    user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    user32.SendMessageTimeoutW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD),
    ]

    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]

    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]

    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]

    user32.SetWindowPos.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                    ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]

    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    user32.EnumDisplayMonitors.argtypes = [
        wintypes.HDC, ctypes.POINTER(wintypes.RECT),
        ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM),
        wintypes.LPARAM,
    ]

    if ctypes.sizeof(ctypes.c_void_p) == 8:
        user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int,
                                             ctypes.c_longlong]
        _get_long = user32.GetWindowLongPtrW
        _set_long = user32.SetWindowLongPtrW
    else:  # 32 位兜底
        _get_long = user32.GetWindowLongW
        _set_long = user32.SetWindowLongW
else:  # 非 Windows 平台下所有函数降级为空实现
    user32 = None


# ---------------------------------------------------------------- 状态
_spawn_done = False        # 防止反复 spawn_worker_w 制造孤儿 WorkerW


# ---------------------------------------------------------------- 对外函数
def is_supported() -> bool:
    return IS_WINDOWS and user32 is not None


def virtual_screen_origin() -> tuple[int, int]:
    """虚拟桌面左上角坐标（多显示器时可能是负数）。

    注意：``GetSystemMetrics`` 在 per-monitor DPI 场景下返回的是虚拟化坐标。
    为了避免与 ``enum_physical_monitors()`` 的结果不一致，这里改用物理屏矩形
    的最小值计算。
    """
    if not is_supported():
        return (0, 0)
    physical = enum_physical_monitors()
    if physical:
        x = min(m[0] for m in physical)
        y = min(m[1] for m in physical)
        return (x, y)
    return (
        user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
    )


def virtual_screen_size() -> tuple[int, int]:
    """虚拟桌面总尺寸（像素）。"""
    if not is_supported():
        return (0, 0)
    physical = enum_physical_monitors()
    if physical:
        left = min(m[0] for m in physical)
        top = min(m[1] for m in physical)
        right = max(m[0] + m[2] for m in physical)
        bottom = max(m[1] + m[3] for m in physical)
        return right - left, bottom - top
    return (
        user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def progman_handle() -> int:
    if not is_supported():
        return 0
    return user32.FindWindowW("Progman", None) or 0


def _class_name(hwnd: int) -> str:
    if not is_supported() or not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(_CLASS_NAME_BUF)
    user32.GetClassNameW(hwnd, buf, _CLASS_NAME_BUF)
    return buf.value


def _get_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    if not is_supported() or not hwnd:
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)


def spawn_worker_w(force: bool = False) -> int:
    """让 Explorer 生成 WorkerW 层，返回 Progman 句柄。

    默认只发送一次；反复发送会创建多个空 WorkerW。
    """
    global _spawn_done
    if not is_supported():
        return 0
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return 0
    if not force and _spawn_done:
        return progman
    result = wintypes.DWORD()
    user32.SendMessageTimeoutW(progman, WM_SPAWN_WORKER, 0xD, 0x1,
                               SMTO_NORMAL, 1000, ctypes.byref(result))
    # 部分系统需要第二种参数组合才会生效
    user32.SendMessageTimeoutW(progman, WM_SPAWN_WORKER, 0xD, 0x0,
                               SMTO_NORMAL, 1000, ctypes.byref(result))
    _spawn_done = True
    return progman


def reset_spawn_flag() -> None:
    """重置 spawn 标记（仅在显式调用时使用，例如日志级别切换）。"""
    global _spawn_done
    _spawn_done = False


def find_worker_w_all() -> list[int]:
    """枚举所有可挂载的 WorkerW 窗口。

    Win10 上 WorkerW 是 Progman 的兄弟（顶层窗口）。
    Win11（21H2+）上空 WorkerW 有时是 Progman 的子窗口，因此这里同时扫描
    顶层窗口与 Progman 的直接子窗口。跳过任何包含 ``SHELLDLL_DefView`` 的层。
    """
    if not is_supported():
        return []

    result: list[tuple[int, str]] = []   # (hwnd, 来源)

    def _is_valid_worker_w(hwnd: int) -> bool:
        if not hwnd:
            return False
        if _class_name(hwnd) != "WorkerW":
            return False
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            return False
        return True

    def _enum_top(hwnd: int, _lparam: int) -> bool:
        if user32.GetParent(hwnd) != 0:
            return True
        if _is_valid_worker_w(hwnd):
            result.append((hwnd, "top"))
        return True

    user32.EnumWindows(WNDENUMPROC(_enum_top), 0)

    # 补充：Progman 的子窗口里也可能有空 WorkerW（Win11 22H2+ 常见）
    progman = progman_handle()
    if progman:
        ENUM_CHILDPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _enum_child(hwnd: int, _lparam: int) -> bool:
            if _is_valid_worker_w(hwnd):
                result.append((hwnd, "child-of-progman"))
            return True

        try:
            user32.EnumChildWindows(progman, ENUM_CHILDPROC(_enum_child), 0)
        except Exception as exc:  # 防御性：万一签名不匹配
            log.debug("EnumChildWindows 跳过：%s", exc)

    seen: set[int] = set()
    deduped: list[int] = []
    for hwnd, _src in result:
        if hwnd in seen:
            continue
        seen.add(hwnd)
        deduped.append(hwnd)
    return deduped


def find_worker_w_with_icons() -> int:
    """找持有桌面图标 ``SHELLDLL_DefView`` 的 WorkerW。

    这个 WorkerW 生命周期与图标同在，比空 WorkerW 更稳定。
    Win11 偶尔会重建空 WorkerW，图标 WorkerW 则几乎不销毁。
    """
    if not is_supported():
        return 0
    progman = progman_handle()
    if not progman:
        return 0
    # 遍历 Progman 的直接子窗口，找类名为 WorkerW 且含 SHELLDLL_DefView
    children: list[int] = []

    def _collect(hwnd: int, _lparam: int) -> bool:
        children.append(hwnd)
        return True

    CHPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows(progman, CHPROC(_collect), 0)
    for hwnd in children:
        if _class_name(hwnd) != "WorkerW":
            continue
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            return hwnd
    return 0


def find_worker_w_for_rect(x: int, y: int, w: int, h: int) -> int:
    """找到最适合覆盖指定屏幕矩形的 WorkerW。

    策略：取窗口矩形中心点，落在哪个 WorkerW 区域里就用哪个；
    若多个 WorkerW 都覆盖（常见于主屏 + 扩展屏各有一个），
    选面积最小的那一个（更精确匹配该显示器）；若都覆盖不到，
    退而求其次选最大的那个（一般是覆盖虚拟桌面的总 WorkerW）。
    """
    candidates = find_worker_w_all()
    if not candidates:
        return 0

    cx = x + w // 2
    cy = y + h // 2

    def area(rect: tuple[int, int, int, int]) -> int:
        return rect[2] * rect[3]

    scored: list[tuple[int, int, int]] = []   # (hwnd, area, contains_point)
    for hwnd in candidates:
        rect = _get_rect(hwnd)
        if not rect or rect[2] <= 0 or rect[3] <= 0:
            continue
        # WorkerW 自身的客户区虽然只是 (0,0,width,height)，
        # 但 Windows 报告的 rect 经常是 (0,0,virtual_width, virtual_height)，
        # 也就是它「覆盖范围」的描述。
        contains = (rect[0] <= cx < rect[0] + rect[2]
                    and rect[1] <= cy < rect[1] + rect[3])
        scored.append((hwnd, area(rect), 1 if contains else 0))

    if not scored:
        return 0

    # 优先选「包含中心点」的最小 WorkerW
    containing = [s for s in scored if s[2]]
    if containing:
        return min(containing, key=lambda s: s[1])[0]

    # 都没覆盖到：选最大的（一般是虚拟桌面 WorkerW）
    return max(scored, key=lambda s: s[1])[0]


def make_click_through(hwnd: int) -> None:
    """让窗口对鼠标完全透明，且不抢焦点、不进任务栏。"""
    if not is_supported() or not hwnd:
        return
    style = _get_long(hwnd, GWL_EXSTYLE)
    style |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    _set_long(hwnd, GWL_EXSTYLE, style)


def embed_to(hwnd: int, target: int) -> bool:
    """把窗口挂到指定 WorkerW 上（首次嵌入，会设置穿透样式）。"""
    if not is_supported() or not hwnd or not target:
        return False
    make_click_through(hwnd)
    if not _set_parent(hwnd, target):
        log.warning("SetParent 失败：0x%X → 0x%X", hwnd, target)
        return False
    log.info("已嵌入桌面层 0x%X → 0x%X", hwnd, target)
    return True


def reparent_only(hwnd: int, target: int) -> bool:
    """纯粹 SetParent，不修改任何窗口样式。

    用于守护循环（父窗口漂移时频繁修复），避免每次改样式触发的
    DWM 重评估 / Qt 重校验导致的"闪动"。
    """
    if not is_supported() or not hwnd or not target:
        return False
    if not _set_parent(hwnd, target):
        log.debug("reparent_only SetParent 失败：0x%X → 0x%X", hwnd, target)
        return False
    return True


def _set_parent(hwnd: int, target: int) -> bool:
    """设置父窗口，并正确处理“原父窗口为空”的成功返回值。

    Win32 的 SetParent 成功时返回旧父窗口句柄，旧父窗口为空时也会返回
    NULL，因此不能单独用返回值判断成功。这里用 GetParent 二次确认。
    """
    previous = user32.SetParent(hwnd, target)
    return bool(previous or get_parent(hwnd) == target)


def embed(hwnd: int) -> tuple[bool, int]:
    """自动找一个 WorkerW 并嵌入（兼容旧调用）。"""
    if not is_supported() or not hwnd:
        return False, 0

    spawn_worker_w()
    progman = progman_handle()
    # 找窗口当前的屏幕坐标
    rect = _get_rect(hwnd)
    if not rect:
        return False, 0
    target = find_worker_w_for_rect(*rect)
    if not target:
        log.info("未找到 WorkerW，回退到 Progman")
        target = progman
    if not target:
        log.warning("未找到桌面窗口，嵌入失败")
        return False, 0

    if not embed_to(hwnd, target):
        return False, 0
    return True, target


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """窗口在屏幕坐标系下的物理像素矩形 ``(x, y, w, h)``。"""
    if not is_supported() or not hwnd:
        return (0, 0, 0, 0)
    rect = _get_rect(hwnd)
    return rect if rect else (0, 0, 0, 0)


def move_physical(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """按物理像素摆放窗口，并压到 Z 序最底。

    不使用 ``SWP_SHOWWINDOW``，避免触发 Qt 的 show 事件链条
    （Qt 可能在处理 show 时发现 Win32 父窗口与 Qt 父窗口不一致，
    进而把窗口重新 SetParent 回 NULL）。
    """
    if not is_supported() or not hwnd:
        return
    user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOACTIVATE)


def get_parent(hwnd: int) -> int:
    if not is_supported() or not hwnd:
        return 0
    # 壁纸窗口使用 Qt 的顶层弹窗（WS_POPUP）样式。对这种窗口，
    # user32.GetParent() 可能返回 0，即使 SetParent 已经成功；
    # GWLP_HWNDPARENT 才能稳定读到实际挂接的 WorkerW 句柄。
    return int(_get_long(hwnd, GWLP_HWNDPARENT) or 0)


def is_alive(hwnd: int) -> bool:
    if not is_supported() or not hwnd:
        return False
    return bool(user32.IsWindow(hwnd))


def enum_physical_monitors() -> list[tuple[int, int, int, int]]:
    """枚举所有物理显示器的矩形 ``(x, y, w, h)``（物理像素）。

    Qt 6 进程使用 Per-Monitor DPI awareness，``EnumDisplayMonitors`` 返回的
    矩形已经是原生像素。不要再按 DPI 二次换算，否则 225% 缩放的 4K 屏会
    得到错误尺寸。当前实机上 Qt geometry 为 1707×960，而这里稳定返回
    3840×2160，正适合离屏渲染和原生窗口定位。
    """
    if not is_supported():
        return []

    monitors: list[tuple[int, int, int, int]] = []

    def _enum(h_monitor, _hdc, lprc, _data) -> bool:
        rect = lprc.contents
        vw = rect.right - rect.left
        vh = rect.bottom - rect.top
        if vw <= 0 or vh <= 0:
            return True

        monitors.append((rect.left, rect.top, vw, vh))
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
    )
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum), 0)
    return monitors


def embed_and_place(hwnd: int) -> tuple[bool, int]:
    """嵌入桌面层并把窗口摆回它原来覆盖的屏幕区域（兼容旧调用）。

    新代码建议直接使用 :func:`find_worker_w_for_rect` + :func:`embed_to` +
    :func:`move_physical` 组合，以获得多显示器友好的表现。
    """
    if not is_supported() or not hwnd:
        return False, 0

    x, y, w, h = window_rect(hwnd)
    ok, parent = embed(hwnd)
    if not ok:
        return False, 0

    vx, vy = virtual_screen_origin()
    if w > 0 and h > 0:
        move_physical(hwnd, x - vx, y - vy, w, h)
    return True, parent


def detach(hwnd: int) -> None:
    """退出前把窗口从桌面层摘下来，避免 Explorer 残留。"""
    if not is_supported() or not hwnd:
        return
    try:
        user32.SetParent(hwnd, None)
    except OSError:
        pass


def refresh_desktop() -> None:
    """通知 Explorer 重绘桌面（退出时清掉残影）。"""
    if not is_supported():
        return
    progman = progman_handle()
    if progman:
        result = wintypes.DWORD()
        user32.SendMessageTimeoutW(progman, 0x0014, 0, 0, SMTO_NORMAL, 500,
                                   ctypes.byref(result))  # WM_ERASEBKGND
