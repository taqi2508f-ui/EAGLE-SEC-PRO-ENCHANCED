import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QComboBox, QLineEdit, QGroupBox, QCheckBox,
    QAbstractItemView, QProgressBar, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from modules.reporter import ReportGenerator
from database.db_manager import DatabaseManager
from core.logger import get_logger

logger = get_logger("reports_tab")


class ReportWorker(QThread):
    done = pyqtSignal(str, str)  # format, path
    error = pyqtSignal(str)

    def __init__(self, fmt: str, requests: list, project: str, findings: list):
        super().__init__()
        self.fmt = fmt
        self.requests = requests
        self.project = project
        self.findings = findings
        self.gen = ReportGenerator()

    def run(self):
        try:
            if self.fmt == "HTML":
                path = self.gen.generate_html(self.requests, self.project, self.findings)
            elif self.fmt == "JSON":
                path = self.gen.generate_json(self.requests, self.project, self.findings)
            elif self.fmt == "PDF":
                path = self.gen.generate_pdf(self.requests, self.project, self.findings)
                if not path:
                    self.error.emit("PDF generation failed (reportlab not installed?)")
                    return
            else:
                self.error.emit(f"Unknown format: {self.fmt}")
                return
            self.done.emit(self.fmt, str(path))
        except Exception as e:
            self.error.emit(str(e))


class ReportsTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._requests: list[dict] = []
        self._findings: list[dict] = []
        self._worker: Optional[ReportWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tabs = QTabWidget()

        # ── Generate tab ─────────────────────────────────────────────
        gen_tab = self._build_generate_tab()
        tabs.addTab(gen_tab, "Generate Report")

        # ── History tab ──────────────────────────────────────────────
        hist_tab = self._build_history_tab()
        tabs.addTab(hist_tab, "Report History")

        # ── Findings tab ─────────────────────────────────────────────
        findings_tab = self._build_findings_tab()
        tabs.addTab(findings_tab, "Findings")

        layout.addWidget(tabs)

    def _build_generate_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Config
        cfg = QGroupBox("Report Configuration")
        cfg_lay = QVBoxLayout(cfg)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Format:"))
        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["HTML", "JSON", "PDF"])
        row1.addWidget(self.cmb_format)

        row1.addWidget(QLabel("Project:"))
        self.txt_project = QLineEdit("Default Project")
        self.txt_project.setMaximumWidth(200)
        row1.addWidget(self.txt_project)

        row1.addWidget(QLabel("Title:"))
        self.txt_title = QLineEdit("Security Audit Report")
        row1.addWidget(self.txt_title, 1)
        cfg_lay.addLayout(row1)

        options_row = QHBoxLayout()
        self.chk_include_findings = QCheckBox("Include Findings")
        self.chk_include_findings.setChecked(True)
        options_row.addWidget(self.chk_include_findings)
        options_row.addStretch()
        cfg_lay.addLayout(options_row)

        layout.addWidget(cfg)

        # Status
        self.lbl_gen_status = QLabel(f"Ready — {len(self._requests)} requests available")
        self.lbl_gen_status.setStyleSheet("color: #64748b;")
        layout.addWidget(self.lbl_gen_status)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(6)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        # Generate button
        btn_bar = QHBoxLayout()
        self.btn_generate = QPushButton("⬇ Generate Report")
        self.btn_generate.setObjectName("btn_success")
        self.btn_generate.setMinimumWidth(160)
        self.btn_open_dir = QPushButton("📁 Open Reports Folder")
        btn_bar.addWidget(self.btn_generate)
        btn_bar.addWidget(self.btn_open_dir)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Preview
        layout.addWidget(QLabel("Preview / Last Report Path:"))
        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFont(QFont("Consolas", 10))
        self.txt_preview.setMaximumHeight(120)
        layout.addWidget(self.txt_preview)

        layout.addStretch()

        self.btn_generate.clicked.connect(self._generate)
        self.btn_open_dir.clicked.connect(self._open_reports_dir)

        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        self.btn_refresh_hist = QPushButton("↻ Refresh")
        self.btn_open_report = QPushButton("▶ Open Selected")
        ctrl.addWidget(self.btn_refresh_hist)
        ctrl.addWidget(self.btn_open_report)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        self.hist_table = QTableWidget(0, 5)
        self.hist_table.setHorizontalHeaderLabels(["Name", "Format", "Project", "Created", "Path"])
        self.hist_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.hist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hist_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hist_table.setFont(QFont("Consolas", 10))
        self.hist_table.verticalHeader().hide()
        layout.addWidget(self.hist_table)

        self.btn_refresh_hist.clicked.connect(self._load_history)
        self.btn_open_report.clicked.connect(self._open_selected_report)
        return w

    def _build_findings_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        self.btn_add_finding = QPushButton("+ Add Finding")
        self.btn_add_finding.setObjectName("btn_success")
        self.btn_del_finding = QPushButton("✕ Remove")
        self.btn_del_finding.setObjectName("btn_danger")
        ctrl.addWidget(self.btn_add_finding)
        ctrl.addWidget(self.btn_del_finding)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.findings_table = QTableWidget(0, 3)
        self.findings_table.setHorizontalHeaderLabels(["Title", "Severity", "URL"])
        self.findings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.findings_table.setFont(QFont("Consolas", 10))
        self.findings_table.verticalHeader().hide()
        self.findings_table.itemSelectionChanged.connect(self._on_finding_select)
        splitter.addWidget(self.findings_table)

        detail = QWidget()
        det = QVBoxLayout(detail)
        det.addWidget(QLabel("Finding Details:"))
        self.txt_finding_detail = QTextEdit()
        self.txt_finding_detail.setFont(QFont("Consolas", 10))
        det.addWidget(self.txt_finding_detail)
        splitter.addWidget(detail)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        self.btn_add_finding.clicked.connect(self._add_finding_dialog)
        self.btn_del_finding.clicked.connect(self._remove_finding)

        return w

    def set_requests(self, requests: list[dict]):
        self._requests = requests
        self.lbl_gen_status.setText(f"Ready — {len(requests)} requests available")

    def _generate(self):
        if not self._requests:
            self.lbl_gen_status.setText("No requests to include in report")
            return

        fmt = self.cmb_format.currentText()
        project = self.txt_project.text() or "Default"
        findings = self._findings if self.chk_include_findings.isChecked() else []

        self.btn_generate.setEnabled(False)
        self.progress.setRange(0, 0)
        self.lbl_gen_status.setText(f"Generating {fmt} report...")

        self._worker = ReportWorker(fmt, self._requests, project, findings)
        self._worker.done.connect(self._on_generated)
        self._worker.error.connect(self._on_gen_error)
        self._worker.start()

    def _on_generated(self, fmt: str, path: str):
        self.btn_generate.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.lbl_gen_status.setText(f"Report saved: {path}")
        self.txt_preview.setPlainText(path)

        report_id = str(uuid.uuid4())[:8]
        try:
            self.db.save_report(
                report_id=report_id,
                project_id="default",
                name=f"{fmt} Report {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                fmt=fmt,
                path=path,
                summary=f"{len(self._requests)} requests",
            )
        except Exception:
            pass
        self._load_history()

    def _on_gen_error(self, error: str):
        self.btn_generate.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.lbl_gen_status.setText(f"Error: {error}")

    def _load_history(self):
        reports = self.db.get_reports()
        self.hist_table.setRowCount(0)
        for r in reports:
            row = self.hist_table.rowCount()
            self.hist_table.insertRow(row)
            ts = datetime.fromtimestamp(r.get("created_at", 0)).strftime("%Y-%m-%d %H:%M")
            for col, val in enumerate([r.get("name",""), r.get("format",""),
                                        r.get("project_id",""), ts, r.get("path","")]):
                self.hist_table.setItem(row, col, QTableWidgetItem(str(val)))

    def _open_selected_report(self):
        items = self.hist_table.selectedItems()
        if not items:
            return
        row = items[0].row()
        path_item = self.hist_table.item(row, 4)
        if path_item:
            self._open_path(path_item.text())

    def _open_reports_dir(self):
        from modules.reporter import REPORTS_DIR
        self._open_path(str(REPORTS_DIR))

    @staticmethod
    def _open_path(path: str):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            logger.error("Open path error: %s", e)

    def _add_finding_dialog(self):
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Finding")
        dlg.setMinimumWidth(400)
        form = QFormLayout(dlg)
        title_ed = QLineEdit()
        sev_cb = QComboBox()
        sev_cb.addItems(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        url_ed = QLineEdit()
        desc_ed = QTextEdit()
        desc_ed.setMaximumHeight(100)
        form.addRow("Title:", title_ed)
        form.addRow("Severity:", sev_cb)
        form.addRow("URL:", url_ed)
        form.addRow("Description:", desc_ed)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            finding = {
                "title": title_ed.text(),
                "severity": sev_cb.currentText(),
                "url": url_ed.text(),
                "description": desc_ed.toPlainText(),
            }
            self._findings.append(finding)
            row = self.findings_table.rowCount()
            self.findings_table.insertRow(row)
            severity_colors = {"CRITICAL": "#FF4444", "HIGH": "#f87171",
                                "MEDIUM": "#FFB800", "LOW": "#4ade80", "INFO": "#38bdf8"}
            for col, val in enumerate([finding["title"], finding["severity"], finding["url"]]):
                item = QTableWidgetItem(val)
                if col == 1:
                    item.setForeground(QColor(severity_colors.get(val, "#e2e8f0")))
                self.findings_table.setItem(row, col, item)

    def _remove_finding(self):
        items = self.findings_table.selectedItems()
        if items:
            row = items[0].row()
            self.findings_table.removeRow(row)
            if row < len(self._findings):
                self._findings.pop(row)

    def _on_finding_select(self):
        items = self.findings_table.selectedItems()
        if not items:
            return
        row = items[0].row()
        if row < len(self._findings):
            f = self._findings[row]
            self.txt_finding_detail.setPlainText(
                f"Title: {f.get('title')}\n"
                f"Severity: {f.get('severity')}\n"
                f"URL: {f.get('url')}\n\n"
                f"Description:\n{f.get('description')}"
            )
