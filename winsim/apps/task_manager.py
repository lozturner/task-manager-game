"""WinSim — Virtual Task Manager (gameplay centrepiece)."""
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon, QPainter, QLinearGradient, QPen
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTreeWidget, QTreeWidgetItem,
                              QHeaderView, QMenu, QTabWidget, QAbstractItemView,
                              QStyledItemDelegate, QStyleOptionViewItem, QStyle)
from .. import skins
from ..widgets import PerfGraph, Card


class BarDelegate(QStyledItemDelegate):
    """Draws an inline progress bar behind the text for CPU/Memory columns."""

    # column -> (max_value, low_colour, high_colour)
    COLUMN_CONFIG = {
        3: (100.0, "#d4e8fc", "#0078d4"),   # CPU %  — blue
        4: (4096.0, "#ead4fc", "#af52de"),   # RAM MB — purple
    }

    def paint(self, painter, option, index):
        col = index.column()
        if col not in self.COLUMN_CONFIG:
            super().paint(painter, option, index)
            return

        max_val, lo_col, hi_col = self.COLUMN_CONFIG[col]

        # Parse numeric value from text like "3.3%" or "82 MB"
        raw = index.data(Qt.DisplayRole) or ""
        try:
            val = float(raw.replace("%", "").replace("MB", "").strip())
        except ValueError:
            super().paint(painter, option, index)
            return

        ratio = min(1.0, max(0.0, val / max_val))

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect

        # Draw selection/alternate background first
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, QColor(skins.get("select")))
        elif index.row() % 2 == 1:
            painter.fillRect(rect, QColor("#f8f8f8"))
        else:
            painter.fillRect(rect, QColor(skins.get("card")))

        # Draw the bar
        bar_margin = 3
        bar_rect = QRect(
            rect.x() + bar_margin,
            rect.y() + bar_margin,
            int((rect.width() - bar_margin * 2) * ratio),
            rect.height() - bar_margin * 2,
        )
        if bar_rect.width() > 0:
            # Gradient from low to high colour based on value
            intensity = min(1.0, ratio * 2.5)  # ramp up faster
            bar_col = QColor(lo_col)
            hi = QColor(hi_col)
            r = bar_col.red() + int((hi.red() - bar_col.red()) * intensity)
            g = bar_col.green() + int((hi.green() - bar_col.green()) * intensity)
            b = bar_col.blue() + int((hi.blue() - bar_col.blue()) * intensity)
            bar_col = QColor(r, g, b, 140)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_col)
            painter.drawRoundedRect(bar_rect, 2, 2)

        # Draw the text on top
        text_rect = rect.adjusted(4, 0, -4, 0)
        painter.setPen(QColor(skins.get("text")))
        painter.setFont(QFont(skins.get("font"), 8))
        painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, raw)

        painter.restore()


class VirtualTaskManager(QWidget):
    """Task Manager UI for the game's virtual processes."""
    def __init__(self, kernel, parent=None):
        super().__init__(parent)
        self.kernel = kernel
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {skins.get('win_bg')}; }}
            QTabBar::tab {{
                background: {skins.get('win_bg')}; color: {skins.get('text2')};
                padding: 8px 16px; border: none; border-bottom: 2px solid transparent;
                font: 11px '{skins.get('font')}';
            }}
            QTabBar::tab:selected {{
                color: {skins.get('accent')}; border-bottom: 2px solid {skins.get('accent')};
            }}
        """)

        tabs.addTab(self._build_processes(), "Processes")
        tabs.addTab(self._build_performance(), "Performance")
        layout.addWidget(tabs)

    def _build_processes(self):
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(6)

        # Process tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["", "Name", "PID", "CPU", "Memory", "Status", "Description"])
        self._tree.setColumnWidth(0, 24)
        self._tree.setColumnWidth(1, 140)
        self._tree.setColumnWidth(2, 50)
        self._tree.setColumnWidth(3, 90)
        self._tree.setColumnWidth(4, 100)
        self._tree.setColumnWidth(5, 70)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._context_menu)
        self._tree.setItemDelegate(BarDelegate(self._tree))
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {skins.get('card')}; border: 1px solid {skins.get('border')};
                font: 11px '{skins.get('font')}'; color: {skins.get('text')};
            }}
            QTreeWidget::item {{ height: 24px; }}
            QTreeWidget::item:alternate {{ background: #f8f8f8; }}
            QTreeWidget::item:selected {{ background: {skins.get('select')}; }}
            QHeaderView::section {{
                background: {skins.get('bg')}; color: {skins.get('text2')};
                border: none; border-bottom: 1px solid {skins.get('border')};
                font: 10px '{skins.get('font')}'; padding: 4px;
            }}
        """)
        pl.addWidget(self._tree)

        # Bottom bar
        bottom = QHBoxLayout()
        self._status = QLabel("0 processes")
        self._status.setStyleSheet(f"color: {skins.get('text2')}; font: 10px '{skins.get('font')}';")
        bottom.addWidget(self._status)
        bottom.addStretch()

        end_btn = QPushButton("End Task")
        end_btn.setCursor(Qt.PointingHandCursor)
        end_btn.setStyleSheet(f"""
            QPushButton {{
                background: {skins.get('danger')}; color: white; border: none;
                border-radius: 4px; font: 11px '{skins.get('font')}'; padding: 4px 16px;
            }}
            QPushButton:hover {{ background: #c41020; }}
        """)
        end_btn.clicked.connect(self._end_task)
        bottom.addWidget(end_btn)
        pl.addLayout(bottom)

        # Context menu
        self._menu = QMenu(self)
        self._menu.setStyleSheet(f"""
            QMenu {{ background: {skins.get('card')}; border: 1px solid {skins.get('border')};
                     font: 11px '{skins.get('font')}'; padding: 4px; }}
            QMenu::item {{ padding: 5px 16px; }}
            QMenu::item:selected {{ background: {skins.get('select')}; }}
        """)
        self._menu.addAction("End Task", self._end_task)
        self._menu.addSeparator()
        pri_menu = self._menu.addMenu("Set Priority")
        for label, val in [("Realtime", 24), ("High", 13), ("Above Normal", 10),
                            ("Normal", 8), ("Below Normal", 6), ("Low", 4)]:
            pri_menu.addAction(label, lambda v=val: self._set_priority(v))
        self._menu.addSeparator()
        self._menu.addAction("Suspend", self._suspend)
        self._menu.addAction("Resume", self._resume)

        return page

    def _build_performance(self):
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(12, 12, 12, 12)
        pl.setSpacing(8)

        cpu_lbl = QLabel("CPU")
        cpu_lbl.setStyleSheet(f"color: {skins.get('text')}; font: bold 13px '{skins.get('font')}';")
        pl.addWidget(cpu_lbl)
        self._cpu_graph = PerfGraph(skins.get("accent"))
        pl.addWidget(self._cpu_graph)

        mem_lbl = QLabel("Memory")
        mem_lbl.setStyleSheet(f"color: {skins.get('text')}; font: bold 13px '{skins.get('font')}';")
        pl.addWidget(mem_lbl)
        self._mem_graph = PerfGraph("#af52de")
        pl.addWidget(self._mem_graph)

        pl.addStretch()
        return page

    def refresh(self):
        """Called by game loop to update the display."""
        tree = self._tree
        sel_pid = None
        sel = tree.currentItem()
        if sel:
            try: sel_pid = int(sel.text(2))
            except (ValueError, TypeError): pass

        tree.setUpdatesEnabled(False)
        tree.clear()
        reselect = None
        procs = sorted(list(self.kernel.processes.values()), key=lambda p: p.cpu_usage, reverse=True)
        for p in procs:
            item = QTreeWidgetItem()
            pm = QPixmap(16, 16)
            pm.fill(QColor(p.colour))
            item.setIcon(0, QIcon(pm))
            item.setText(1, p.name)
            item.setText(2, str(p.pid))
            item.setText(3, f"{p.cpu_usage:.1f}%")
            item.setText(4, f"{p.ram_mb:.0f} MB")
            item.setText(5, p.status.capitalize())
            item.setText(6, p.description)
            for c in (2, 3, 4):
                item.setTextAlignment(c, Qt.AlignRight | Qt.AlignVCenter)
            if p.is_malware:
                for c in range(7):
                    item.setForeground(c, QColor(skins.get("danger")))
            tree.addTopLevelItem(item)
            if sel_pid and p.pid == sel_pid:
                reselect = item

        tree.setUpdatesEnabled(True)
        if reselect:
            tree.setCurrentItem(reselect)

        self._status.setText(f"{len(procs)} processes | "
                              f"CPU {self.kernel.get_cpu_percent():.0f}% | "
                              f"RAM {self.kernel.memory.get_percent(self.kernel.processes):.0f}%")

        # Graphs
        self._cpu_graph.set_data(self.kernel.cpu_history)
        self._mem_graph.set_data(self.kernel.mem_history)

    def _get_pid(self):
        item = self._tree.currentItem()
        if item:
            try: return int(item.text(2))
            except (ValueError, TypeError): pass
        return None

    def _end_task(self):
        pid = self._get_pid()
        if pid:
            self.kernel.kill(pid)
            self.refresh()

    def _set_priority(self, val):
        pid = self._get_pid()
        if pid:
            self.kernel.set_priority(pid, val)

    def _suspend(self):
        pid = self._get_pid()
        if pid:
            self.kernel.suspend(pid)
            self.refresh()

    def _resume(self):
        pid = self._get_pid()
        if pid:
            self.kernel.resume(pid)
            self.refresh()

    def _context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if item:
            self._tree.setCurrentItem(item)
            self._menu.exec_(self._tree.viewport().mapToGlobal(pos))
