"""WinSim — Window manager. Draggable game windows with Win10 title bar."""
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QIcon, QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSizePolicy, QGraphicsDropShadowEffect)
from . import skins


class TitleBarButton(QPushButton):
    def __init__(self, char, hover_bg, hover_fg="#ffffff", parent=None):
        super().__init__(char, parent)
        self._hover_bg = hover_bg
        self._hover_fg = hover_fg
        self.setFixedSize(46, 30)
        self.setFlat(True)
        self.setCursor(Qt.ArrowCursor)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {skins.get('win_title_text')};
                border: none; font: 14px 'Segoe MDL2 Assets', 'Segoe UI';
            }}
            QPushButton:hover {{
                background: {self._hover_bg}; color: {self._hover_fg};
            }}
        """)


class GameWindow(QWidget):
    """A draggable, closeable window that mimics Win10 chrome."""
    closed = pyqtSignal(str)       # emits window_id
    minimized = pyqtSignal(str)
    focused = pyqtSignal(str)

    def __init__(self, window_id, title, content_widget, icon_text="AP",
                 icon_colour="#0078d4", size=(600, 400), parent=None):
        super().__init__(parent)
        self.window_id = window_id
        self._title_text = title
        self._dragging = False
        self._drag_pos = QPoint()
        self._maximized = False
        self._normal_geo = None

        self.setMinimumSize(300, 200)
        self.resize(*size)
        self.setStyleSheet(f"background: transparent;")

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        # Main frame
        frame = QWidget(self)
        frame.setStyleSheet(f"""
            background: {skins.get('win_bg')};
            border: 1px solid {skins.get('win_border')};
        """)
        frame_layout = QVBoxLayout(self)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(frame)

        inner = QVBoxLayout(frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # ── Title bar ────────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet(f"background: {skins.get('win_title_bg')}; border: none;")
        title_bar.setCursor(Qt.ArrowCursor)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(8, 0, 0, 0)
        tb_layout.setSpacing(6)

        # App icon (small coloured square)
        icon_lbl = QLabel()
        pm = QPixmap(16, 16)
        pm.fill(QColor(icon_colour))
        icon_lbl.setPixmap(pm)
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        tb_layout.addWidget(icon_lbl)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"""
            color: {skins.get('win_title_text')}; font: 12px '{skins.get('font')}';
            background: transparent; border: none;
        """)
        tb_layout.addWidget(self._title_label)
        tb_layout.addStretch()

        # Window buttons
        min_btn = TitleBarButton("\u2013", skins.get("win_title_btn"), skins.get("win_title_text"))
        min_btn.clicked.connect(self._on_minimize)
        tb_layout.addWidget(min_btn)

        max_btn = TitleBarButton("\u25a1", skins.get("win_title_btn"), skins.get("win_title_text"))
        max_btn.clicked.connect(self._on_maximize)
        tb_layout.addWidget(max_btn)

        close_btn = TitleBarButton("\u2715", skins.get("win_close_hover"), skins.get("win_close_text"))
        close_btn.clicked.connect(self._on_close)
        tb_layout.addWidget(close_btn)

        inner.addWidget(title_bar)

        # ── Content ──────────────────────────────────────────────────────
        content_widget.setStyleSheet(f"background: {skins.get('win_bg')}; border: none;")
        inner.addWidget(content_widget, 1)

        # Title bar drag
        title_bar.mousePressEvent = self._title_press
        title_bar.mouseMoveEvent = self._title_move
        title_bar.mouseReleaseEvent = self._title_release

    def _title_press(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.pos()
            self.focused.emit(self.window_id)

    def _title_move(self, event):
        if self._dragging:
            if self._maximized:
                self._on_maximize()  # unmaximize on drag
            self.move(event.globalPos() - self._drag_pos)

    def _title_release(self, event):
        self._dragging = False

    def _on_minimize(self):
        self.hide()
        self.minimized.emit(self.window_id)

    def _on_maximize(self):
        if self._maximized:
            if self._normal_geo:
                self.setGeometry(self._normal_geo)
            self._maximized = False
        else:
            self._normal_geo = self.geometry()
            if self.parent():
                pr = self.parent().rect()
                self.setGeometry(0, 0, pr.width(), pr.height() - 40)
            self._maximized = True

    def _on_close(self):
        self.hide()
        self.closed.emit(self.window_id)

    def mousePressEvent(self, event):
        self.focused.emit(self.window_id)
        super().mousePressEvent(event)

    def activate(self):
        self.show()
        self.raise_()
