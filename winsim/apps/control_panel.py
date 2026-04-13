"""WinSim — Virtual Control Panel (services + system info)."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QCheckBox, QFrame, QScrollArea)
from .. import skins


class VirtualControlPanel(QWidget):
    def __init__(self, kernel, parent=None):
        super().__init__(parent)
        self.kernel = kernel
        self._checks = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # System info card
        info_lbl = QLabel("System Information")
        info_lbl.setStyleSheet(f"color: {skins.get('text')}; font: bold 14px '{skins.get('font')}';")
        layout.addWidget(info_lbl)

        self._info = QLabel()
        self._info.setStyleSheet(f"""
            background: {skins.get('card')}; border: 1px solid {skins.get('border')};
            border-radius: 4px; padding: 10px; font: 11px '{skins.get('font_mono')}';
            color: {skins.get('text')};
        """)
        layout.addWidget(self._info)

        # Services section
        svc_lbl = QLabel("Services (toggle to enable/disable)")
        svc_lbl.setStyleSheet(f"color: {skins.get('text')}; font: bold 14px '{skins.get('font')}';")
        layout.addWidget(svc_lbl)

        svc_frame = QFrame()
        svc_frame.setStyleSheet(f"""
            background: {skins.get('card')}; border: 1px solid {skins.get('border')};
            border-radius: 4px;
        """)
        svc_layout = QVBoxLayout(svc_frame)
        svc_layout.setContentsMargins(12, 8, 12, 8)
        svc_layout.setSpacing(4)

        for name, enabled in self.kernel.services.items():
            row = QHBoxLayout()
            cb = QCheckBox(name)
            cb.setChecked(enabled)
            cb.setStyleSheet(f"font: 12px '{skins.get('font')}'; color: {skins.get('text')};")
            cb.toggled.connect(lambda checked, n=name: self._toggle_service(n, checked))
            row.addWidget(cb)

            desc = QLabel("Running" if enabled else "Stopped")
            desc.setStyleSheet(f"color: {skins.get('text2')}; font: 10px '{skins.get('font')}';")
            row.addStretch()
            row.addWidget(desc)
            self._checks[name] = (cb, desc)
            svc_layout.addLayout(row)

        layout.addWidget(svc_frame)

        # Event log
        log_lbl = QLabel("Event Log")
        log_lbl.setStyleSheet(f"color: {skins.get('text')}; font: bold 14px '{skins.get('font')}';")
        layout.addWidget(log_lbl)

        self._log = QLabel()
        self._log.setWordWrap(True)
        self._log.setAlignment(Qt.AlignTop)
        self._log.setStyleSheet(f"""
            background: {skins.get('card')}; border: 1px solid {skins.get('border')};
            border-radius: 4px; padding: 8px; font: 10px '{skins.get('font_mono')}';
            color: {skins.get('text')};
        """)
        self._log.setMinimumHeight(120)
        layout.addWidget(self._log)

        layout.addStretch()

    def _toggle_service(self, name, enabled):
        self.kernel.services[name] = enabled
        cb, desc = self._checks[name]
        desc.setText("Running" if enabled else "Stopped")
        self.kernel.log(f"Service '{name}' {'started' if enabled else 'stopped'}")

    def refresh(self):
        s = self.kernel.get_summary()
        self._info.setText(
            f"CPU Cores: {self.kernel.cpu_cores}\n"
            f"Total CPU: {s['cpu_pct']:.1f}%\n"
            f"RAM: {s['mem_used']:.0f} MB / {s['mem_total']} MB ({s['mem_pct']:.0f}%)\n"
            f"Disk: {s['disk_pct']:.1f}% used ({s['disk_free']:.1f} GB free)\n"
            f"Processes: {s['n_procs']}\n"
            f"Game Time: {s['game_time']:.0f}s"
        )
        self._log.setText("\n".join(self.kernel.event_log[-15:]))

        for name, enabled in self.kernel.services.items():
            if name in self._checks:
                cb, desc = self._checks[name]
                cb.setChecked(enabled)
                desc.setText("Running" if enabled else "Stopped")
