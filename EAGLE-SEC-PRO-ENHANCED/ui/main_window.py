import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar, QMenuBar, QMenu, QToolBar,
    QFileDialog, QMessageBox, QDialog, QProgressBar, QFrame,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont, QColor, QIcon, QKeySequence

from core.proxy_engine import ProxyEngine
from core.session_manager import SessionManager
from core.certificate_manager import CertificateManager
from database.db_manager import DatabaseManager
from plugins.plugin_manager import PluginManager
from modules.site_mapper import SiteMapper

from ui.proxy_tab import ProxyTab
from ui.repeater_tab import RepeaterTab
from ui.comparer_tab import ComparerTab
from ui.decoder_tab import DecoderTab
from ui.sitemap_tab import SiteMapTab
from ui.crawler_tab import CrawlerTab
from ui.reports_tab import ReportsTab
from ui.notifications import NotificationManager
from ui.settings_dialog import SettingsDialog
from ui.eagle_banner import EagleBanner

from config.settings import settings
from core.logger import get_logger

logger = get_logger("main_window")


class AutoSaveWorker(QThread):
    def __init__(self, interval_s: int, callback):
        super().__init__()
        self.interval_s = interval_s
        self.callback = callback
        self._running = True

    def run(self):
        while self._running:
            time.sleep(self.interval_s)
            try:
                self.callback()
            except Exception as e:
                logger.error("Autosave error: %s", e)

    def stop(self):
        self._running = False


class StatusLED(QLabel):
    def __init__(self, parent=None):
        super().__init__("●", parent)
        self.setStyleSheet("color: #FF4444; font-size: 16px;")

    def set_active(self, active: bool):
        color = "#00FF88" if active else "#FF4444"
        self.setStyleSheet(f"color: {color}; font-size: 16px;")


class MainWindow(QMainWindow):
    VERSION = "1.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"EAGLE-SEC PRO v{self.VERSION}  —  Professional Security Testing Suite")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        # Core subsystems
        self.db = DatabaseManager()
        self.proxy_engine = ProxyEngine(
            host=settings.get("proxy.host", "127.0.0.1"),
            port=settings.get("proxy.port", 8080),
        )
        self.session_mgr = SessionManager()
        self.cert_mgr = CertificateManager()
        self.plugin_mgr = PluginManager()

        # Autosave
        self._autosave_worker: Optional[AutoSaveWorker] = None
        self._current_session = self.session_mgr.new_session("Default Session")

        # Notifications
        self.notif: Optional[NotificationManager] = None  # initialized after show()

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_proxy_callbacks()
        self._start_autosave()
        self._load_plugins()

        # Init CA
        QTimer.singleShot(500, self._init_ca)

        logger.info("MainWindow initialized")

    def show(self):
        super().show()
        self.notif = NotificationManager(self)

    # ── UI Setup ─────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header banner — animated EagleBanner replaces old static header
        self.eagle_banner = EagleBanner()
        layout.addWidget(self.eagle_banner)

        # Legacy header (hidden, keeps status LED references alive)
        header = self._build_header()
        header.setVisible(False)
        layout.addWidget(header)

        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)

        # Create tabs
        self.proxy_tab = ProxyTab(self.proxy_engine)
        self.repeater_tab = RepeaterTab()
        self.comparer_tab = ComparerTab()
        self.decoder_tab = DecoderTab()
        self.sitemap_tab = SiteMapTab()
        self.crawler_tab = CrawlerTab()
        self.reports_tab = ReportsTab(self.db)

        tab_defs = [
            ("⚡ Proxy", self.proxy_tab),
            ("↻ Repeater", self.repeater_tab),
            ("⟺ Comparer", self.comparer_tab),
            ("⌘ Decoder", self.decoder_tab),
            ("🗺 Site Map", self.sitemap_tab),
            ("🕷 Crawler", self.crawler_tab),
            ("📊 Reports", self.reports_tab),
        ]

        for label, widget in tab_defs:
            self.tabs.addTab(widget, label)

        layout.addWidget(self.tabs)

        # Wire cross-tab signals
        self.proxy_tab.send_to_repeater.connect(self.repeater_tab.load_request)
        self.proxy_tab.send_to_comparer.connect(self.comparer_tab.load_request)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("glass")
        header.setFixedHeight(52)
        header.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "stop:0 #060d1f, stop:0.5 #0a0e1a, stop:1 #060d1f);"
            "border-bottom: 1px solid #1e3a5f; }"
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)

        # Logo text
        logo = QLabel("⚡ EAGLE-SEC PRO")
        logo.setStyleSheet(
            "color: #00D4FF; font-size: 16px; font-weight: bold; font-family: Consolas;"
            "letter-spacing: 3px;"
        )
        layout.addWidget(logo)

        # Version badge
        ver = QLabel(f"v{self.VERSION}")
        ver.setStyleSheet(
            "color: #1e3a5f; background: #0d1b2e; border: 1px solid #1e3a5f;"
            "border-radius: 3px; padding: 1px 6px; font-size: 10px; font-family: Consolas;"
        )
        layout.addWidget(ver)

        layout.addStretch()

        # Proxy status indicator
        self.proxy_led = StatusLED()
        self.lbl_proxy_status = QLabel("Proxy: Stopped")
        self.lbl_proxy_status.setStyleSheet("color: #64748b; font-size: 11px; font-family: Consolas;")
        layout.addWidget(self.proxy_led)
        layout.addWidget(self.lbl_proxy_status)

        layout.addSpacing(20)

        # Session info
        self.lbl_session = QLabel(f"Session: {self._current_session.name}")
        self.lbl_session.setStyleSheet("color: #475569; font-size: 10px; font-family: Consolas;")
        layout.addWidget(self.lbl_session)

        layout.addSpacing(20)

        # Quick action buttons in header
        btn_settings = QPushButton("⚙")
        btn_settings.setToolTip("Settings")
        btn_settings.setFixedSize(32, 32)
        btn_settings.setStyleSheet(
            "QPushButton { background: transparent; color: #64748b; border: none; font-size: 16px; }"
            "QPushButton:hover { color: #00D4FF; }"
        )
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        return header

    # ── Menu ─────────────────────────────────────────────────────────
    def _setup_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self._action("New Session", self._new_session, "Ctrl+N"))
        file_menu.addAction(self._action("Open Session...", self._open_session, "Ctrl+O"))
        file_menu.addAction(self._action("Save Session", self._save_session, "Ctrl+S"))
        file_menu.addSeparator()
        file_menu.addAction(self._action("Import Requests (JSON)...", self._import_requests))
        file_menu.addAction(self._action("Export Session (JSON)...", self._export_session))
        file_menu.addSeparator()
        file_menu.addAction(self._action("Settings...", self._open_settings, "Ctrl+,"))
        file_menu.addSeparator()
        file_menu.addAction(self._action("Exit", self.close, "Alt+F4"))

        # Proxy
        proxy_menu = menubar.addMenu("Proxy")
        self.act_start_proxy = self._action("Start Proxy", self._start_proxy_from_menu)
        self.act_stop_proxy = self._action("Stop Proxy", self._stop_proxy_from_menu)
        self.act_stop_proxy.setEnabled(False)
        proxy_menu.addAction(self.act_start_proxy)
        proxy_menu.addAction(self.act_stop_proxy)
        proxy_menu.addSeparator()
        proxy_menu.addAction(self._action("Clear History", self._clear_proxy_history, "Ctrl+L"))
        proxy_menu.addSeparator()
        proxy_menu.addAction(self._action("Export CA Certificate...", self._export_ca_cert))
        proxy_menu.addAction(self._action("View CA Certificate...", self._view_ca_cert))

        # Tools
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self._action("Generate Report (HTML)", lambda: self._quick_report("HTML")))
        tools_menu.addAction(self._action("Generate Report (JSON)", lambda: self._quick_report("JSON")))
        tools_menu.addAction(self._action("Generate Report (PDF)", lambda: self._quick_report("PDF")))
        tools_menu.addSeparator()
        tools_menu.addAction(self._action("Manage Plugins...", self._manage_plugins))
        tools_menu.addSeparator()
        tools_menu.addAction(self._action("Clear Database", self._clear_database))
        tools_menu.addAction(self._action("Vacuum Database", lambda: self.db.vacuum()))

        # View
        view_menu = menubar.addMenu("View")
        view_menu.addAction(self._action("Proxy Tab", lambda: self.tabs.setCurrentIndex(0), "Alt+1"))
        view_menu.addAction(self._action("Repeater Tab", lambda: self.tabs.setCurrentIndex(1), "Alt+2"))
        view_menu.addAction(self._action("Comparer Tab", lambda: self.tabs.setCurrentIndex(2), "Alt+3"))
        view_menu.addAction(self._action("Decoder Tab", lambda: self.tabs.setCurrentIndex(3), "Alt+4"))
        view_menu.addAction(self._action("Site Map Tab", lambda: self.tabs.setCurrentIndex(4), "Alt+5"))
        view_menu.addAction(self._action("Crawler Tab", lambda: self.tabs.setCurrentIndex(5), "Alt+6"))
        view_menu.addAction(self._action("Reports Tab", lambda: self.tabs.setCurrentIndex(6), "Alt+7"))

        # Help
        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self._action("About EAGLE-SEC PRO", self._show_about))
        help_menu.addAction(self._action("View Logs", self._view_logs))

    @staticmethod
    def _action(label: str, slot, shortcut: str = None) -> QAction:
        act = QAction(label)
        if slot:
            act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        return act

    # ── Status Bar ───────────────────────────────────────────────────
    def _setup_statusbar(self):
        sb = self.statusBar()
        self.lbl_req_count = QLabel("Requests: 0")
        self.lbl_req_count.setStyleSheet("color: #64748b; padding: 0 12px;")
        self.lbl_time = QLabel("")
        self.lbl_time.setStyleSheet("color: #64748b; padding: 0 12px;")
        sb.addPermanentWidget(self.lbl_req_count)
        sb.addPermanentWidget(self.lbl_time)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # Request counter timer
        self._counter_timer = QTimer(self)
        self._counter_timer.timeout.connect(self._update_req_count)
        self._counter_timer.start(500)

    def _update_clock(self):
        self.lbl_time.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    def _update_req_count(self):
        count = self.proxy_engine.request_count
        self.lbl_req_count.setText(f"Requests: {count:,}")

    # ── Proxy Callbacks ──────────────────────────────────────────────
    def _setup_proxy_callbacks(self):
        def on_request(req):
            self._current_session.add_request(req.to_dict())
            self.sitemap_tab.add_request(req.to_dict())

        def on_response(req):
            pass

        self.proxy_engine.on_request(on_request)
        self.proxy_engine.on_response(on_response)

    def _update_proxy_banner(self, active: bool):
        """Sync proxy state to the animated banner."""
        self.proxy_led.set_active(active)
        self.lbl_proxy_status.setText("Proxy: Active" if active else "Proxy: Stopped")
        if hasattr(self, "eagle_banner"):
            self.eagle_banner.set_proxy_status(active)

    # ── Actions ──────────────────────────────────────────────────────
    def _start_proxy_from_menu(self):
        self.tabs.setCurrentIndex(0)
        self.proxy_tab._start_proxy()

    def _stop_proxy_from_menu(self):
        self.proxy_tab._stop_proxy()

    def _new_session(self):
        self._current_session = self.session_mgr.new_session("New Session")
        self.lbl_session.setText(f"Session: {self._current_session.name}")
        if self.notif:
            self.notif.success("New session created")

    def _open_session(self):
        sessions = self.session_mgr.list_sessions()
        if not sessions:
            QMessageBox.information(self, "Sessions", "No saved sessions found")
            return
        # Simple selection dialog
        from PyQt6.QtWidgets import QInputDialog
        names = [f"{s['name']} ({s['request_count']} reqs)" for s in sessions]
        choice, ok = QInputDialog.getItem(self, "Open Session", "Select session:", names, 0, False)
        if ok and choice:
            idx = names.index(choice)
            sid = sessions[idx]["session_id"]
            session = self.session_mgr.load_session(sid)
            if session:
                self._current_session = session
                self.lbl_session.setText(f"Session: {session.name}")
                if self.notif:
                    self.notif.success(f"Loaded session: {session.name}")

    def _save_session(self):
        self.session_mgr.save_session(self._current_session)
        self.statusBar().showMessage("Session saved", 2000)

    def _import_requests(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Requests", "", "JSON (*.json)")
        if not path:
            return
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            reqs = data if isinstance(data, list) else data.get("requests", [])
            for req in reqs:
                self._current_session.add_request(req)
            self.reports_tab.set_requests(reqs)
            if self.notif:
                self.notif.success(f"Imported {len(reqs)} requests")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def _export_session(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Session", "session.json", "JSON (*.json)")
        if not path:
            return
        import json
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._current_session.to_dict(), f, indent=2)
            if self.notif:
                self.notif.success(f"Session exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.settings_saved.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self):
        if self.notif:
            self.notif.success("Settings applied")

    def _export_ca_cert(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CA Certificate", "eagle_ca.crt",
                                               "Certificate (*.crt *.pem)")
        if path:
            import shutil
            shutil.copy2(self.cert_mgr.CA_CERT_FILE, path)
            if self.notif:
                self.notif.success(f"CA Certificate exported to {path}")

    def _view_ca_cert(self):
        pem = self.cert_mgr.get_ca_cert_pem()
        dlg = QDialog(self)
        dlg.setWindowTitle("CA Certificate")
        dlg.setMinimumSize(600, 400)
        layout = QVBoxLayout(dlg)
        from PyQt6.QtWidgets import QTextEdit
        txt = QTextEdit()
        txt.setFont(QFont("Consolas", 10))
        txt.setReadOnly(True)
        txt.setPlainText(pem or "CA not initialized yet")
        layout.addWidget(txt)
        dlg.exec()

    def _quick_report(self, fmt: str):
        reqs = [r.to_dict() if hasattr(r, "to_dict") else r
                for r in self._current_session.requests]
        if not reqs:
            if self.notif:
                self.notif.warning("No requests to report")
            return
        self.reports_tab.set_requests(reqs)
        self.tabs.setCurrentIndex(6)
        self.reports_tab.cmb_format.setCurrentText(fmt)
        self.reports_tab._generate()

    def _manage_plugins(self):
        plugins = self.plugin_mgr.get_plugins()
        dlg = QDialog(self)
        dlg.setWindowTitle("Plugin Manager")
        dlg.setMinimumSize(700, 400)
        layout = QVBoxLayout(dlg)

        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Name", "Version", "Author", "Enabled", "Status"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for p in plugins:
            row = table.rowCount()
            table.insertRow(row)
            for col, val in enumerate([p.get("name",""), p.get("version",""),
                                        p.get("author",""),
                                        "Yes" if p.get("enabled") else "No",
                                        p.get("error","OK") or "OK"]):
                item = QTableWidgetItem(str(val))
                if col == 3:
                    item.setForeground(QColor("#00FF88") if val == "Yes" else QColor("#FF4444"))
                table.setItem(row, col, item)

        layout.addWidget(table)

        if not plugins:
            layout.addWidget(QLabel("No plugins installed. Place plugin folders in the plugins/ directory."))

        btns = QHBoxLayout()
        btn_refresh = QPushButton("↻ Reload All")
        btn_refresh.clicked.connect(lambda: (self.plugin_mgr.discover_and_load(), dlg.accept()))
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        btns.addWidget(btn_refresh)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)
        dlg.exec()

    def _clear_proxy_history(self):
        self.proxy_tab._clear()
        if self.notif:
            self.notif.info("Proxy history cleared")

    def _clear_database(self):
        reply = QMessageBox.question(
            self, "Clear Database",
            "This will delete ALL stored requests, reports, and logs. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_requests()
            if self.notif:
                self.notif.warning("Database cleared")

    def _view_logs(self):
        from pathlib import Path
        log_path = Path(__file__).resolve().parent.parent / "logs" / "eagle_sec.log"
        dlg = QDialog(self)
        dlg.setWindowTitle("Application Logs")
        dlg.setMinimumSize(800, 500)
        layout = QVBoxLayout(dlg)
        from PyQt6.QtWidgets import QTextEdit
        txt = QTextEdit()
        txt.setFont(QFont("Consolas", 9))
        txt.setReadOnly(True)
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8", errors="replace")
            txt.setPlainText(content[-50000:])
            txt.verticalScrollBar().setValue(txt.verticalScrollBar().maximum())
        else:
            txt.setPlainText("No log file found")
        layout.addWidget(txt)
        dlg.exec()

    def _show_about(self):
        QMessageBox.information(
            self, "About EAGLE-SEC PRO",
            f"""<h2 style='color:#00D4FF'>EAGLE-SEC PRO v{self.VERSION}</h2>
<p>Professional Web Security Testing Suite</p>
<p><b>Features:</b></p>
<ul>
<li>HTTP/HTTPS Proxy with Intercept</li>
<li>Request Repeater &amp; Comparer</li>
<li>Decoder (Base64, URL, Hex, JWT, Hash)</li>
<li>Site Mapper &amp; Web Crawler</li>
<li>HTML / PDF / JSON Report Generation</li>
<li>Plugin System</li>
<li>SQLite Session Management</li>
</ul>
<p style='color:#64748b'>Built with Python 3.12 + PyQt6</p>"""
        )

    # ── Autosave ─────────────────────────────────────────────────────
    def _start_autosave(self):
        interval = settings.get("general.autosave_interval", 60)
        self._autosave_worker = AutoSaveWorker(interval, self._autosave)
        self._autosave_worker.start()

    def _autosave(self):
        try:
            self.session_mgr.save_session(self._current_session)
            logger.debug("Autosave complete")
        except Exception as e:
            logger.error("Autosave failed: %s", e)

    # ── Certificate Init ─────────────────────────────────────────────
    def _init_ca(self):
        success = self.cert_mgr.ensure_ca()
        if success:
            logger.info("CA certificate ready")
        else:
            logger.warning("CA init failed — HTTPS interception may not work")

    # ── Plugin Loading ───────────────────────────────────────────────
    def _load_plugins(self):
        try:
            loaded = self.plugin_mgr.discover_and_load()
            if loaded:
                logger.info("Loaded %d plugin(s)", len(loaded))
        except Exception as e:
            logger.error("Plugin loading error: %s", e)

    # ── Sync proxy data to reports ────────────────────────────────────
    def _sync_requests_to_reports(self):
        reqs = [r.to_dict() if hasattr(r, "to_dict") else r
                for r in self._current_session.requests]
        self.reports_tab.set_requests(reqs)

    # ── Close event ──────────────────────────────────────────────────
    def closeEvent(self, event):
        # Stop proxy
        if self.proxy_engine.running:
            self.proxy_engine.stop()

        # Stop autosave worker
        if self._autosave_worker:
            self._autosave_worker.stop()
            self._autosave_worker.wait(2000)

        # Save session
        try:
            self.session_mgr.save_session(self._current_session)
        except Exception:
            pass

        logger.info("Application closing")
        event.accept()
