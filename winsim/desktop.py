"""WinSim — Desktop surface with icons and wallpaper."""
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QLinearGradient, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from . import skins


class DesktopIcon(QWidget):
    """A desktop icon — double-click to launch."""
    def __init__(self, name, icon_char, colour, parent=None):
        super().__init__(parent)
        self.app_name = name
        self.setFixedSize(80, 80)
        self.setCursor(Qt.PointingHandCursor)
        self._icon_char = icon_char
        self._colour = colour
        self._selected = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self._selected:
            p.fillRect(0, 0, 80, 80, QColor(255, 255, 255, 40))

        # Icon box
        p.setBrush(QColor(self._colour))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(22, 4, 36, 36, 6, 6)

        # Icon text
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont(skins.get("font_mono"), 12, QFont.Bold))
        p.drawText(22, 4, 36, 36, Qt.AlignCenter, self._icon_char)

        # Label with shadow
        p.setPen(QColor(0, 0, 0, 120))
        p.setFont(QFont(skins.get("font"), 9))
        p.drawText(1, 45, 79, 34, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.app_name)
        p.setPen(QColor(skins.get("icon_text")))
        p.drawText(0, 44, 79, 34, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.app_name)
        p.end()

    def mousePressEvent(self, event):
        self._selected = True
        self.update()

    def mouseDoubleClickEvent(self, event):
        # Parent (Desktop) handles launch
        if self.parent() and hasattr(self.parent(), 'launch_app'):
            self.parent().launch_app(self.app_name)


DESKTOP_ICONS = [
    ("Task Manager",  "TM", "#0078d4"),
    ("File Explorer", "FE", "#ffc107"),
    ("Notepad",       "NP", "#ffd54f"),
    ("Control Panel", "CP", "#5c6bc0"),
    ("This PC",       "PC", "#78909c"),
    ("Recycle Bin",   "RB", "#9e9e9e"),
]


class Desktop(QWidget):
    """The desktop surface — wallpaper gradient + icons."""
    def __init__(self, launch_callback=None, parent=None):
        super().__init__(parent)
        self._launch_cb = launch_callback
        self._icons = []

        for i, (name, char, colour) in enumerate(DESKTOP_ICONS):
            icon = DesktopIcon(name, char, colour, self)
            col, row = divmod(i, 4)
            icon.move(20 + col * 90, 20 + row * 90)
            self._icons.append(icon)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(skins.get("desktop_bg_top")))
        grad.setColorAt(1, QColor(skins.get("desktop_bg_bottom")))
        p.fillRect(self.rect(), grad)
        p.end()

    def launch_app(self, name):
        if self._launch_cb:
            self._launch_cb(name)

    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {skins.get('card')}; border: 1px solid {skins.get('border')};
                     border-radius: 4px; font: 12px '{skins.get('font')}'; padding: 4px; }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{ background: {skins.get('select')}; }}
        """)
        menu.addAction("Refresh", lambda: None)
        menu.addSeparator()
        menu.addAction("View \u2192 Large icons", lambda: None)
        menu.addAction("Personalise...", lambda: None)
        menu.exec_(self.mapToGlobal(pos))

    def mousePressEvent(self, event):
        # Deselect all icons
        for icon in self._icons:
            icon._selected = False
            icon.update()
