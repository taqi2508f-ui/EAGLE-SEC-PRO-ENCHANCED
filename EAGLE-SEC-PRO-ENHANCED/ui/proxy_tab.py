import json
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit,
    QComboBox, QCheckBox, QGroupBox, QTabWidget, QFrame, QSpinBox,
    QHeaderView, QToolBar, QStatusBar, QAbstractItemView, QSizePolicy,
    QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QAction

from core.proxy_engine import ProxyEngine, HttpRequest
from core.logger import get_logger

logger = get_logger("proxy_tab")


class ProxyWorkerSignals(QThread):
    request_received = pyqtSignal(dict)
    response_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)


class RequestTableWidget(QTableWidget):
    COLUMNS = ["#", "Method", "Host", "Path", "Status", "Length", "Duration", "Time"]
    COL_WIDTHS = [40, 70, 200, 300, 60, 80, 80, 80]

    METHOD_COLORS = {
        "GET": "#38bdf8", "POST": "#4ade80", "PUT": "#fbbf24",
        "DELETE": "#f87171", "PATCH": "#a78bfa", "OPTIONS": "#94a3b8",
        "HEAD": "#e2e8f0", "CONNECT": "#00D4FF",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(False)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        for i, w in enumerate(self.COL_WIDTHS):
            self.setColumnWidth(i, w)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._rows: list[dict] = []

    def add_request(self, req: dict):
        self._rows.append(req)
        row = self.rowCount()
        self.insertRow(row)
        resp = req.get("response") or {}
        status = resp.get("status_code", "")
        body = resp.get("body", "")
        length = len(body) if body else 0
        ts = datetime.fromtimestamp(req.get("timestamp", time.time())).strftime("%H:%M:%S")

        values = [
            str(row + 1),
            req.get("method", ""),
            req.get("host", ""),
            (req.get("path", "") or "")[:80],
            str(status) if status else "",
            f"{length}B" if length else "",
            f"{req.get('duration_ms', 0):.0f}ms",
            ts,
        ]

        method = req.get("method", "")
        method_color = self.METHOD_COLORS.get(method, "#e2e8f0")
        status_color = self._status_color(status)

        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setData(Qt.ItemDataRole.UserRole, req)
            if col == 1:
                item.setForeground(QColor(method_color))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            elif col == 4:
                item.setForeground(QColor(status_color))
            self.setItem(row, col, item)

        if self.rowCount() > 1:
            self.scrollToBottom()

    def get_request_at(self, row: int) -> Optional[dict]:
        item = self.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def clear_all(self):
        self.setRowCount(0)
        self._rows.clear()

    def filter_rows(self, text: str):
        text = text.lower()
        for row in range(self.rowCount()):
            match = False
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.setRowHidden(row, not match if text else False)

    @staticmethod
    def _status_color(code) -> str:
        if not code:
            return "#94a3b8"
        try:
            c = int(code)
            if 200 <= c < 300: return "#4ade80"
            if 300 <= c < 400: return "#fbbf24"
            if 400 <= c < 500: return "#f87171"
            if 500 <= c < 600: return "#ff6b6b"
        except Exception:
            pass
        return "#94a3b8"


class RequestDetailPanel(QWidget):
    send_to_repeater = pyqtSignal(dict)
    send_to_comparer = pyqtSignal(dict)
    forward_request = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Action bar
        action_bar = QHBoxLayout()
        self.btn_repeater = QPushButton("→ Repeater")
        self.btn_repeater.setObjectName("btn_success")
        self.btn_comparer = QPushButton("→ Comparer")
        self.btn_comparer.setObjectName("btn_warn")
        self.btn_copy_curl = QPushButton("Copy cURL")
        self.btn_forward = QPushButton("⏩ Forward")
        self.btn_forward.setObjectName("btn_forward")
        self.btn_forward.setMaximumHeight(28)
        self.btn_forward.setToolTip("Forward this request through the proxy")
        self.btn_forward.setStyleSheet(
            "QPushButton#btn_forward {"
            "  background-color: #0e7490;"
            "  color: #e0f7fa;"
            "  border: 1px solid #06b6d4;"
            "  border-radius: 4px;"
            "  padding: 2px 10px;"
            "  font-weight: bold;"
            "}"
            "QPushButton#btn_forward:hover {"
            "  background-color: #0891b2;"
            "  border-color: #22d3ee;"
            "}"
            "QPushButton#btn_forward:pressed {"
            "  background-color: #164e63;"
            "}"
        )

        for btn in [self.btn_repeater, self.btn_comparer, self.btn_copy_curl]:
            btn.setMaximumHeight(28)
            action_bar.addWidget(btn)
        action_bar.addWidget(self.btn_forward)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        tabs = QTabWidget()
        tabs.setMaximumHeight(999999)

        # Request tab
        self.req_text = QTextEdit()
        self.req_text.setReadOnly(True)
        self.req_text.setFont(QFont("Consolas", 10))
        tabs.addTab(self.req_text, "Request")

        # Response tab
        self.resp_text = QTextEdit()
        self.resp_text.setReadOnly(True)
        self.resp_text.setFont(QFont("Consolas", 10))
        tabs.addTab(self.resp_text, "Response")

        # Headers tab
        self.headers_text = QTextEdit()
        self.headers_text.setReadOnly(True)
        self.headers_text.setFont(QFont("Consolas", 10))
        tabs.addTab(self.headers_text, "Headers")

        layout.addWidget(tabs)

        self.btn_repeater.clicked.connect(self._send_to_repeater)
        self.btn_comparer.clicked.connect(self._send_to_comparer)
        self.btn_copy_curl.clicked.connect(self._copy_curl)
        self.btn_forward.clicked.connect(self._forward_request)

        self._current: Optional[dict] = None

    def load_request(self, req: dict):
        self._current = req
        resp = req.get("response") or {}

        # Request
        lines = [f"{req.get('method','GET')} {req.get('path','/')} {req.get('http_version','HTTP/1.1')}"]
        for k, v in (req.get("headers") or {}).items():
            lines.append(f"{k}: {v}")
        lines.append("")
        body = req.get("body", "")
        if body:
            lines.append(body[:4096])
        self.req_text.setPlainText("\n".join(lines))

        # Response
        if resp:
            rlines = [f"{resp.get('http_version','HTTP/1.1')} {resp.get('status_code','')} {resp.get('status_text','')}"]
            for k, v in (resp.get("headers") or {}).items():
                rlines.append(f"{k}: {v}")
            rlines.append("")
            rbody = resp.get("body", "")
            if rbody:
                rlines.append(rbody[:8192])
            self.resp_text.setPlainText("\n".join(rlines))
        else:
            self.resp_text.setPlainText("(no response captured)")

        # Headers
        all_headers = {}
        all_headers.update(req.get("headers") or {})
        hlines = ["=== REQUEST HEADERS ==="]
        for k, v in (req.get("headers") or {}).items():
            hlines.append(f"  {k}: {v}")
        if resp.get("headers"):
            hlines.append("\n=== RESPONSE HEADERS ===")
            for k, v in (resp.get("headers") or {}).items():
                hlines.append(f"  {k}: {v}")
        self.headers_text.setPlainText("\n".join(hlines))

    def _send_to_repeater(self):
        if self._current:
            self.send_to_repeater.emit(self._current)

    def _send_to_comparer(self):
        if self._current:
            self.send_to_comparer.emit(self._current)

    def _forward_request(self):
        if self._current:
            self.forward_request.emit(self._current)
            # Visual feedback: flash button green briefly
            self.btn_forward.setText("✓ Forwarded")
            self.btn_forward.setStyleSheet(
                "QPushButton {"
                "  background-color: #065f46;"
                "  color: #6ee7b7;"
                "  border: 1px solid #10b981;"
                "  border-radius: 4px;"
                "  padding: 2px 10px;"
                "  font-weight: bold;"
                "}"
            )
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1200, self._reset_forward_button)

    def _reset_forward_button(self):
        self.btn_forward.setText("⏩ Forward")
        self.btn_forward.setStyleSheet(
            "QPushButton#btn_forward {"
            "  background-color: #0e7490;"
            "  color: #e0f7fa;"
            "  border: 1px solid #06b6d4;"
            "  border-radius: 4px;"
            "  padding: 2px 10px;"
            "  font-weight: bold;"
            "}"
            "QPushButton#btn_forward:hover {"
            "  background-color: #0891b2;"
            "  border-color: #22d3ee;"
            "}"
            "QPushButton#btn_forward:pressed {"
            "  background-color: #164e63;"
            "}"
        )

    def _copy_curl(self):
        if not self._current:
            return
        from PyQt6.QtWidgets import QApplication
        req = self._current
        url = req.get("url", req.get("host", ""))
        method = req.get("method", "GET")
        parts = [f"curl -X {method} '{url}'"]
        for k, v in (req.get("headers") or {}).items():
            parts.append(f"  -H '{k}: {v}'")
        if req.get("body"):
            parts.append(f"  -d '{req['body'][:500]}'")
        QApplication.clipboard().setText(" \\\n".join(parts))


class ProxyTab(QWidget):
    send_to_repeater = pyqtSignal(dict)
    send_to_comparer = pyqtSignal(dict)

    def __init__(self, engine: ProxyEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._setup_ui()
        self._connect_signals()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._poll_proxy)
        self._refresh_timer.start(200)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Toolbar ──────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.btn_start = QPushButton("▶ Start Proxy")
        self.btn_start.setObjectName("btn_success")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setObjectName("btn_danger")
        self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("✕ Clear")

        self.lbl_host = QLabel("Host:")
        self.txt_host = QLineEdit("127.0.0.1")
        self.txt_host.setMaximumWidth(120)
        self.lbl_port = QLabel("Port:")
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(8080)
        self.spin_port.setMaximumWidth(80)

        self.chk_intercept = QCheckBox("Intercept")
        self.chk_intercept.setStyleSheet("color: #FFB800;")

        self.status_led = QLabel("●")
        self.status_led.setStyleSheet("color: #FF4444; font-size: 18px;")
        self.lbl_status = QLabel("Stopped")
        self.lbl_counter = QLabel("0 requests")
        self.lbl_counter.setStyleSheet("color: #64748b;")

        toolbar.addWidget(self.status_led)
        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_stop)
        toolbar.addWidget(self.btn_clear)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.lbl_host)
        toolbar.addWidget(self.txt_host)
        toolbar.addWidget(self.lbl_port)
        toolbar.addWidget(self.spin_port)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.chk_intercept)
        toolbar.addStretch()
        toolbar.addWidget(self.lbl_counter)
        layout.addLayout(toolbar)

        # ── Filter bar ────────────────────────────────────────────────
        filter_bar = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter requests (host, path, method...)")
        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["All Methods", "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["All Status", "2xx", "3xx", "4xx", "5xx"])
        filter_bar.addWidget(QLabel("Filter:"))
        filter_bar.addWidget(self.txt_filter, 1)
        filter_bar.addWidget(self.cmb_method)
        filter_bar.addWidget(self.cmb_status)
        layout.addLayout(filter_bar)

        # ── Main splitter ─────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = RequestTableWidget()
        splitter.addWidget(self.table)

        self.detail = RequestDetailPanel()
        splitter.addWidget(self.detail)

        splitter.setSizes([300, 300])
        layout.addWidget(splitter)

    def _connect_signals(self):
        self.btn_start.clicked.connect(self._start_proxy)
        self.btn_stop.clicked.connect(self._stop_proxy)
        self.btn_clear.clicked.connect(self._clear)
        self.txt_filter.textChanged.connect(self.table.filter_rows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.detail.send_to_repeater.connect(self.send_to_repeater)
        self.detail.send_to_comparer.connect(self.send_to_comparer)
        self.detail.forward_request.connect(self._forward_request)
        self.chk_intercept.toggled.connect(self._toggle_intercept)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def _start_proxy(self):
        host = self.txt_host.text().strip() or "127.0.0.1"
        port = self.spin_port.value()
        self.engine.host = host
        self.engine.port = port
        if self.engine.start():
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.txt_host.setEnabled(False)
            self.spin_port.setEnabled(False)
            self.status_led.setStyleSheet("color: #00FF88; font-size: 18px;")
            self.lbl_status.setText(f"Running on {host}:{port}")
        else:
            self.status_led.setStyleSheet("color: #FF4444; font-size: 18px;")
            self.lbl_status.setText("Failed to start")

    def _stop_proxy(self):
        self.engine.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.txt_host.setEnabled(True)
        self.spin_port.setEnabled(True)
        self.status_led.setStyleSheet("color: #FF4444; font-size: 18px;")
        self.lbl_status.setText("Stopped")

    def _clear(self):
        self.table.clear_all()
        self.engine.clear_requests()
        self.lbl_counter.setText("0 requests")

    def _toggle_intercept(self, state: bool):
        self.engine.intercept_enabled = state

    def _poll_proxy(self):
        reqs = self.engine.get_requests()
        current_rows = self.table.rowCount()
        new_reqs = reqs[current_rows:]
        for req in new_reqs:
            self.table.add_request(req.to_dict())
        if new_reqs:
            self.lbl_counter.setText(f"{len(reqs)} requests")

    def _on_selection_changed(self):
        rows = self.table.selectedItems()
        if rows:
            row = rows[0].row()
            req = self.table.get_request_at(row)
            if req:
                self.detail.load_request(req)

    def _show_context_menu(self, pos: QPoint):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        req = self.table.get_request_at(row)
        if not req:
            return
        menu = QMenu(self)
        menu.addAction("Send to Repeater", lambda: self.send_to_repeater.emit(req))
        menu.addAction("Send to Comparer", lambda: self.send_to_comparer.emit(req))
        menu.addSeparator()
        menu.addAction("Copy URL", lambda: self._copy_text(req.get("url", "")))
        menu.addAction("Copy as cURL", lambda: self.detail._copy_curl())
        menu.addSeparator()
        menu.addAction("Delete", lambda: self.table.removeRow(row))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    @staticmethod
    def _copy_text(text: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _forward_request(self, req: dict):
        """Forward an intercepted request through the proxy engine."""
        req_id = req.get("id")
        if req_id is not None:
            # Find the matching HttpRequest object in the engine and forward it
            with self.engine._lock:
                for engine_req in self.engine._requests:
                    if engine_req.id == req_id and engine_req.status == "intercepted":
                        self.engine.forward_request(engine_req)
                        return
        # Fallback: if not intercepted (already forwarded/completed), just notify
        logger.debug("Forward called on non-intercepted request id=%s", req_id)
