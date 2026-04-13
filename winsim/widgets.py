"""WinSim — Reusable UI widgets (adapted from DevSpy patterns)."""
from PyQt5.QtCore import (Qt, QRectF, QPointF, QTimer, QPropertyAnimation,
                           QEasingCurve, QPoint, pyqtSignal)
from PyQt5.QtGui import (QPainter, QPainterPath, QColor, QFont, QLinearGradient,
                          QPen, QBrush, QFontMetrics, QRegion, QRadialGradient)
from PyQt5.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
                              QHBoxLayout, QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from . import skins


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_style()
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 18))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def _apply_style(self):
        self.setStyleSheet(f"""
            Card {{ background: {skins.get('card')}; border-radius: 8px;
                    border: 1px solid {skins.get('border')}; }}
        """)


class PerfGraph(QWidget):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._data = []
        self._color = QColor(color or skins.get("accent"))
        self.setMinimumHeight(120)

    def set_data(self, data):
        self._data = data[-60:]
        self.update()

    def paintEvent(self, event):
        if len(self._data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(skins.get("card")))

        # Grid
        pen = QPen(QColor(skins.get("border")), 0.5, Qt.DotLine)
        p.setPen(pen)
        for i in range(1, 5):
            y = h * i // 5
            p.drawLine(0, y, w, y)

        n = len(self._data)
        path = QPainterPath()
        fill = QPainterPath()

        def pt(i, v):
            return QPointF(w * i / (n - 1), h * (1 - v / 100.0))

        path.moveTo(pt(0, self._data[0]))
        fill.moveTo(QPointF(0, h))
        fill.lineTo(pt(0, self._data[0]))
        for i in range(1, n):
            path.lineTo(pt(i, self._data[i]))
            fill.lineTo(pt(i, self._data[i]))
        fill.lineTo(QPointF(w, h))
        fill.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        c = QColor(self._color)
        c.setAlpha(50)
        grad.setColorAt(0, c)
        c.setAlpha(5)
        grad.setColorAt(1, c)
        p.fillPath(fill, QBrush(grad))

        p.setPen(QPen(self._color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)

        p.setPen(QColor(skins.get("text")))
        p.setFont(QFont(skins.get("font"), 9, QFont.Bold))
        p.drawText(QRectF(w - 60, 4, 54, 20), Qt.AlignRight, f"{self._data[-1]:.0f}%")
        p.end()


class ToastNotification(QWidget):
    """Windows 10 style slide-in notification."""
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setFixedSize(340, 80)
        self.setStyleSheet(f"""
            background: {skins.get('toast_bg')}; border-radius: 6px;
            border: 1px solid #444444;
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        t = QLabel(title)
        t.setStyleSheet(f"color: {skins.get('toast_accent')}; font: bold 12px '{skins.get('font')}'; background: transparent; border: none;")
        layout.addWidget(t)

        m = QLabel(message)
        m.setWordWrap(True)
        m.setStyleSheet(f"color: {skins.get('toast_text')}; font: 11px '{skins.get('font')}'; background: transparent; border: none;")
        layout.addWidget(m)

        # Auto-dismiss after 6 seconds
        QTimer.singleShot(6000, self._dismiss)

    def _dismiss(self):
        self.hide()
        self.deleteLater()

    def show_at(self, parent_widget):
        pw = parent_widget.width()
        self.move(pw - self.width() - 12, 12)
        self.show()
        self.raise_()


# ── Tutorial Overlay ─────────────────────────────────────────────────────────

TUTORIAL_STEPS = [
    {
        "target": "desktop",
        "title": "Welcome to Task Manager!",
        "text": "This is your virtual Windows desktop.\n"
                "Double-click icons to launch apps.\n"
                "Manage processes, memory, and disk to complete missions!",
        "offset": (0.35, 0.35),
        "radius": 180,
    },
    {
        "target": "desktop_icons",
        "title": "Desktop Icons",
        "text": "These are your apps — Task Manager, File Explorer,\n"
                "Notepad, and Control Panel.\n"
                "Double-click any icon to open it.",
        "offset": (0.08, 0.2),
        "radius": 120,
    },
    {
        "target": "taskbar",
        "title": "The Taskbar",
        "text": "Running apps appear here. Click to show/hide windows.\n"
                "The Start button opens the app launcher.",
        "offset": (0.3, 0.96),
        "radius": 100,
    },
    {
        "target": "system_tray",
        "title": "System Tray",
        "text": "CPU, RAM, and XP stats update in real-time.\n"
                "Keep an eye on resource usage!",
        "offset": (0.85, 0.96),
        "radius": 90,
    },
    {
        "target": "task_manager",
        "title": "Task Manager",
        "text": "This is where the action is! View running processes,\n"
                "right-click to End Task, Set Priority, or Suspend.\n"
                "Complete missions to earn XP and level up!",
        "offset": (0.45, 0.4),
        "radius": 200,
    },
]


class TutorialOverlay(QWidget):
    """Animated pinhole spotlight tutorial that guides the user around the UI."""
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self._step = 0
        self._total = len(TUTORIAL_STEPS)
        self._active = False

        # Spotlight state (animated)
        self._spot_x = 0.5
        self._spot_y = 0.5
        self._spot_radius = 180.0
        self._target_x = 0.5
        self._target_y = 0.5
        self._target_radius = 180.0
        self._alpha = 0.0
        self._fading_in = False

        # Animation timer — only runs when tutorial is active
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._animate)

    def start(self):
        self._step = 0
        self._alpha = 0.0
        self._fading_in = True
        self._active = True
        self._spot_x = 0.5
        self._spot_y = 0.5
        self._go_to_step(0)
        self._anim_timer.start(16)
        self.setFocus()
        self.show()
        self.raise_()

    def _go_to_step(self, idx):
        if idx >= self._total:
            self._dismiss()
            return
        self._step = idx
        step = TUTORIAL_STEPS[idx]
        self._target_x = step["offset"][0]
        self._target_y = step["offset"][1]
        self._target_radius = step["radius"]
        self.update()

    def _animate(self):
        changed = False
        # Fade in
        if self._fading_in and self._alpha < 1.0:
            self._alpha = min(1.0, self._alpha + 0.04)
            changed = True
            if self._alpha >= 1.0:
                self._fading_in = False

        # Ease spotlight towards target
        ease = 0.08
        dx = self._target_x - self._spot_x
        dy = self._target_y - self._spot_y
        dr = self._target_radius - self._spot_radius
        if abs(dx) > 0.001 or abs(dy) > 0.001 or abs(dr) > 0.5:
            self._spot_x += dx * ease
            self._spot_y += dy * ease
            self._spot_radius += dr * ease
            changed = True

        if changed:
            self.update()

    def paintEvent(self, event):
        if self._alpha <= 0 or not self._active:
            return
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return
        cx = max(0, min(w, int(self._spot_x * w)))
        cy = max(0, min(h, int(self._spot_y * h)))
        r = max(10, int(self._spot_radius))

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Dark overlay with radial gradient cutout (pinhole)
        overlay_alpha = int(180 * self._alpha)
        grad = QRadialGradient(cx, cy, r * 1.8)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.45, QColor(0, 0, 0, 0))
        grad.setColorAt(0.7, QColor(0, 0, 0, overlay_alpha // 2))
        grad.setColorAt(1.0, QColor(0, 0, 0, overlay_alpha))
        p.fillRect(0, 0, w, h, QBrush(grad))

        # Spotlight ring glow
        ring_pen = QPen(QColor(0, 120, 212, int(120 * self._alpha)), 2.5)
        p.setPen(ring_pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)

        # Pulsing outer ring
        pulse = 0.9 + 0.1 * (1.0 if int(self._spot_x * 1000) % 2 == 0 else 0.0)
        ring_pen2 = QPen(QColor(0, 120, 212, int(40 * self._alpha)), 1.0)
        p.setPen(ring_pen2)
        p.drawEllipse(QPointF(cx, cy), r * 1.1 * pulse, r * 1.1 * pulse)

        # Text card
        if self._step < self._total:
            step = TUTORIAL_STEPS[self._step]
            # Position card: prefer below the spotlight, but flip if near bottom
            card_w, card_h = 340, 130
            card_x = cx - card_w // 2
            card_y = cy + r + 30
            if card_y + card_h > h - 60:
                card_y = cy - r - card_h - 30
            card_x = max(12, min(w - card_w - 12, card_x))
            card_y = max(12, min(h - card_h - 12, card_y))

            # Card background
            card_alpha = int(230 * self._alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(30, 30, 36, card_alpha))
            p.drawRoundedRect(card_x, card_y, card_w, card_h, 10, 10)

            # Accent bar
            p.setBrush(QColor(0, 120, 212, card_alpha))
            p.drawRoundedRect(card_x, card_y, 4, card_h, 2, 2)

            # Title
            p.setPen(QColor(0, 180, 255, int(255 * self._alpha)))
            p.setFont(QFont(skins.get("font"), 14, QFont.Bold))
            p.drawText(QRectF(card_x + 16, card_y + 10, card_w - 32, 24),
                       Qt.AlignLeft, step["title"])

            # Body
            p.setPen(QColor(220, 220, 220, int(255 * self._alpha)))
            p.setFont(QFont(skins.get("font"), 10))
            p.drawText(QRectF(card_x + 16, card_y + 38, card_w - 32, 70),
                       Qt.AlignLeft | Qt.TextWordWrap, step["text"])

            # Step counter + next hint
            p.setPen(QColor(140, 140, 160, int(200 * self._alpha)))
            p.setFont(QFont(skins.get("font"), 9))
            counter = f"Step {self._step + 1} of {self._total}"
            hint = "Click anywhere to continue" if self._step < self._total - 1 else "Click to start playing!"
            p.drawText(QRectF(card_x + 16, card_y + card_h - 26, card_w - 32, 20),
                       Qt.AlignLeft, counter)
            p.drawText(QRectF(card_x + 16, card_y + card_h - 26, card_w - 32, 20),
                       Qt.AlignRight, hint)

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._go_to_step(self._step + 1)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Right):
            self._go_to_step(self._step + 1)
        elif event.key() == Qt.Key_Escape:
            self._dismiss()

    def _dismiss(self):
        self._active = False
        self._anim_timer.stop()
        self.hide()
        self.finished.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
