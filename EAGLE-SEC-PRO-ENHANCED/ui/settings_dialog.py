from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QPushButton,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox, QGroupBox,
    QFormLayout, QDialogButtonBox, QColorDialog, QSlider, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from config.settings import settings
from core.logger import get_logger

logger = get_logger("settings_dialog")


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EAGLE-SEC PRO — Settings")
        self.setMinimumSize(700, 520)
        self.setModal(True)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        tabs.addTab(self._build_proxy_tab(), "Proxy")
        tabs.addTab(self._build_ui_tab(), "Interface")
        tabs.addTab(self._build_capture_tab(), "Capture")
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_notifications_tab(), "Notifications")

        layout.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._reset)
        layout.addWidget(btns)

    # ── Proxy ────────────────────────────────────────────────────────
    def _build_proxy_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.proxy_host = QLineEdit()
        form.addRow("Listen Host:", self.proxy_host)

        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        form.addRow("Listen Port:", self.proxy_port)

        self.proxy_timeout = QSpinBox()
        self.proxy_timeout.setRange(1, 300)
        self.proxy_timeout.setSuffix(" s")
        form.addRow("Timeout:", self.proxy_timeout)

        self.proxy_upstream = QLineEdit()
        self.proxy_upstream.setPlaceholderText("http://upstream:8080  (leave blank to disable)")
        form.addRow("Upstream Proxy:", self.proxy_upstream)

        self.proxy_ssl_strip = QCheckBox("Enable SSL Strip")
        form.addRow("SSL Strip:", self.proxy_ssl_strip)

        return w

    # ── UI ───────────────────────────────────────────────────────────
    def _build_ui_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        form = QFormLayout()
        self.ui_font_size = QSpinBox()
        self.ui_font_size.setRange(8, 24)
        form.addRow("Font Size:", self.ui_font_size)

        self.ui_font_family = QComboBox()
        self.ui_font_family.addItems(["Consolas", "Courier New", "Fira Code",
                                       "JetBrains Mono", "Cascadia Code"])
        form.addRow("Font Family:", self.ui_font_family)

        self.ui_animations = QCheckBox("Enable Animations")
        form.addRow("Animations:", self.ui_animations)

        self.ui_glassmorphism = QCheckBox("Glassmorphism Effects")
        form.addRow("Glassmorphism:", self.ui_glassmorphism)

        layout.addLayout(form)

        # Accent color picker
        acc_row = QHBoxLayout()
        acc_row.addWidget(QLabel("Accent Color:"))
        self.lbl_accent = QLabel()
        self.lbl_accent.setFixedSize(36, 24)
        self.lbl_accent.setAutoFillBackground(True)
        self.btn_pick_accent = QPushButton("Pick Color")
        acc_row.addWidget(self.lbl_accent)
        acc_row.addWidget(self.btn_pick_accent)
        acc_row.addStretch()
        layout.addLayout(acc_row)

        self.btn_pick_accent.clicked.connect(self._pick_accent)
        self._accent = settings.get("ui.accent_color", "#00D4FF")
        self._update_accent_preview()

        layout.addStretch()
        return w

    def _pick_accent(self):
        color = QColorDialog.getColor(QColor(self._accent), self, "Pick Accent Color")
        if color.isValid():
            self._accent = color.name()
            self._update_accent_preview()

    def _update_accent_preview(self):
        self.lbl_accent.setStyleSheet(
            f"background: {self._accent}; border: 1px solid #1e3a5f; border-radius: 3px;"
        )

    # ── Capture ──────────────────────────────────────────────────────
    def _build_capture_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.cap_log_body = QCheckBox("Log Request/Response Bodies")
        form.addRow("Log Bodies:", self.cap_log_body)

        self.cap_max_body = QSpinBox()
        self.cap_max_body.setRange(1024, 100 * 1024 * 1024)
        self.cap_max_body.setSingleStep(1024 * 1024)
        self.cap_max_body.setSuffix(" bytes")
        form.addRow("Max Body Size:", self.cap_max_body)

        self.cap_exclude = QLineEdit()
        self.cap_exclude.setPlaceholderText("*.png, *.jpg, *.gif (comma-separated)")
        form.addRow("Exclude Patterns:", self.cap_exclude)

        self.cap_include = QLineEdit()
        self.cap_include.setPlaceholderText("api.*, *.php (leave blank for all)")
        form.addRow("Include Patterns:", self.cap_include)

        return w

    # ── General ──────────────────────────────────────────────────────
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.gen_autosave = QSpinBox()
        self.gen_autosave.setRange(10, 3600)
        self.gen_autosave.setSuffix(" s")
        form.addRow("Autosave Interval:", self.gen_autosave)

        self.gen_max_history = QSpinBox()
        self.gen_max_history.setRange(100, 100000)
        self.gen_max_history.setSingleStep(100)
        form.addRow("Max History Items:", self.gen_max_history)

        self.gen_check_updates = QCheckBox("Check for Updates on Startup")
        form.addRow("Updates:", self.gen_check_updates)

        return w

    # ── Notifications ────────────────────────────────────────────────
    def _build_notifications_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.notif_enabled = QCheckBox("Enable Notifications")
        form.addRow("Notifications:", self.notif_enabled)

        self.notif_desktop = QCheckBox("Desktop Notifications")
        form.addRow("Desktop:", self.notif_desktop)

        self.notif_sound = QCheckBox("Sound Alerts")
        form.addRow("Sound:", self.notif_sound)

        return w

    # ── Load / Save / Reset ──────────────────────────────────────────
    def _load_values(self):
        self.proxy_host.setText(settings.get("proxy.host", "127.0.0.1"))
        self.proxy_port.setValue(settings.get("proxy.port", 8080))
        self.proxy_timeout.setValue(settings.get("proxy.timeout", 30))
        self.proxy_upstream.setText(settings.get("proxy.upstream_proxy", ""))
        self.proxy_ssl_strip.setChecked(settings.get("proxy.ssl_strip", False))

        self.ui_font_size.setValue(settings.get("ui.font_size", 12))
        idx = self.ui_font_family.findText(settings.get("ui.font_family", "Consolas"))
        if idx >= 0:
            self.ui_font_family.setCurrentIndex(idx)
        self.ui_animations.setChecked(settings.get("ui.animations_enabled", True))
        self.ui_glassmorphism.setChecked(settings.get("ui.glassmorphism", True))

        self.cap_log_body.setChecked(settings.get("capture.log_body", True))
        self.cap_max_body.setValue(settings.get("capture.max_body_size", 10485760))
        self.cap_exclude.setText(", ".join(settings.get("capture.exclude_filters", [])))
        self.cap_include.setText(", ".join(settings.get("capture.include_filters", [])))

        self.gen_autosave.setValue(settings.get("general.autosave_interval", 60))
        self.gen_max_history.setValue(settings.get("general.max_history", 10000))
        self.gen_check_updates.setChecked(settings.get("general.check_updates", True))

        self.notif_enabled.setChecked(settings.get("notifications.enabled", True))
        self.notif_desktop.setChecked(settings.get("notifications.desktop", True))
        self.notif_sound.setChecked(settings.get("notifications.sound", False))

    def _save(self):
        settings.set("proxy.host", self.proxy_host.text())
        settings.set("proxy.port", self.proxy_port.value())
        settings.set("proxy.timeout", self.proxy_timeout.value())
        settings.set("proxy.upstream_proxy", self.proxy_upstream.text())
        settings.set("proxy.ssl_strip", self.proxy_ssl_strip.isChecked())

        settings.set("ui.font_size", self.ui_font_size.value())
        settings.set("ui.font_family", self.ui_font_family.currentText())
        settings.set("ui.accent_color", self._accent)
        settings.set("ui.animations_enabled", self.ui_animations.isChecked())
        settings.set("ui.glassmorphism", self.ui_glassmorphism.isChecked())

        excludes = [p.strip() for p in self.cap_exclude.text().split(",") if p.strip()]
        includes = [p.strip() for p in self.cap_include.text().split(",") if p.strip()]
        settings.set("capture.log_body", self.cap_log_body.isChecked())
        settings.set("capture.max_body_size", self.cap_max_body.value())
        settings.set("capture.exclude_filters", excludes)
        settings.set("capture.include_filters", includes)

        settings.set("general.autosave_interval", self.gen_autosave.value())
        settings.set("general.max_history", self.gen_max_history.value())
        settings.set("general.check_updates", self.gen_check_updates.isChecked())

        settings.set("notifications.enabled", self.notif_enabled.isChecked())
        settings.set("notifications.desktop", self.notif_desktop.isChecked())
        settings.set("notifications.sound", self.notif_sound.isChecked())

        logger.info("Settings saved")
        self.settings_saved.emit()
        self.accept()

    def _reset(self):
        settings.reset()
        self._load_values()
        logger.info("Settings reset to defaults")
