"""WinSim — Virtual Notepad (simple text editor, costs RAM)."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QLabel
from .. import skins


class VirtualNotepad(QWidget):
    def __init__(self, kernel, parent=None):
        super().__init__(parent)
        self.kernel = kernel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Type here... (this app uses RAM while open)")
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background: {skins.get('card')}; color: {skins.get('text')};
                border: none; font: 12px '{skins.get('font_mono')}'; padding: 8px;
            }}
        """)
        layout.addWidget(self._editor)

        status = QLabel("  Notepad — editing uses memory")
        status.setFixedHeight(22)
        status.setStyleSheet(f"""
            background: {skins.get('bg')}; color: {skins.get('text2')};
            font: 9px '{skins.get('font')}'; border-top: 1px solid {skins.get('border')};
        """)
        layout.addWidget(status)
