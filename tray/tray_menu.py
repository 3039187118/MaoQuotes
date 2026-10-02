"""系统托盘。

菜单结构（与需求文档一致）：

    Mao Wallpaper
    ├── 下一条语录
    ├── 上一条语录
    ├── 暂停动画 / 恢复动画
    ├── 设置
    └── 退出程序
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

import paths
from settings.config_manager import ConfigManager
from wallpaper.controller import WallpaperController

from .settings_dialog import SettingsDialog

log = logging.getLogger(__name__)

ICON_REL = "assets/icon.png"


def _fallback_icon() -> QIcon:
    """没有图标素材时，现画一个朱红小印。"""
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(150, 42, 36))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 8, 8)
    font = QFont()
    font.setPixelSize(int(size * 0.56))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(250, 245, 235))
    painter.drawText(pix.rect(), int(Qt.AlignmentFlag.AlignCenter), "毛")
    painter.end()
    return QIcon(pix)


def load_icon() -> QIcon:
    icon_file = paths.resource_path(ICON_REL)
    if icon_file.is_file():
        icon = QIcon(str(icon_file))
        if not icon.isNull():
            return icon
    return _fallback_icon()


class TrayMenu(QObject):
    """托盘图标与菜单。"""

    exitRequested = Signal()

    def __init__(self, controller: WallpaperController, config: ConfigManager,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._config = config
        self._settings_dialog: SettingsDialog | None = None

        self._tray = QSystemTrayIcon(load_icon(), self)
        self._tray.setToolTip("Mao Quotes Live Wallpaper")

        self._menu = QMenu()
        self._act_next = QAction("下一条语录", self._menu)
        self._act_prev = QAction("上一条语录", self._menu)
        self._act_pause = QAction("暂停动画", self._menu)
        self._act_settings = QAction("设置…", self._menu)
        self._act_reload = QAction("重新载入语录", self._menu)
        self._act_exit = QAction("退出程序", self._menu)

        self._act_next.triggered.connect(
            lambda: self._controller.next_quote(reason="tray-menu")
        )
        self._act_prev.triggered.connect(
            lambda: self._controller.prev_quote(reason="tray-menu")
        )
        self._act_pause.triggered.connect(self._controller.toggle_paused)
        self._act_settings.triggered.connect(self.open_settings)
        self._act_reload.triggered.connect(self._controller.reload_quotes)
        self._act_exit.triggered.connect(self._confirm_exit)

        self._menu.addAction(self._act_next)
        self._menu.addAction(self._act_prev)
        self._menu.addSeparator()
        self._menu.addAction(self._act_pause)
        self._menu.addAction(self._act_reload)
        self._menu.addSeparator()
        self._menu.addAction(self._act_settings)
        self._menu.addSeparator()
        self._menu.addAction(self._act_exit)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

        controller.pausedChanged.connect(self._on_paused_changed)
        controller.quoteChanged.connect(self._on_quote_changed)

    # ================================================================ 显示
    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def notify(self, title: str, message: str) -> None:
        if self._tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(title, message, load_icon(), 3000)

    # ================================================================ 交互
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # 单击托盘图标不执行切换，避免误触导致“未到时间就换内容”。
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def _confirm_exit(self) -> None:
        answer = QMessageBox.question(
            None,
            "退出 Mao Wallpaper",
            "确定要退出桌面壁纸程序吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            log.info("用户确认退出程序")
            self.exitRequested.emit()

    def open_settings(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self._config)
            self._settings_dialog.finished.connect(self._on_settings_closed)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_settings_closed(self, *_args) -> None:
        if self._settings_dialog is not None:
            self._settings_dialog.deleteLater()
            self._settings_dialog = None

    # ================================================================ 状态同步
    def _on_paused_changed(self, paused: bool) -> None:
        self._act_pause.setText("恢复动画" if paused else "暂停动画")

    def _on_quote_changed(self, quote) -> None:
        if quote is None:
            return
        text = quote.cn or quote.en
        if len(text) > 24:
            text = text[:24] + "…"
        self._tray.setToolTip(f"Mao Quotes Live Wallpaper\n{text}")
