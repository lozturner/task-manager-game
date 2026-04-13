"""
Task Manager v1.0.0 — OS Simulator Game
A fake Windows desktop where you manage virtual processes, memory, and disk.
Missions teach you how Windows works by playing.
"""
__version__ = "1.0.0"

import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout

from .game_engine import GameEngine
from .desktop import Desktop
from .taskbar import Taskbar, StartMenu
from .window_manager import GameWindow
from .widgets import ToastNotification, TutorialOverlay
from .apps.task_manager import VirtualTaskManager
from .apps.file_explorer import VirtualFileExplorer
from .apps.notepad import VirtualNotepad
from .apps.control_panel import VirtualControlPanel
from . import skins


APP_REGISTRY = {
    "Task Manager":  {"icon": "TM", "colour": "#0078d4", "size": (700, 480)},
    "File Explorer": {"icon": "FE", "colour": "#ffc107", "size": (650, 450)},
    "Notepad":       {"icon": "NP", "colour": "#ffd54f", "size": (500, 380)},
    "Control Panel": {"icon": "CP", "colour": "#5c6bc0", "size": (550, 420)},
}


class WinSimWindow(QWidget):
    """Main game window — the fake Windows desktop."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Manager — OS Simulator")
        self.setMinimumSize(1024, 640)
        self.resize(1200, 750)
        self.setStyleSheet("background: #000;")

        # Engine
        self.engine = GameEngine()
        self.engine.toast.connect(self._show_toast)

        # Open windows tracking
        self._windows = {}     # window_id -> GameWindow
        self._app_widgets = {} # window_id -> app widget (for refresh)
        self._next_win_id = 1

        # Layout: desktop + taskbar
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Desktop (takes all space)
        self._desktop = Desktop(launch_callback=self._launch_app)
        layout.addWidget(self._desktop, 1)

        # Taskbar
        self._taskbar = Taskbar()
        self._taskbar.app_button_clicked.connect(self._on_taskbar_click)
        layout.addWidget(self._taskbar)

        # Start menu
        self._start_menu = StartMenu(self)
        self._start_menu.app_clicked.connect(self._on_start_menu)
        self._taskbar.connect_start_button(self._start_menu.toggle)

        # Game loop timer (500ms)
        self._game_timer = QTimer()
        self._game_timer.timeout.connect(self._game_tick)
        self._game_timer.start(500)

        # UI refresh timer (1s)
        self._ui_timer = QTimer()
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.start(1000)

        # Tutorial overlay
        self._tutorial = TutorialOverlay(self)
        self._tutorial.finished.connect(self._on_tutorial_done)
        self._tutorial.hide()

        # Auto-launch Task Manager + show tutorial after a short delay
        QTimer.singleShot(600, self._auto_start)

    # ── Tutorial / auto-start ────────────────────────────────────────────
    def _auto_start(self):
        """Auto-launch Task Manager and show the tutorial overlay."""
        self._launch_app("Task Manager")
        # Show tutorial over everything
        QTimer.singleShot(400, self._show_tutorial)

    def _show_tutorial(self):
        self._tutorial.setGeometry(0, 0, self.width(), self.height())
        self._tutorial.start()

    def _on_tutorial_done(self):
        """Tutorial finished — game is fully live."""
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_tutorial') and self._tutorial.isVisible():
            self._tutorial.setGeometry(0, 0, self.width(), self.height())

    # ── App launching ────────────────────────────────────────────────────
    def _launch_app(self, name):
        # Check if already open (safe snapshot)
        for wid, gw in list(self._windows.items()):
            if gw._title_text == name and gw.isVisible():
                gw.activate()
                self._taskbar.set_active(wid)
                return

        reg = APP_REGISTRY.get(name)
        if not reg:
            # Try launching as a kernel process anyway
            self.engine.launch_app(name)
            return

        # Create the app widget
        kernel = self.engine.kernel
        if name == "Task Manager":
            widget = VirtualTaskManager(kernel)
            widget.refresh()
        elif name == "File Explorer":
            widget = VirtualFileExplorer(kernel)
            widget.refresh()
        elif name == "Notepad":
            widget = VirtualNotepad(kernel)
        elif name == "Control Panel":
            widget = VirtualControlPanel(kernel)
            widget.refresh()
        else:
            return

        # Spawn process in virtual OS
        self.engine.launch_app(name)

        # Create game window
        wid = f"win_{self._next_win_id}"
        self._next_win_id += 1

        gw = GameWindow(wid, name, widget,
                         icon_text=reg["icon"], icon_colour=reg["colour"],
                         size=reg["size"], parent=self._desktop)
        gw.closed.connect(self._on_window_closed)
        gw.minimized.connect(self._on_window_minimized)
        gw.focused.connect(self._on_window_focused)

        # Position with slight offset
        offset = len(self._windows) * 30
        gw.move(80 + offset, 40 + offset)
        gw.show()
        gw.raise_()

        self._windows[wid] = gw
        self._app_widgets[wid] = widget
        self._taskbar.add_app_button(wid, name, reg["icon"], reg["colour"])
        self._taskbar.set_active(wid)

    def _on_window_closed(self, wid):
        gw = self._windows.pop(wid, None)
        self._app_widgets.pop(wid, None)
        self._taskbar.remove_app_button(wid)
        if gw:
            gw.deleteLater()

    def _on_window_minimized(self, wid):
        self._taskbar.set_active("")

    def _on_window_focused(self, wid):
        self._taskbar.set_active(wid)
        # Raise to top
        gw = self._windows.get(wid)
        if gw:
            gw.raise_()

    def _on_taskbar_click(self, wid):
        gw = self._windows.get(wid)
        if gw:
            if gw.isVisible():
                gw.hide()
                self._taskbar.set_active("")
            else:
                gw.activate()
                self._taskbar.set_active(wid)

    def _on_start_menu(self, name):
        if name.startswith("__power__"):
            action = name.replace("__power__", "")
            if action == "shutdown":
                self.engine.save()
                QApplication.quit()
            elif action == "restart":
                self.engine.kernel.boot_sequence()
                self.engine.active_missions.clear()
                self.engine.score = 0
                for wid in list(self._windows):
                    self._on_window_closed(wid)
        else:
            self._launch_app(name)

    # ── Game loop ────────────────────────────────────────────────────────
    def _game_tick(self):
        self.engine.tick(0.5)

    def _refresh_ui(self):
        # Update taskbar stats
        s = self.engine.kernel.get_summary()
        self._taskbar.update_stats(s["cpu_pct"], s["mem_pct"], self.engine.xp)

        # Refresh open app widgets (safe snapshot)
        for wid, widget in list(self._app_widgets.items()):
            gw = self._windows.get(wid)
            if gw and gw.isVisible() and hasattr(widget, 'refresh'):
                widget.refresh()

    def _show_toast(self, title, message):
        t = ToastNotification(title, message, self)
        t.show_at(self)

    def closeEvent(self, event):
        self.engine.save()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    win = WinSimWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
