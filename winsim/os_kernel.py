"""WinSim — Virtual OS Kernel. Pure Python, no Qt dependency."""
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class VirtualProcess:
    pid: int
    name: str
    ppid: int = 0
    status: str = "running"       # running, waiting, suspended, zombie
    priority: int = 8             # 0-31
    cpu_base: float = 0.5         # baseline CPU %
    cpu_usage: float = 0.5        # current CPU %
    ram_mb: float = 20.0          # current RAM
    ram_base: float = 20.0        # baseline RAM
    disk_io: float = 0.0          # MB/s
    start_time: float = 0.0
    is_system: bool = False
    is_malware: bool = False
    is_startup: bool = True       # runs on boot
    icon: str = "AP"              # 2-char icon code
    colour: str = "#0078d4"
    description: str = ""

    def tick(self, dt: float):
        if self.status != "running":
            return
        # Fluctuate CPU around baseline
        self.cpu_usage = max(0.0, min(100.0,
            self.cpu_base + random.gauss(0, self.cpu_base * 0.15)))
        # Malware grows
        if self.is_malware:
            self.cpu_base = min(95.0, self.cpu_base + 0.3 * dt)
            self.ram_mb = min(2048, self.ram_mb + 1.5 * dt)
        # Small RAM drift
        self.ram_mb = max(1.0, self.ram_base + random.gauss(0, self.ram_base * 0.03))
        if self.is_malware:
            self.ram_mb = max(self.ram_mb, self.ram_base)
            self.ram_base += 0.8 * dt


@dataclass
class VirtualMemory:
    total_mb: int = 4096
    page_file_mb: int = 4096
    page_file_used: float = 0.0

    def get_used(self, processes: Dict[int, VirtualProcess]) -> float:
        return sum(p.ram_mb for p in processes.values() if p.status == "running")

    def get_percent(self, processes: Dict[int, VirtualProcess]) -> float:
        used = self.get_used(processes)
        return min(100.0, (used / self.total_mb) * 100)

    def get_pressure(self, processes: Dict[int, VirtualProcess]) -> float:
        """0.0 = fine, 1.0 = critical."""
        pct = self.get_percent(processes)
        if pct < 70: return 0.0
        if pct < 85: return (pct - 70) / 15 * 0.5
        return 0.5 + (pct - 85) / 15 * 0.5


@dataclass
class VirtualFile:
    path: str
    size_mb: float
    file_type: str = "file"     # file, folder, temp, system
    created: float = 0.0
    modified: float = 0.0


@dataclass
class VirtualDisk:
    total_gb: float = 128.0
    files: Dict[str, VirtualFile] = field(default_factory=dict)

    def get_used_gb(self) -> float:
        return sum(f.size_mb for f in self.files.values()) / 1024

    def get_free_gb(self) -> float:
        return self.total_gb - self.get_used_gb()

    def get_percent(self) -> float:
        return (self.get_used_gb() / self.total_gb) * 100

    def add_file(self, path: str, size_mb: float, file_type: str = "file", t: float = 0.0):
        self.files[path] = VirtualFile(path, size_mb, file_type, t, t)

    def delete_file(self, path: str) -> float:
        if path in self.files:
            size = self.files[path].size_mb
            del self.files[path]
            return size
        return 0.0

    def list_dir(self, prefix: str) -> List[VirtualFile]:
        return [f for p, f in self.files.items() if p.startswith(prefix)]


# ── Boot process definitions ─────────────────────────────────────────────────
BOOT_PROCESSES = [
    {"name": "System",         "cpu_base": 0.2, "ram_base": 4,    "is_system": True,  "icon": "SY", "colour": "#666666", "description": "Windows NT Kernel"},
    {"name": "smss.exe",       "cpu_base": 0.1, "ram_base": 1,    "is_system": True,  "icon": "SM", "colour": "#888888", "description": "Session Manager"},
    {"name": "csrss.exe",      "cpu_base": 0.3, "ram_base": 5,    "is_system": True,  "icon": "CS", "colour": "#888888", "description": "Client/Server Runtime"},
    {"name": "wininit.exe",    "cpu_base": 0.1, "ram_base": 2,    "is_system": True,  "icon": "WI", "colour": "#888888", "description": "Windows Init"},
    {"name": "services.exe",   "cpu_base": 0.4, "ram_base": 8,    "is_system": True,  "icon": "SV", "colour": "#5c6bc0", "description": "Service Control Manager"},
    {"name": "lsass.exe",      "cpu_base": 0.2, "ram_base": 12,   "is_system": True,  "icon": "LS", "colour": "#ef5350", "description": "Local Security Authority"},
    {"name": "svchost.exe",    "cpu_base": 1.5, "ram_base": 45,   "is_system": True,  "icon": "SH", "colour": "#5c6bc0", "description": "Service Host (Network)"},
    {"name": "svchost.exe",    "cpu_base": 0.8, "ram_base": 30,   "is_system": True,  "icon": "SH", "colour": "#5c6bc0", "description": "Service Host (Local)"},
    {"name": "svchost.exe",    "cpu_base": 2.0, "ram_base": 60,   "is_system": True,  "icon": "SH", "colour": "#5c6bc0", "description": "Service Host (System)"},
    {"name": "svchost.exe",    "cpu_base": 0.5, "ram_base": 25,   "is_system": True,  "icon": "SH", "colour": "#5c6bc0", "description": "Service Host (DcomLaunch)"},
    {"name": "svchost.exe",    "cpu_base": 3.0, "ram_base": 80,   "is_system": False, "icon": "SH", "colour": "#5c6bc0", "description": "Service Host (Windows Update)"},
    {"name": "dwm.exe",        "cpu_base": 1.0, "ram_base": 50,   "is_system": True,  "icon": "DW", "colour": "#42a5f5", "description": "Desktop Window Manager"},
    {"name": "explorer.exe",   "cpu_base": 1.5, "ram_base": 80,   "is_system": True,  "icon": "EX", "colour": "#ffc107", "description": "Windows Explorer Shell"},
    {"name": "SearchUI.exe",   "cpu_base": 0.8, "ram_base": 65,   "is_system": False, "icon": "SR", "colour": "#29b6f6", "description": "Windows Search"},
    {"name": "RuntimeBroker.exe", "cpu_base": 0.3, "ram_base": 15, "is_system": False, "icon": "RB", "colour": "#78909c", "description": "Runtime Broker"},
    {"name": "taskhostw.exe",  "cpu_base": 0.2, "ram_base": 10,   "is_system": False, "icon": "TH", "colour": "#78909c", "description": "Task Host Window"},
    {"name": "sihost.exe",     "cpu_base": 0.3, "ram_base": 12,   "is_system": False, "icon": "SI", "colour": "#78909c", "description": "Shell Infrastructure Host"},
    {"name": "ctfmon.exe",     "cpu_base": 0.1, "ram_base": 6,    "is_system": False, "icon": "CT", "colour": "#78909c", "description": "CTF Loader"},
]

# Apps the player can launch
LAUNCHABLE_APPS = {
    "Task Manager":    {"cpu_base": 1.0, "ram_base": 35,  "icon": "TM", "colour": "#0078d4", "description": "Task Manager"},
    "Notepad":         {"cpu_base": 0.2, "ram_base": 12,  "icon": "NP", "colour": "#ffd54f", "description": "Notepad"},
    "File Explorer":   {"cpu_base": 0.8, "ram_base": 45,  "icon": "FE", "colour": "#ffc107", "description": "File Explorer"},
    "Control Panel":   {"cpu_base": 0.3, "ram_base": 20,  "icon": "CP", "colour": "#5c6bc0", "description": "Control Panel"},
    "Chrome":          {"cpu_base": 8.0, "ram_base": 350, "icon": "CR", "colour": "#4caf50", "description": "Google Chrome"},
    "Edge":            {"cpu_base": 5.0, "ram_base": 250, "icon": "ED", "colour": "#0078d4", "description": "Microsoft Edge"},
    "Spotify":         {"cpu_base": 2.0, "ram_base": 150, "icon": "SP", "colour": "#1db954", "description": "Spotify"},
    "Discord":         {"cpu_base": 3.0, "ram_base": 200, "icon": "DC", "colour": "#5865f2", "description": "Discord"},
    "VS Code":         {"cpu_base": 4.0, "ram_base": 280, "icon": "VS", "colour": "#007acc", "description": "Visual Studio Code"},
}

# Default filesystem
DEFAULT_FILES = {
    "C:/Windows/System32/ntoskrnl.exe":    (15.0, "system"),
    "C:/Windows/System32/kernel32.dll":    (1.2,  "system"),
    "C:/Windows/System32/user32.dll":      (1.8,  "system"),
    "C:/Windows/explorer.exe":             (4.5,  "system"),
    "C:/Program Files/Chrome/chrome.exe":  (2.1,  "file"),
    "C:/Program Files/Notepad/notepad.exe":(0.3,  "file"),
    "C:/Users/Player/Documents/notes.txt": (0.01, "file"),
    "C:/Users/Player/Documents/report.docx":(0.5, "file"),
    "C:/Users/Player/Desktop/shortcut.lnk":(0.001,"file"),
    "C:/Users/Player/Downloads/setup.exe": (45.0, "file"),
    "C:/Users/Player/Downloads/movie.zip": (700.0,"file"),
    "C:/Temp/cache_001.tmp":               (120.0,"temp"),
    "C:/Temp/cache_002.tmp":               (85.0, "temp"),
    "C:/Temp/cache_003.tmp":               (200.0,"temp"),
    "C:/Temp/update_log.tmp":              (50.0, "temp"),
    "C:/Temp/crash_dump.tmp":              (300.0,"temp"),
    "C:/Windows/Temp/setup_log.tmp":       (15.0, "temp"),
    "C:/Windows/Installer/patch_old.msp":  (400.0,"temp"),
}


class VirtualKernel:
    def __init__(self):
        self.processes: Dict[int, VirtualProcess] = {}
        self.memory = VirtualMemory()
        self.disk = VirtualDisk()
        self.next_pid = 4
        self.game_time = 0.0
        self.cpu_cores = 2
        self.total_cpu = 100.0 * self.cpu_cores
        self.services = {
            "Windows Update": True,
            "Windows Search": True,
            "Print Spooler": True,
            "Bluetooth": False,
            "Remote Desktop": False,
            "Telemetry": True,
        }
        self.event_log: List[str] = []
        self.cpu_history: List[float] = []
        self.mem_history: List[float] = []

    def boot_sequence(self):
        """Spawn all initial system processes and populate disk."""
        self.game_time = 0.0
        self.processes.clear()
        self.event_log.clear()

        # Spawn boot processes
        for pdef in BOOT_PROCESSES:
            self.spawn(pdef["name"], is_boot=True, **{k: v for k, v in pdef.items() if k != "name"})

        # Populate filesystem
        for path, (size, ftype) in DEFAULT_FILES.items():
            self.disk.add_file(path, size, ftype)

        self.log("System booted successfully.")

    def spawn(self, name: str, is_boot=False, **kwargs) -> VirtualProcess:
        pid = self.next_pid
        self.next_pid += 1
        p = VirtualProcess(
            pid=pid, name=name,
            cpu_base=kwargs.get("cpu_base", 1.0),
            cpu_usage=kwargs.get("cpu_base", 1.0),
            ram_mb=kwargs.get("ram_base", 20.0),
            ram_base=kwargs.get("ram_base", 20.0),
            is_system=kwargs.get("is_system", False),
            is_malware=kwargs.get("is_malware", False),
            is_startup=is_boot,
            icon=kwargs.get("icon", "AP"),
            colour=kwargs.get("colour", "#0078d4"),
            description=kwargs.get("description", name),
            start_time=self.game_time,
        )
        self.processes[pid] = p
        if not is_boot:
            self.log(f"Started: {name} (PID {pid})")
        return p

    def kill(self, pid: int) -> bool:
        p = self.processes.get(pid)
        if not p:
            return False
        if p.is_system:
            self.log(f"WARNING: Cannot kill system process {p.name} (PID {pid})")
            return False
        del self.processes[pid]
        self.log(f"Killed: {p.name} (PID {pid}), freed {p.ram_mb:.0f} MB")
        return True

    def suspend(self, pid: int):
        p = self.processes.get(pid)
        if p and not p.is_system:
            p.status = "suspended"
            self.log(f"Suspended: {p.name} (PID {pid})")

    def resume(self, pid: int):
        p = self.processes.get(pid)
        if p and p.status == "suspended":
            p.status = "running"
            self.log(f"Resumed: {p.name} (PID {pid})")

    def set_priority(self, pid: int, priority: int):
        p = self.processes.get(pid)
        if p:
            old = p.priority
            p.priority = max(0, min(31, priority))
            self.log(f"Priority: {p.name} {old} -> {p.priority}")

    def tick(self, dt: float):
        """Advance the simulation."""
        self.game_time += dt
        procs = list(self.processes.values())
        for p in procs:
            p.tick(dt)

        # Clamp total CPU
        running = [p for p in procs if p.status == "running" and p.pid in self.processes]
        total_cpu = sum(p.cpu_usage for p in running)
        if total_cpu > self.total_cpu and total_cpu > 0:
            scale = self.total_cpu / total_cpu
            for p in running:
                p.cpu_usage *= scale

        # Memory pressure → page file
        mem_pct = self.memory.get_percent(self.processes)
        if mem_pct > 90:
            overflow = self.memory.get_used(self.processes) - self.memory.total_mb * 0.9
            self.memory.page_file_used = min(self.memory.page_file_mb, overflow)

        # Track history
        cpu_pct = self.get_cpu_percent()
        self.cpu_history.append(cpu_pct)
        self.mem_history.append(mem_pct)
        self.cpu_history = self.cpu_history[-60:]
        self.mem_history = self.mem_history[-60:]

    def get_cpu_percent(self) -> float:
        if self.cpu_cores <= 0:
            return 0.0
        total = sum(p.cpu_usage for p in self.processes.values() if p.status == "running")
        return min(100.0, total / self.cpu_cores)

    def get_summary(self) -> dict:
        return {
            "cpu_pct": self.get_cpu_percent(),
            "mem_pct": self.memory.get_percent(self.processes),
            "mem_used": self.memory.get_used(self.processes),
            "mem_total": self.memory.total_mb,
            "disk_pct": self.disk.get_percent(),
            "disk_free": self.disk.get_free_gb(),
            "n_procs": len(self.processes),
            "game_time": self.game_time,
            "cpu_history": list(self.cpu_history),
            "mem_history": list(self.mem_history),
        }

    def log(self, msg: str):
        ts = f"[{self.game_time:.0f}s]"
        self.event_log.append(f"{ts} {msg}")
        self.event_log = self.event_log[-100:]

    def launch_app(self, app_name: str) -> Optional[VirtualProcess]:
        if app_name in LAUNCHABLE_APPS:
            return self.spawn(app_name.lower().replace(" ", "_") + ".exe",
                              **LAUNCHABLE_APPS[app_name])
        return None

    def inject_malware(self, name: str = "svchost.exe"):
        """Spawn a disguised malware process."""
        p = self.spawn(name, cpu_base=2.0, ram_base=40, is_malware=True,
                       icon="!!", colour="#f44336", description="Suspicious Process")
        self.log(f"ALERT: Suspicious activity detected (PID {p.pid})")
        return p
