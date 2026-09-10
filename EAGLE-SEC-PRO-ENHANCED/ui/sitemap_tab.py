from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QTabWidget, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from modules.site_mapper import SiteMapper, SiteNode
from core.logger import get_logger

logger = get_logger("sitemap_tab")


class SiteMapTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mapper = SiteMapper()
        self.mapper.on_update(self._on_update)
        self._pending_updates: list[SiteNode] = []
        self._setup_ui()
        self._host_items: dict[str, QTreeWidgetItem] = {}
        self._url_items: dict[str, QTreeWidgetItem] = {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        self.btn_clear = QPushButton("✕ Clear Map")
        self.btn_clear.setObjectName("btn_danger")
        self.btn_export = QPushButton("⬇ Export")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search URLs...")
        self.lbl_stats = QLabel("0 URLs | 0 Hosts")
        self.lbl_stats.setStyleSheet("color: #64748b;")

        tb.addWidget(self.btn_clear)
        tb.addWidget(self.btn_export)
        tb.addWidget(self.txt_search, 1)
        tb.addStretch()
        tb.addWidget(self.lbl_stats)
        layout.addLayout(tb)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["URL / Path", "Methods", "Status", "Requests"])
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.setColumnWidth(0, 350)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 60)
        self.tree.header().setStretchLastSection(False)
        self.tree.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.tree)

        # Detail panel
        detail = QWidget()
        det_layout = QVBoxLayout(detail)
        det_layout.setContentsMargins(0, 0, 0, 0)
        det_layout.addWidget(QLabel("URL DETAILS"))
        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setFont(QFont("Consolas", 10))
        det_layout.addWidget(self.txt_detail)
        splitter.addWidget(detail)

        splitter.setSizes([500, 300])
        layout.addWidget(splitter)

        # Connect
        self.btn_clear.clicked.connect(self._clear)
        self.btn_export.clicked.connect(self._export)
        self.txt_search.textChanged.connect(self._search)

    def add_request(self, req: dict):
        """Called when a new proxy request comes in."""
        self.mapper.add_request(req)

    def _on_update(self, node: SiteNode):
        self._pending_updates.append(node)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._flush_updates)

    def _flush_updates(self):
        if not self._pending_updates:
            return
        for node in self._pending_updates:
            self._add_or_update_node(node)
        self._pending_updates.clear()
        stats = self.mapper.stats()
        self.lbl_stats.setText(f"{stats['total_urls']} URLs | {stats['total_hosts']} Hosts")

    def _add_or_update_node(self, node: SiteNode):
        host = node.host
        if host not in self._host_items:
            host_item = QTreeWidgetItem([f"🌐 {host}", "", "", ""])
            host_item.setForeground(0, QColor("#00D4FF"))
            font = host_item.font(0)
            font.setBold(True)
            host_item.setFont(0, font)
            host_item.setData(0, Qt.ItemDataRole.UserRole, host)
            self.tree.addTopLevelItem(host_item)
            self._host_items[host] = host_item

        host_item = self._host_items[host]

        if node.url in self._url_items:
            item = self._url_items[node.url]
        else:
            path = node.path or "/"
            item = QTreeWidgetItem([path, "", "", ""])
            item.setData(0, Qt.ItemDataRole.UserRole, node.url)
            host_item.addChild(item)
            self._url_items[node.url] = item

        methods = " ".join(sorted(node.methods))
        codes = ", ".join(str(c) for c in sorted(set(node.status_codes))[:3])
        item.setText(1, methods)
        item.setText(2, codes)
        item.setText(3, str(node.request_count))

        color = QColor("#94a3b8")
        if any(400 <= c < 500 for c in node.status_codes):
            color = QColor("#f87171")
        elif any(500 <= c < 600 for c in node.status_codes):
            color = QColor("#FF4444")
        elif any(200 <= c < 300 for c in node.status_codes):
            color = QColor("#4ade80")
        item.setForeground(0, color)

        host_item.setExpanded(True)

    def _on_select(self):
        items = self.tree.selectedItems()
        if not items:
            return
        item = items[0]
        url = item.data(0, Qt.ItemDataRole.UserRole)
        if not url or url in self._host_items:
            return
        node = self.mapper.get_node(url)
        if not node:
            return
        lines = [
            f"URL:       {node.url}",
            f"Host:      {node.host}",
            f"Path:      {node.path}",
            f"Methods:   {', '.join(sorted(node.methods))}",
            f"Statuses:  {', '.join(str(c) for c in sorted(set(node.status_codes)))}",
            f"Requests:  {node.request_count}",
            f"Added:     {datetime.fromtimestamp(node.added_at).strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if node.content_types:
            lines.append(f"Content:   {', '.join(set(node.content_types[:5]))}")
        self.txt_detail.setPlainText("\n".join(lines))

    def _clear(self):
        self.mapper.clear()
        self.tree.clear()
        self._host_items.clear()
        self._url_items.clear()
        self.txt_detail.clear()
        self.lbl_stats.setText("0 URLs | 0 Hosts")

    def _export(self):
        import json
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Site Map", "sitemap.json", "JSON (*.json)")
        if path:
            data = self.mapper.export_dict()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def _search(self, text: str):
        def _show_all(item):
            item.setHidden(False)
            for i in range(item.childCount()):
                _show_all(item.child(i))

        if not text:
            for i in range(self.tree.topLevelItemCount()):
                _show_all(self.tree.topLevelItem(i))
            return

        text = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            host_item = self.tree.topLevelItem(i)
            any_visible = False
            for j in range(host_item.childCount()):
                child = host_item.child(j)
                url = child.data(0, Qt.ItemDataRole.UserRole) or ""
                match = text in url.lower()
                child.setHidden(not match)
                if match:
                    any_visible = True
            host_item.setHidden(not any_visible)
