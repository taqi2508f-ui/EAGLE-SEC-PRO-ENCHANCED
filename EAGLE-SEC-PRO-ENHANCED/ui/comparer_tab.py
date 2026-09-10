from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QTextEdit, QTabWidget, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter

from modules.comparer import ComparerEngine
from core.logger import get_logger

logger = get_logger("comparer_tab")


class DiffHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str):
        fmt_add = QTextCharFormat()
        fmt_add.setForeground(QColor("#00FF88"))
        fmt_add.setBackground(QColor("#00FF8815"))

        fmt_rem = QTextCharFormat()
        fmt_rem.setForeground(QColor("#FF4444"))
        fmt_rem.setBackground(QColor("#FF444415"))

        fmt_meta = QTextCharFormat()
        fmt_meta.setForeground(QColor("#00D4FF"))

        if text.startswith("+") and not text.startswith("+++"):
            self.setFormat(0, len(text), fmt_add)
        elif text.startswith("-") and not text.startswith("---"):
            self.setFormat(0, len(text), fmt_rem)
        elif text.startswith("@@") or text.startswith("---") or text.startswith("+++"):
            self.setFormat(0, len(text), fmt_meta)


class ComparerPanel(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setPlaceholderText(f"Paste {label.lower()} content here...")
        layout.addWidget(self.editor)

    def get_text(self) -> str:
        return self.editor.toPlainText()

    def set_text(self, text: str):
        self.editor.setPlainText(text)

    def load_request(self, req: dict):
        lines = [f"{req.get('method','GET')} {req.get('path','/')} HTTP/1.1"]
        for k, v in (req.get("headers") or {}).items():
            lines.append(f"{k}: {v}")
        lines.append("")
        if req.get("body"):
            lines.append(req["body"])
        self.editor.setPlainText("\r\n".join(lines))


class ComparerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = ComparerEngine()
        self._slot_a_filled = False
        self._slot_b_filled = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        self.btn_compare = QPushButton("⟺  Compare")
        self.btn_compare.setObjectName("btn_success")
        self.btn_clear_a = QPushButton("Clear A")
        self.btn_clear_b = QPushButton("Clear B")
        self.btn_clear_a.setObjectName("btn_danger")
        self.btn_clear_b.setObjectName("btn_danger")
        self.lbl_similarity = QLabel("")
        self.lbl_similarity.setStyleSheet("color: #00D4FF; font-size: 13px; font-weight: bold;")

        tb.addWidget(self.btn_compare)
        tb.addWidget(self.btn_clear_a)
        tb.addWidget(self.btn_clear_b)
        tb.addStretch()
        tb.addWidget(self.lbl_similarity)
        layout.addLayout(tb)

        # Panels A & B
        panel_split = QSplitter(Qt.Orientation.Horizontal)
        self.panel_a = ComparerPanel("ORIGINAL  (A)")
        self.panel_b = ComparerPanel("MODIFIED  (B)")
        panel_split.addWidget(self.panel_a)
        panel_split.addWidget(self.panel_b)
        panel_split.setSizes([500, 500])

        # Output tabs
        self.output_tabs = QTabWidget()

        self.txt_diff = QTextEdit()
        self.txt_diff.setReadOnly(True)
        self.txt_diff.setFont(QFont("Consolas", 10))
        DiffHighlighter(self.txt_diff.document())
        self.output_tabs.addTab(self.txt_diff, "Unified Diff")

        self.txt_summary = QTextEdit()
        self.txt_summary.setReadOnly(True)
        self.txt_summary.setFont(QFont("Consolas", 10))
        self.output_tabs.addTab(self.txt_summary, "Summary")

        main_split = QSplitter(Qt.Orientation.Vertical)
        main_split.addWidget(panel_split)
        main_split.addWidget(self.output_tabs)
        main_split.setSizes([300, 200])
        layout.addWidget(main_split)

        # Connect
        self.btn_compare.clicked.connect(self._compare)
        self.btn_clear_a.clicked.connect(lambda: self.panel_a.set_text(""))
        self.btn_clear_b.clicked.connect(lambda: self.panel_b.set_text(""))

    def _compare(self):
        a = self.panel_a.get_text()
        b = self.panel_b.get_text()
        if not a or not b:
            self.lbl_similarity.setText("Both panels must have content")
            return

        result = self.engine.compare_text(a, b)
        self.lbl_similarity.setText(f"Similarity: {result.similarity}%")
        self.txt_diff.setPlainText(result.unified_diff or "No differences found")

        summary = (
            f"Similarity:  {result.similarity}%\n"
            f"Added lines: {result.added}\n"
            f"Removed:     {result.removed}\n"
            f"Unchanged:   {result.unchanged}\n"
        )
        self.txt_summary.setPlainText(summary)

    def load_to_a(self, req: dict):
        self.panel_a.load_request(req)

    def load_to_b(self, req: dict):
        self.panel_b.load_request(req)

    def load_request(self, req: dict):
        if not self._slot_a_filled:
            self.panel_a.load_request(req)
            self._slot_a_filled = True
        else:
            self.panel_b.load_request(req)
            self._slot_b_filled = True
            self._slot_a_filled = False
