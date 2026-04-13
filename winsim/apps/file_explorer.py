"""WinSim — Virtual File Explorer."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTreeWidget, QTreeWidgetItem, QMenu)
from .. import skins


class VirtualFileExplorer(QWidget):
    def __init__(self, kernel, parent=None):
        super().__init__(parent)
        self.kernel = kernel
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Breadcrumb
        nav = QHBoxLayout()
        self._path_lbl = QLabel("C:/")
        self._path_lbl.setStyleSheet(f"""
            background: {skins.get('card')}; border: 1px solid {skins.get('border')};
            padding: 4px 8px; font: 11px '{skins.get('font')}'; color: {skins.get('text')};
        """)
        nav.addWidget(self._path_lbl, 1)
        layout.addLayout(nav)

        # File tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Size", "Type"])
        self._tree.setColumnWidth(0, 300)
        self._tree.setColumnWidth(1, 80)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {skins.get('card')}; border: 1px solid {skins.get('border')};
                font: 11px '{skins.get('font')}'; color: {skins.get('text')};
            }}
            QTreeWidget::item {{ height: 22px; }}
            QTreeWidget::item:alternate {{ background: #f8f8f8; }}
            QTreeWidget::item:selected {{ background: {skins.get('select')}; }}
            QHeaderView::section {{
                background: {skins.get('bg')}; color: {skins.get('text2')};
                border: none; border-bottom: 1px solid {skins.get('border')};
                font: 10px '{skins.get('font')}'; padding: 4px;
            }}
        """)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._ctx_menu)
        layout.addWidget(self._tree)

        # Status
        bottom = QHBoxLayout()
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {skins.get('text2')}; font: 10px '{skins.get('font')}';")
        bottom.addWidget(self._status)
        bottom.addStretch()

        del_btn = QPushButton("Delete Selected")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: {skins.get('danger')}; color: white; border: none;
                border-radius: 4px; font: 11px '{skins.get('font')}'; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: #c41020; }}
        """)
        del_btn.clicked.connect(self._delete_selected)
        bottom.addWidget(del_btn)
        layout.addLayout(bottom)

    def refresh(self):
        self._tree.clear()
        disk = self.kernel.disk
        files = sorted(list(disk.files.values()), key=lambda f: f.path)

        for f in files:
            item = QTreeWidgetItem()
            item.setText(0, f.path)
            item.setText(1, f"{f.size_mb:.1f} MB" if f.size_mb >= 1 else f"{f.size_mb*1024:.0f} KB")
            item.setText(2, f.file_type)
            item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            if f.file_type == "temp":
                for c in range(3):
                    item.setForeground(c, QColor(skins.get("warning")))
            elif f.file_type == "system":
                for c in range(3):
                    item.setForeground(c, QColor(skins.get("text2")))
            self._tree.addTopLevelItem(item)

        self._status.setText(
            f"{len(files)} files | {disk.get_used_gb():.1f} GB / {disk.total_gb:.0f} GB "
            f"({disk.get_percent():.0f}%) | Free: {disk.get_free_gb():.1f} GB")

    def _delete_selected(self):
        item = self._tree.currentItem()
        if item:
            path = item.text(0)
            f = self.kernel.disk.files.get(path)
            if f and f.file_type in ("temp", "file"):
                self.kernel.disk.delete_file(path)
                self.kernel.log(f"Deleted: {path}")
                self.refresh()

    def _ctx_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        self._tree.setCurrentItem(item)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {skins.get('card')}; border: 1px solid {skins.get('border')};
                     font: 11px '{skins.get('font')}'; padding: 4px; }}
            QMenu::item {{ padding: 5px 16px; }}
            QMenu::item:selected {{ background: {skins.get('select')}; }}
        """)
        menu.addAction("Delete", self._delete_selected)
        menu.exec_(self._tree.viewport().mapToGlobal(pos))
