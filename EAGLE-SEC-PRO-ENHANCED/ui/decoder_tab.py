import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QTextEdit, QComboBox, QTabWidget, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from modules.decoder import DecoderEngine
from core.logger import get_logger

logger = get_logger("decoder_tab")


class DecoderTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = DecoderEngine()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tabs = QTabWidget()

        # ── Encode/Decode ────────────────────────────────────────────
        enc_widget = self._build_enc_tab()
        tabs.addTab(enc_widget, "Encode / Decode")

        # ── Hash ─────────────────────────────────────────────────────
        hash_widget = self._build_hash_tab()
        tabs.addTab(hash_widget, "Hash")

        # ── JWT ──────────────────────────────────────────────────────
        jwt_widget = self._build_jwt_tab()
        tabs.addTab(jwt_widget, "JWT")

        # ── Auto-Detect ──────────────────────────────────────────────
        auto_widget = self._build_auto_tab()
        tabs.addTab(auto_widget, "Smart Decode")

        layout.addWidget(tabs)

    # ── Encode/Decode tab ────────────────────────────────────────────
    def _build_enc_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Mode selector
        mode_bar = QHBoxLayout()
        mode_bar.addWidget(QLabel("Mode:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            "Base64 Decode", "Base64 Encode",
            "Base64 URL Decode", "Base64 URL Encode",
            "URL Decode", "URL Encode", "URL Encode (All)",
            "Hex Decode", "Hex Encode", "Hex Encode (Formatted)",
            "HTML Decode", "HTML Encode",
            "JSON Format", "JSON Minify",
        ])
        mode_bar.addWidget(self.cmb_mode, 1)
        self.btn_go = QPushButton("▶ Apply")
        self.btn_go.setObjectName("btn_success")
        self.btn_swap = QPushButton("⇅ Swap")
        self.btn_clear = QPushButton("✕ Clear")
        mode_bar.addWidget(self.btn_go)
        mode_bar.addWidget(self.btn_swap)
        mode_bar.addWidget(self.btn_clear)
        layout.addLayout(mode_bar)

        # Status
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        in_frame = QWidget()
        in_lay = QVBoxLayout(in_frame)
        in_lay.setContentsMargins(0, 0, 0, 0)
        in_lay.addWidget(QLabel("INPUT"))
        self.txt_input = QTextEdit()
        self.txt_input.setFont(QFont("Consolas", 10))
        self.txt_input.setPlaceholderText("Paste text to encode or decode...")
        in_lay.addWidget(self.txt_input)
        splitter.addWidget(in_frame)

        out_frame = QWidget()
        out_lay = QVBoxLayout(out_frame)
        out_lay.setContentsMargins(0, 0, 0, 0)
        out_lay.addWidget(QLabel("OUTPUT"))
        self.txt_output = QTextEdit()
        self.txt_output.setFont(QFont("Consolas", 10))
        self.txt_output.setReadOnly(True)
        out_lay.addWidget(self.txt_output)
        splitter.addWidget(out_frame)

        splitter.setSizes([250, 250])
        layout.addWidget(splitter)

        self.btn_go.clicked.connect(self._apply_enc)
        self.btn_swap.clicked.connect(self._swap)
        self.btn_clear.clicked.connect(lambda: (self.txt_input.clear(), self.txt_output.clear()))

        return w

    def _apply_enc(self):
        text = self.txt_input.toPlainText()
        if not text:
            return
        mode = self.cmb_mode.currentText()
        e = self.engine

        dispatch = {
            "Base64 Decode": e.b64_decode, "Base64 Encode": e.b64_encode,
            "Base64 URL Decode": e.b64url_decode, "Base64 URL Encode": e.b64url_encode,
            "URL Decode": e.url_decode, "URL Encode": e.url_encode, "URL Encode (All)": e.url_encode_all,
            "Hex Decode": e.hex_decode, "Hex Encode": e.hex_encode,
            "Hex Encode (Formatted)": e.hex_encode_formatted,
            "HTML Decode": e.html_decode, "HTML Encode": e.html_encode,
            "JSON Format": e.json_format, "JSON Minify": e.json_minify,
        }

        fn = dispatch.get(mode)
        if fn:
            result, status = fn(text)
            self.txt_output.setPlainText(result)
            self.lbl_status.setText(f"Status: {status}  |  Input: {len(text)}  →  Output: {len(result)}")
        else:
            self.lbl_status.setText("Unknown mode")

    def _swap(self):
        out = self.txt_output.toPlainText()
        self.txt_input.setPlainText(out)
        self.txt_output.clear()

    # ── Hash tab ─────────────────────────────────────────────────────
    def _build_hash_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        self.txt_hash_input = QLineEdit()
        self.txt_hash_input.setPlaceholderText("Enter text to hash...")
        self.txt_hash_input.setFont(QFont("Consolas", 10))
        self.btn_hash = QPushButton("▶ Hash")
        self.btn_hash.setObjectName("btn_success")
        ctrl.addWidget(self.txt_hash_input, 1)
        ctrl.addWidget(self.btn_hash)
        layout.addLayout(ctrl)

        # Hash results table
        self.hash_table = QTableWidget(0, 2)
        self.hash_table.setHorizontalHeaderLabels(["Algorithm", "Hash"])
        self.hash_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.hash_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hash_table.setFont(QFont("Consolas", 10))
        self.hash_table.verticalHeader().hide()
        layout.addWidget(self.hash_table)

        # Multi-line hash area
        layout.addWidget(QLabel("Multi-line hash (one per line):"))
        self.txt_hash_multi = QTextEdit()
        self.txt_hash_multi.setFont(QFont("Consolas", 10))
        self.txt_hash_multi.setMaximumHeight(100)
        self.txt_hash_multi.setPlaceholderText("Paste multiple values...")
        self.btn_hash_multi = QPushButton("Hash All Lines")
        self.txt_hash_result = QTextEdit()
        self.txt_hash_result.setFont(QFont("Consolas", 10))
        self.txt_hash_result.setReadOnly(True)
        self.txt_hash_result.setMaximumHeight(150)

        layout.addWidget(self.txt_hash_multi)
        layout.addWidget(self.btn_hash_multi)
        layout.addWidget(self.txt_hash_result)

        self.btn_hash.clicked.connect(self._hash_single)
        self.btn_hash_multi.clicked.connect(self._hash_multi)

        return w

    def _hash_single(self):
        text = self.txt_hash_input.text()
        if not text:
            return
        results = self.engine.hash_all(text)
        self.hash_table.setRowCount(0)
        for algo, val in results.items():
            row = self.hash_table.rowCount()
            self.hash_table.insertRow(row)
            alg_item = QTableWidgetItem(algo.upper())
            alg_item.setForeground(QColor("#00D4FF"))
            self.hash_table.setItem(row, 0, alg_item)
            self.hash_table.setItem(row, 1, QTableWidgetItem(val))

    def _hash_multi(self):
        lines = self.txt_hash_multi.toPlainText().splitlines()
        out = []
        for line in lines:
            if not line.strip():
                continue
            h = self.engine.hash_all(line)
            out.append(f"Input: {line}")
            for algo, val in h.items():
                out.append(f"  {algo.upper()}: {val}")
            out.append("")
        self.txt_hash_result.setPlainText("\n".join(out))

    # ── JWT tab ──────────────────────────────────────────────────────
    def _build_jwt_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        self.txt_jwt_input = QTextEdit()
        self.txt_jwt_input.setFont(QFont("Consolas", 10))
        self.txt_jwt_input.setPlaceholderText("Paste JWT token here...")
        self.txt_jwt_input.setMaximumHeight(80)
        ctrl.addWidget(self.txt_jwt_input)
        layout.addLayout(ctrl)

        self.btn_jwt_decode = QPushButton("▶ Decode JWT")
        self.btn_jwt_decode.setObjectName("btn_success")
        layout.addWidget(self.btn_jwt_decode)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        header_frame = QWidget()
        h_lay = QVBoxLayout(header_frame)
        h_lay.addWidget(QLabel("HEADER"))
        self.txt_jwt_header = QTextEdit()
        self.txt_jwt_header.setFont(QFont("Consolas", 10))
        self.txt_jwt_header.setReadOnly(True)
        h_lay.addWidget(self.txt_jwt_header)
        splitter.addWidget(header_frame)

        payload_frame = QWidget()
        p_lay = QVBoxLayout(payload_frame)
        p_lay.addWidget(QLabel("PAYLOAD"))
        self.txt_jwt_payload = QTextEdit()
        self.txt_jwt_payload.setFont(QFont("Consolas", 10))
        self.txt_jwt_payload.setReadOnly(True)
        p_lay.addWidget(self.txt_jwt_payload)
        splitter.addWidget(payload_frame)

        sig_frame = QWidget()
        s_lay = QVBoxLayout(sig_frame)
        s_lay.addWidget(QLabel("SIGNATURE"))
        self.txt_jwt_sig = QTextEdit()
        self.txt_jwt_sig.setFont(QFont("Consolas", 10))
        self.txt_jwt_sig.setReadOnly(True)
        s_lay.addWidget(self.txt_jwt_sig)
        splitter.addWidget(sig_frame)

        layout.addWidget(splitter)

        self.lbl_jwt_status = QLabel("")
        self.lbl_jwt_status.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_jwt_status)

        self.btn_jwt_decode.clicked.connect(self._decode_jwt)
        return w

    def _decode_jwt(self):
        token = self.txt_jwt_input.toPlainText().strip()
        result, status = self.engine.jwt_decode(token)
        if status == "success":
            self.txt_jwt_header.setPlainText(json.dumps(result.get("header", {}), indent=2))
            self.txt_jwt_payload.setPlainText(json.dumps(result.get("payload", {}), indent=2))
            self.txt_jwt_sig.setPlainText(result.get("signature", ""))
            self.lbl_jwt_status.setText(f"Decoded OK  |  Algorithm: {result.get('header', {}).get('alg', 'N/A')}")
        else:
            self.lbl_jwt_status.setText(f"Error: {status}")

    # ── Auto-detect tab ──────────────────────────────────────────────
    def _build_auto_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        self.txt_auto_input = QTextEdit()
        self.txt_auto_input.setFont(QFont("Consolas", 10))
        self.txt_auto_input.setPlaceholderText("Paste any encoded string and let EAGLE-SEC auto-detect the encoding...")
        self.txt_auto_input.setMaximumHeight(80)
        layout.addWidget(QLabel("Input:"))
        layout.addWidget(self.txt_auto_input)

        self.btn_auto = QPushButton("🔍 Smart Decode")
        self.btn_auto.setObjectName("btn_success")
        layout.addWidget(self.btn_auto)

        self.auto_table = QTableWidget(0, 3)
        self.auto_table.setHorizontalHeaderLabels(["Method", "Result", "Status"])
        self.auto_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.auto_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.auto_table.setFont(QFont("Consolas", 10))
        self.auto_table.verticalHeader().hide()
        layout.addWidget(self.auto_table)

        self.btn_auto.clicked.connect(self._auto_decode)
        return w

    def _auto_decode(self):
        text = self.txt_auto_input.toPlainText().strip()
        if not text:
            return
        results = self.engine.smart_decode(text)
        self.auto_table.setRowCount(0)
        for r in results:
            row = self.auto_table.rowCount()
            self.auto_table.insertRow(row)
            m = QTableWidgetItem(r.get("method", ""))
            m.setForeground(QColor("#00D4FF"))
            self.auto_table.setItem(row, 0, m)
            result_text = r.get("result", "")[:200]
            self.auto_table.setItem(row, 1, QTableWidgetItem(result_text))
            s = QTableWidgetItem(r.get("status", ""))
            s.setForeground(QColor("#00FF88"))
            self.auto_table.setItem(row, 2, s)

    def load_text(self, text: str):
        self.txt_input.setPlainText(text)
