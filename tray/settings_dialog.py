"""设置窗口。

界面按需求文档组织为四组：切换时间、显示内容、切换模式、其他。
所有改动通过 :class:`ConfigManager` 落盘，控制器会自动收到通知并即时生效。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from settings.config_manager import ConfigManager
import paths

from . import autostart

PRESET_INTERVALS = (10, 30, 60)

# (界面文字, 配置值)
FIT_OPTIONS = (
    ("铺满（推荐，按比例裁剪铺满全屏）", "fill"),
    ("适应（完整显示，可能留黑边）", "fit"),
    ("拉伸（不裁剪，比例可能变形）", "stretch"),
    ("居中（原始尺寸）", "center"),
    ("平铺", "tile"),
)

RESOLUTION_OPTIONS = (
    ("自动（跟随屏幕物理分辨率）", "auto"),
    ("1920 × 1080", "1920x1080"),
    ("2560 × 1440", "2560x1440"),
    ("3840 × 2160", "3840x2160"),
    ("1366 × 768", "1366x768"),
    ("1600 × 900", "1600x900"),
    ("3440 × 1440", "3440x1440"),
    ("自定义…", "custom"),
)

DEFAULT_CUSTOM_SIZE = (1920, 1080)


class SettingsDialog(QDialog):
    """壁纸设置对话框。"""

    def __init__(self, config: ConfigManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Mao Wallpaper · 设置")
        icon_path = paths.resource_path("assets/icon.png")
        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                self.setWindowIcon(icon)
        self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self._build_interval_group())
        layout.addWidget(self._build_content_group())
        layout.addWidget(self._build_mode_group())
        layout.addWidget(self._build_display_group())
        layout.addWidget(self._build_misc_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        layout.addWidget(buttons)

        self._load_from_config()

    # ================================================================ 构建界面
    def _build_interval_group(self) -> QGroupBox:
        box = QGroupBox("自动切换时间")
        row = QHBoxLayout(box)

        self._interval_combo = QComboBox()
        for sec in PRESET_INTERVALS:
            self._interval_combo.addItem(f"{sec} 秒", sec)
        self._interval_combo.addItem("自定义", -1)
        self._interval_combo.currentIndexChanged.connect(self._on_interval_changed)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(3, 3600)
        self._interval_spin.setSuffix(" 秒")

        row.addWidget(self._interval_combo, 1)
        row.addWidget(self._interval_spin, 1)
        return box

    def _build_content_group(self) -> QGroupBox:
        box = QGroupBox("显示内容")
        col = QVBoxLayout(box)
        self._cb_cn = QCheckBox("显示中文")
        self._cb_en = QCheckBox("显示英文")
        self._cb_src = QCheckBox("显示来源")
        self._cb_seal = QCheckBox("显示印章")
        self._cb_page = QCheckBox("显示页码")
        for cb in (self._cb_cn, self._cb_en, self._cb_src, self._cb_seal, self._cb_page):
            col.addWidget(cb)
        return box

    def _build_mode_group(self) -> QGroupBox:
        box = QGroupBox("切换模式")
        col = QVBoxLayout(box)
        self._rb_sequential = QRadioButton("顺序播放")
        self._rb_random = QRadioButton("随机播放")
        col.addWidget(self._rb_sequential)
        col.addWidget(self._rb_random)
        return box

    def _build_display_group(self) -> QGroupBox:
        box = QGroupBox("显示与分辨率")
        form = QFormLayout(box)

        self._fit_combo = QComboBox()
        for label, value in FIT_OPTIONS:
            self._fit_combo.addItem(label, value)
        form.addRow("显示方式", self._fit_combo)

        self._res_combo = QComboBox()
        for label, value in RESOLUTION_OPTIONS:
            self._res_combo.addItem(label, value)
        self._res_combo.currentIndexChanged.connect(self._on_resolution_changed)

        self._res_w = QSpinBox()
        self._res_w.setRange(640, 15360)
        self._res_h = QSpinBox()
        self._res_h.setRange(480, 8640)

        size_row = QHBoxLayout()
        size_row.setContentsMargins(0, 0, 0, 0)
        size_row.addWidget(self._res_w)
        size_row.addWidget(QLabel("×"))
        size_row.addWidget(self._res_h)
        size_row.addStretch(1)
        size_box = QWidget()
        size_box.setLayout(size_row)
        form.addRow("自定义尺寸", size_box)

        hint = QLabel(
            "「自动」会直接读屏幕物理分辨率，换电脑无需改动；"
            "手动指定只在自动识别不准、或需要给别的机器预先出图时使用。"
            "尺寸与屏幕比例不同时，铺满会裁掉边缘。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #777;")
        form.addRow(hint)
        return box

    def _build_misc_group(self) -> QGroupBox:
        box = QGroupBox("其他")
        form = QFormLayout(box)

        self._cb_anim = QCheckBox("启用过场动画")
        self._cb_page_turn = QCheckBox("启用翻页效果")
        self._cb_drift = QCheckBox("纸张缓慢浮动")
        self._cb_all_screens = QCheckBox("覆盖所有显示器（取消则只在副屏显示）")
        self._cb_autostart = QCheckBox("开机自动启动")
        self._cb_autostart.setEnabled(autostart.is_supported())

        self._anim_spin = QSpinBox()
        self._anim_spin.setRange(4, 100)
        self._anim_spin.setSuffix(" ×0.1 秒")

        self._size_spin = QSpinBox()
        self._size_spin.setRange(20, 160)
        self._size_spin.setSuffix(" ‰ 屏高")

        form.addRow(self._cb_anim)
        form.addRow(self._cb_page_turn)
        form.addRow("动画时长", self._anim_spin)
        form.addRow(self._cb_drift)
        form.addRow(self._cb_all_screens)
        form.addRow(self._cb_autostart)
        form.addRow("中文字号", self._size_spin)

        hint = QLabel("语录内容可直接编辑 data/quotes.json，保存后数秒内自动生效。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #777;")
        form.addRow(hint)

        open_btn = QPushButton("打开语录文件所在目录")
        open_btn.clicked.connect(self._open_quotes_dir)
        form.addRow(open_btn)
        return box

    # ================================================================ 数据同步
    def _load_from_config(self) -> None:
        cfg = self._config
        interval = int(cfg.get("time_interval"))
        if interval in PRESET_INTERVALS:
            self._interval_combo.setCurrentIndex(PRESET_INTERVALS.index(interval))
        else:
            self._interval_combo.setCurrentIndex(len(PRESET_INTERVALS))
        self._interval_spin.setValue(interval)
        self._on_interval_changed()

        self._cb_cn.setChecked(cfg.get("show_cn"))
        self._cb_en.setChecked(cfg.get("show_en"))
        self._cb_src.setChecked(cfg.get("show_source"))
        self._cb_seal.setChecked(cfg.get("show_seal"))
        self._cb_page.setChecked(cfg.get("show_page_number"))

        if cfg.get("play_mode") == "sequential":
            self._rb_sequential.setChecked(True)
        else:
            self._rb_random.setChecked(True)

        self._cb_anim.setChecked(cfg.get("animation_enabled"))
        self._cb_page_turn.setChecked(cfg.get("page_turn_enabled"))
        self._cb_drift.setChecked(cfg.get("paper_drift"))
        self._cb_all_screens.setChecked(cfg.get("all_screens"))
        self._anim_spin.setValue(int(round(float(cfg.get("animation_duration")) * 10)))
        self._size_spin.setValue(int(round(float(cfg.get("cn_size_ratio")) * 1000)))
        self._cb_autostart.setChecked(autostart.is_enabled())

        fit_index = self._fit_combo.findData(cfg.get("wallpaper_fit"))
        self._fit_combo.setCurrentIndex(fit_index if fit_index >= 0 else 0)

        render_size = str(cfg.get("render_size") or "auto")
        width, height = ConfigManager.parse_render_size(render_size) or DEFAULT_CUSTOM_SIZE
        self._res_w.setValue(width)
        self._res_h.setValue(height)
        res_index = self._res_combo.findData(render_size)
        if res_index < 0:
            res_index = self._res_combo.findData("custom")
        self._res_combo.setCurrentIndex(res_index if res_index >= 0 else 0)
        self._on_resolution_changed()

    def _on_interval_changed(self) -> None:
        data = self._interval_combo.currentData()
        custom = data == -1
        self._interval_spin.setEnabled(custom)
        if not custom:
            self._interval_spin.setValue(int(data))

    def _on_resolution_changed(self) -> None:
        custom = self._res_combo.currentData() == "custom"
        self._res_w.setEnabled(custom)
        self._res_h.setEnabled(custom)

    def _selected_render_size(self) -> str:
        data = self._res_combo.currentData()
        if data == "custom":
            return f"{self._res_w.value()}x{self._res_h.value()}"
        return str(data)

    def apply(self) -> None:
        values = {
            "time_interval": self._interval_spin.value(),
            "show_cn": self._cb_cn.isChecked(),
            "show_en": self._cb_en.isChecked(),
            "show_source": self._cb_src.isChecked(),
            "show_seal": self._cb_seal.isChecked(),
            "show_page_number": self._cb_page.isChecked(),
            "play_mode": "sequential" if self._rb_sequential.isChecked() else "random",
            "animation_enabled": self._cb_anim.isChecked(),
            "page_turn_enabled": self._cb_page_turn.isChecked(),
            "paper_drift": self._cb_drift.isChecked(),
            "all_screens": self._cb_all_screens.isChecked(),
            "animation_duration": self._anim_spin.value() / 10.0,
            "cn_size_ratio": self._size_spin.value() / 1000.0,
            "wallpaper_fit": self._fit_combo.currentData(),
            "render_size": self._selected_render_size(),
            "autostart": self._cb_autostart.isChecked(),
        }
        self._config.update(values)

        if autostart.is_supported():
            autostart.set_enabled(self._cb_autostart.isChecked())

    def _on_accept(self) -> None:
        self.apply()
        self.accept()

    def _open_quotes_dir(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        import paths

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.quotes_path().parent)))
