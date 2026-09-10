from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QCheckBox, QGroupBox, QAbstractItemView,
    QProgressBar, QTabWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from modules.crawler import WebCrawler, CrawlResult
from core.logger import get_logger

logger = get_logger("crawler_tab")


class CrawlerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crawler = WebCrawler()
        self.crawler.on_result(self._on_result)
        self.crawler.on_done(self._on_done)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Config
        cfg = QGroupBox("Crawler Configuration")
        cfg_layout = QVBoxLayout(cfg)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Target URL:"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://example.com")
        self.txt_url.setFont(QFont("Consolas", 10))
        row1.addWidget(self.txt_url, 1)
        cfg_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Max Depth:"))
        self.spin_depth = QSpinBox()
        self.spin_depth.setRange(1, 10)
        self.spin_depth.setValue(3)
        self.spin_depth.setMaximumWidth(60)
        row2.addWidget(self.spin_depth)

        row2.addWidget(QLabel("Max Pages:"))
        self.spin_pages = QSpinBox()
        self.spin_pages.setRange(1, 10000)
        self.spin_pages.setValue(100)
        self.spin_pages.setMaximumWidth(80)
        row2.addWidget(self.spin_pages)

        row2.addWidget(QLabel("Delay (ms):"))
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(0, 10000)
        self.spin_delay.setValue(500)
        self.spin_delay.setMaximumWidth(80)
        row2.addWidget(self.spin_delay)

        self.chk_external = QCheckBox("Follow External Links")
        row2.addWidget(self.chk_external)
        row2.addStretch()
        cfg_layout.addLayout(row2)

        layout.addWidget(cfg)

        # Control bar
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start Crawl")
        self.btn_start.setObjectName("btn_success")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setObjectName("btn_danger")
        self.btn_stop.setEnabled(False)
        self.btn_clear = QPushButton("✕ Clear")
        self.btn_export = QPushButton("⬇ Export")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setTextVisible(False)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #64748b;")

        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_clear)
        ctrl.addWidget(self.btn_export)
        ctrl.addStretch()
        ctrl.addWidget(self.lbl_status)
        layout.addLayout(ctrl)
        layout.addWidget(self.progress_bar)

        # Results
        output_tabs = QTabWidget()

        # Pages table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["URL", "Status", "Title", "Links", "Forms", "Time"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFont(QFont("Consolas", 10))
        self.table.verticalHeader().hide()
        self.table.itemSelectionChanged.connect(self._on_select)
        output_tabs.addTab(self.table, "Pages")

        # Detail
        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setFont(QFont("Consolas", 10))
        output_tabs.addTab(self.txt_detail, "Details")

        # Log
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 9))
        output_tabs.addTab(self.txt_log, "Log")

        layout.addWidget(output_tabs)

        # Connect
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_export.clicked.connect(self._export)

        # Pulse timer for progress animation
        self._pulse = 0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._update_pulse)

    def _start(self):
        url = self.txt_url.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
            self.txt_url.setText(url)

        self.crawler.max_depth = self.spin_depth.value()
        self.crawler.max_pages = self.spin_pages.value()
        self.crawler.delay_ms = self.spin_delay.value()
        self.crawler.follow_external = self.chk_external.isChecked()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText("Crawling...")
        self._pulse_timer.start(100)
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Started crawl: {url}")
        self.crawler.start(url)

    def _stop(self):
        self.crawler.stop()
        self._on_done([])

    def _on_result(self, result: CrawlResult):
        from PyQt6.QtWidgets import QApplication
        row = self.table.rowCount()
        self.table.insertRow(row)

        url_item = QTableWidgetItem(result.url[:80])
        url_item.setData(Qt.ItemDataRole.UserRole, result)
        status_item = QTableWidgetItem(str(result.status_code) if result.status_code else "err")
        title_item = QTableWidgetItem(result.title[:40])
        links_item = QTableWidgetItem(str(len(result.links)))
        forms_item = QTableWidgetItem(str(len(result.forms)))
        time_item = QTableWidgetItem(f"{result.response_time_ms:.0f}ms")

        if result.error:
            url_item.setForeground(QColor("#FF4444"))
        elif 200 <= result.status_code < 300:
            status_item.setForeground(QColor("#4ade80"))
        elif 400 <= result.status_code < 500:
            status_item.setForeground(QColor("#f87171"))
        elif 500 <= result.status_code < 600:
            status_item.setForeground(QColor("#FF4444"))

        for col, item in enumerate([url_item, status_item, title_item, links_item, forms_item, time_item]):
            self.table.setItem(row, col, item)

        count = self.table.rowCount()
        self.lbl_status.setText(f"Crawled {count} pages...")
        self.txt_log.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {result.status_code} "
            f"({result.response_time_ms:.0f}ms) {result.url}"
        )

    def _on_done(self, results: list):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self._pulse_timer.stop()
        count = self.table.rowCount()
        self.lbl_status.setText(f"Done — {count} pages crawled")
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Crawl complete. {count} pages.")

    def _update_pulse(self):
        self._pulse = (self._pulse + 5) % 100
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            pass

    def _on_select(self):
        items = self.table.selectedItems()
        if not items:
            return
        result = items[0].data(Qt.ItemDataRole.UserRole)
        if not isinstance(result, CrawlResult):
            return
        lines = [
            f"URL:     {result.url}",
            f"Status:  {result.status_code}",
            f"Title:   {result.title}",
            f"Type:    {result.content_type}",
            f"Size:    {result.body_size} bytes",
            f"Time:    {result.response_time_ms:.1f}ms",
            f"Depth:   {result.depth}",
            "",
            f"Links ({len(result.links)}):",
        ]
        for link in result.links[:50]:
            lines.append(f"  {link}")

        if result.forms:
            lines.append(f"\nForms ({len(result.forms)}):")
            for form in result.forms:
                lines.append(f"  Action: {form.get('action','')}  Method: {form.get('method','')}")
                for inp in form.get("inputs", []):
                    lines.append(f"    [{inp.get('type','text')}] {inp.get('name','')}")

        if result.scripts:
            lines.append(f"\nScripts ({len(result.scripts)}):")
            for s in result.scripts[:20]:
                lines.append(f"  {s}")

        if result.error:
            lines.append(f"\nError: {result.error}")

        self.txt_detail.setPlainText("\n".join(lines))

    def _clear(self):
        self.table.setRowCount(0)
        self.txt_detail.clear()
        self.txt_log.clear()
        self.lbl_status.setText("Ready")

    def _export(self):
        import json
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Crawl Results", "crawl_results.json", "JSON (*.json)")
        if path:
            data = [r.to_dict() for r in self.crawler.get_results()]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
