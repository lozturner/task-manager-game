"""WinSim — Taskbar, start menu, system tray, clock."""
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                              QVBoxLayout, QFrame, QMenu)
from . import skins


class TaskbarAppButton(QPushButton):
    """Button for a running app in the taskbar."""
    def __init__(self, window_id, title, icon_char, colour, parent=None):
        super().__init__(parent)
        self.window_id = window_id
        self.setText(f" {icon_char} {title[:15]}")
        self.setFixedHeight(34)
        self.setMinimumWidth(60)
        self.setMaximumWidth(160)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {skins.get('taskbar_text')};
                border: none; border-bottom: 2px solid transparent;
                font: 11px '{skins.get('font')}'; text-align: left; padding: 0 8px;
            }}
            QPushButton:hover {{ background: {skins.get('taskbar_hover')}; }}
            QPushButton:checked {{
                border-bottom: 2px solid {skins.get('accent')};
                background: {skins.get('taskbar_active')};
            }}
        """)


class StartMenu(QWidget):
    """Win10-style start menu popup."""
    app_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 400)
        self.setStyleSheet(f"""
            background: {skins.get('start_menu_bg')};
            border: 1px solid #444;
        """)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        # App list
        apps = ["Task Manager", "File Explorer", "Notepad", "Control Panel",
                "Chrome", "Edge", "Spotify", "Discord", "VS Code"]
        for name in apps:
            btn = QPushButton(f"  {name}")
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {skins.get('start_menu_text')};
                    border: none; font: 12px '{skins.get('font')}'; text-align: left;
                    padding-left: 16px;
                }}
                QPushButton:hover {{ background: {skins.get('start_menu_hover')}; }}
            """)
            btn.clicked.connect(lambda _, n=name: (self.hide(), self.app_clicked.emit(n)))
            layout.addWidget(btn)

        layout.addStretch()

        # Power bar
        power = QWidget()
        power.setFixedHeight(44)
        power.setStyleSheet(f"background: #222226; border: none;")
        pl = QHBoxLayout(power)
        pl.setContentsMargins(8, 0, 8, 0)
        for label, action in [("Shut Down", "shutdown"), ("Restart", "restart")]:
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: #ccc; border: none;
                    font: 11px '{skins.get('font')}'; padding: 4px 12px;
                }}
                QPushButton:hover {{ background: #333; }}
            """)
            b.clicked.connect(lambda _, a=action: (self.hide(), self.app_clicked.emit(f"__power__{a}")))
            pl.addWidget(b)
        pl.addStretch()
        layout.addWidget(power)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            # Position above taskbar
            if self.parent():
                px = 0
                py = self.parent().height() - self.height() - 40
                self.move(px, py)
            self.show()
            self.raise_()


class Taskbar(QWidget):
    """Win10-style taskbar at the bottom."""
    app_button_clicked = pyqtSignal(str)  # window_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"background: {skins.get('taskbar_bg')};")
        self._app_buttons: dict = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        # Start button
        self._start_btn = QPushButton(" \u229E ")
        self._start_btn.setFixedSize(48, 40)
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {skins.get('taskbar_text')};
                border: none; font: 18px '{skins.get('font')}';
            }}
            QPushButton:hover {{ background: {skins.get('taskbar_hover')}; }}
        """)
        layout.addWidget(self._start_btn)

        # Search (decorative)
        search = QLabel("  \U0001F50D  Search")
        search.setFixedSize(180, 34)
        search.setStyleSheet(f"""
            background: #2a2a3e; color: #888; border-radius: 4px;
            font: 11px '{skins.get('font')}'; padding-left: 4px;
        """)
        layout.addWidget(search)

        # App buttons area
        self._apps_layout = QHBoxLayout()
        self._apps_layout.setSpacing(2)
        layout.addLayout(self._apps_layout)

        layout.addStretch()

        # System tray area
        tray = QWidget()
        tray.setFixedWidth(220)
        tray_layout = QHBoxLayout(tray)
        tray_layout.setContentsMargins(8, 0, 0, 0)
        tray_layout.setSpacing(12)

        # CPU/RAM mini indicators
        self._cpu_lbl = QLabel("CPU 0%")
        self._cpu_lbl.setStyleSheet(f"color: #88aacc; font: 9px '{skins.get('font_mono')}'; background: transparent;")
        tray_layout.addWidget(self._cpu_lbl)

        self._ram_lbl = QLabel("RAM 0%")
        self._ram_lbl.setStyleSheet(f"color: #aa88cc; font: 9px '{skins.get('font_mono')}'; background: transparent;")
        tray_layout.addWidget(self._ram_lbl)

        # XP display
        self._xp_lbl = QLabel("XP: 0")
        self._xp_lbl.setStyleSheet(f"color: #ffcc00; font: bold 10px '{skins.get('font')}'; background: transparent;")
        tray_layout.addWidget(self._xp_lbl)

        # Clock
        self._clock = QLabel()
        self._clock.setStyleSheet(f"color: {skins.get('taskbar_text')}; font: 11px '{skins.get('font')}'; background: transparent;")
        tray_layout.addWidget(self._clock)

        layout.addWidget(tray)

        # Clock timer
        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def connect_start_button(self, callback):
        self._start_btn.clicked.connect(callback)

    def _update_clock(self):
        self._clock.setText(datetime.now().strftime("%H:%M"))

    def update_stats(self, cpu, ram, xp=0):
        self._cpu_lbl.setText(f"CPU {cpu:.0f}%")
        self._ram_lbl.setText(f"RAM {ram:.0f}%")
        self._xp_lbl.setText(f"XP: {xp}")

        # Colour coding
        cpu_col = "#ff4444" if cpu > 80 else "#ffaa00" if cpu > 50 else "#88aacc"
        ram_col = "#ff4444" if ram > 85 else "#ffaa00" if ram > 60 else "#aa88cc"
        self._cpu_lbl.setStyleSheet(f"color: {cpu_col}; font: 9px '{skins.get('font_mono')}'; background: transparent;")
        self._ram_lbl.setStyleSheet(f"color: {ram_col}; font: 9px '{skins.get('font_mono')}'; background: transparent;")

    def add_app_button(self, window_id, title, icon_char="AP", colour="#0078d4"):
        btn = TaskbarAppButton(window_id, title, icon_char, colour)
        btn.setChecked(True)
        btn.clicked.connect(lambda: self.app_button_clicked.emit(window_id))
        self._apps_layout.addWidget(btn)
        self._app_buttons[window_id] = btn

    def remove_app_button(self, window_id):
        btn = self._app_buttons.pop(window_id, None)
        if btn:
            self._apps_layout.removeWidget(btn)
            btn.deleteLater()

    def set_active(self, window_id):
        for wid, btn in self._app_buttons.items():
            btn.setChecked(wid == window_id)
