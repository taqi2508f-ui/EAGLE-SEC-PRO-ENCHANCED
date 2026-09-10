import socket
import ssl
import threading
import time
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QTabWidget, QSpinBox,
    QCheckBox, QGroupBox, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.logger import get_logger

logger = get_logger("repeater_tab")


class SendWorker(QThread):
    result = pyqtSignal(str, float)
    error = pyqtSignal(str)

    def __init__(self, host: str, port: int, raw_request: str, use_ssl: bool, timeout: int):
        super().__init__()
        self.host = host
        self.port = port
        self.raw = raw_request
        self.use_ssl = use_ssl
        self.timeout = timeout

    def run(self):
        try:
            t0 = time.time()
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            if self.use_ssl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)

            raw_bytes = self.raw.encode("utf-8", errors="replace")
            sock.sendall(raw_bytes)

            response = b""
            sock.settimeout(self.timeout)
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            sock.close()

            elapsed = (time.time() - t0) * 1000
            self.result.emit(response.decode("utf-8", errors="replace"), elapsed)
        except Exception as e:
            self.error.emit(str(e))


class RepeaterInstance(QWidget):
    """A single repeater tab with request/response editors."""

    def __init__(self, name: str = "Request 1", parent=None):
        super().__init__(parent)
        self.name = name
        self._worker: Optional[SendWorker] = None
        self._history: list[tuple[str, str]] = []  # (request, response)
        self._history_index = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Target bar
        target_bar = QHBoxLayout()
        target_bar.addWidget(QLabel("Host:"))
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("example.com")
        self.txt_host.setMaximumWidth(250)
        target_bar.addWidget(self.txt_host)

        target_bar.addWidget(QLabel("Port:"))
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(80)
        self.spin_port.setMaximumWidth(75)
        target_bar.addWidget(self.spin_port)

        self.chk_ssl = QCheckBox("HTTPS")
        target_bar.addWidget(self.chk_ssl)

        target_bar.addWidget(QLabel("Timeout:"))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 120)
        self.spin_timeout.setValue(30)
        self.spin_timeout.setSuffix("s")
        self.spin_timeout.setMaximumWidth(70)
        target_bar.addWidget(self.spin_timeout)

        target_bar.addStretch()

        self.btn_back = QPushButton("◀")
        self.btn_back.setMaximumWidth(36)
        self.btn_forward = QPushButton("▶")
        self.btn_forward.setMaximumWidth(36)
        target_bar.addWidget(self.btn_back)
        target_bar.addWidget(self.btn_forward)

        self.btn_send = QPushButton("▶ Send")
        self.btn_send.setObjectName("btn_success")
        self.btn_send.setMinimumWidth(90)
        target_bar.addWidget(self.btn_send)

        layout.addLayout(target_bar)

        # Status bar
        status_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        self.lbl_timing = QLabel("")
        self.lbl_timing.setStyleSheet("color: #00D4FF; font-size: 11px;")
        status_bar.addWidget(self.lbl_status)
        status_bar.addStretch()
        status_bar.addWidget(self.lbl_timing)
        layout.addLayout(status_bar)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Request editor
        req_frame = QWidget()
        req_layout = QVBoxLayout(req_frame)
        req_layout.setContentsMargins(0, 0, 0, 0)
        req_layout.addWidget(QLabel("REQUEST"))
        self.txt_request = QTextEdit()
        self.txt_request.setFont(QFont("Consolas", 10))
        self.txt_request.setPlaceholderText(
            "GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n"
        )
        req_layout.addWidget(self.txt_request)
        splitter.addWidget(req_frame)

        # Response viewer
        resp_frame = QWidget()
        resp_layout = QVBoxLayout(resp_frame)
        resp_layout.setContentsMargins(0, 0, 0, 0)
        resp_layout.addWidget(QLabel("RESPONSE"))
        self.txt_response = QTextEdit()
        self.txt_response.setFont(QFont("Consolas", 10))
        self.txt_response.setReadOnly(True)
        resp_layout.addWidget(self.txt_response)
        splitter.addWidget(resp_frame)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        # Connect
        self.btn_send.clicked.connect(self._send)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.chk_ssl.toggled.connect(lambda v: self.spin_port.setValue(443 if v else 80))

    def load_request(self, req: dict):
        host = req.get("host", "")
        port = req.get("port", 80)
        is_https = req.get("is_https", False)
        self.txt_host.setText(host)
        self.spin_port.setValue(port)
        self.chk_ssl.setChecked(is_https)

        lines = [f"{req.get('method','GET')} {req.get('path','/')} {req.get('http_version','HTTP/1.1')}"]
        for k, v in (req.get("headers") or {}).items():
            lines.append(f"{k}: {v}")
        lines.append("")
        if req.get("body"):
            lines.append(req["body"])
        self.txt_request.setPlainText("\r\n".join(lines))

    def _send(self):
        if self._worker and self._worker.isRunning():
            return
        host = self.txt_host.text().strip()
        port = self.spin_port.value()
        raw = self.txt_request.toPlainText()
        use_ssl = self.chk_ssl.isChecked()
        timeout = self.spin_timeout.value()

        if not host or not raw:
            self.lbl_status.setText("Please enter host and request")
            return

        self.btn_send.setEnabled(False)
        self.lbl_status.setText("Sending...")
        self.txt_response.setPlainText("...")

        self._worker = SendWorker(host, port, raw, use_ssl, timeout)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, response: str, elapsed: float):
        self._history.append((self.txt_request.toPlainText(), response))
        self._history_index = len(self._history) - 1
        self.txt_response.setPlainText(response)
        self.lbl_timing.setText(f"{elapsed:.0f}ms")
        lines = response.splitlines()
        status = lines[0] if lines else "unknown"
        self.lbl_status.setText(f"Response: {status}")
        self.btn_send.setEnabled(True)

    def _on_error(self, error: str):
        self.txt_response.setPlainText(f"[ERROR] {error}")
        self.lbl_status.setText(f"Error: {error[:80]}")
        self.btn_send.setEnabled(True)

    def _go_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            req, resp = self._history[self._history_index]
            self.txt_request.setPlainText(req)
            self.txt_response.setPlainText(resp)

    def _go_forward(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            req, resp = self._history[self._history_index]
            self.txt_request.setPlainText(req)
            self.txt_response.setPlainText(resp)


class RepeaterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._instances: list[RepeaterInstance] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab controls
        ctrl_bar = QHBoxLayout()
        self.btn_new = QPushButton("+ New Tab")
        self.btn_close = QPushButton("✕ Close Tab")
        self.btn_close.setObjectName("btn_danger")
        ctrl_bar.addWidget(self.btn_new)
        ctrl_bar.addWidget(self.btn_close)
        ctrl_bar.addStretch()
        layout.addLayout(ctrl_bar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs)

        self.btn_new.clicked.connect(self._new_tab)
        self.btn_close.clicked.connect(lambda: self._close_tab(self.tabs.currentIndex()))

        self._new_tab()

    def _new_tab(self) -> RepeaterInstance:
        n = len(self._instances) + 1
        inst = RepeaterInstance(f"Request {n}")
        self._instances.append(inst)
        self.tabs.addTab(inst, f"Request {n}")
        self.tabs.setCurrentWidget(inst)
        return inst

    def _close_tab(self, index: int):
        if self.tabs.count() <= 1:
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget in self._instances:
            self._instances.remove(widget)
        widget.deleteLater()

    def load_request(self, req: dict):
        inst = self._new_tab()
        inst.load_request(req)
