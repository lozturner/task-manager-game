"""WinSim — Game engine: missions, scoring, events."""
import json
import random
import time
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal
from .os_kernel import VirtualKernel, LAUNCHABLE_APPS
from .missions import MISSIONS

import sys as _sys

def _get_save_path():
    """Resolve save path — avoid temp dirs in frozen PyInstaller builds."""
    if getattr(_sys, 'frozen', False):
        return Path(_sys.executable).parent / "winsim_config.json"
    return Path(__file__).parent / "winsim_config.json"

SAVE_PATH = _get_save_path()


class ActiveMission:
    def __init__(self, definition, start_time):
        self.defn = definition
        self.start_time = start_time
        self.completed = False
        self.failed = False
        self.spawned_pid = None       # PID of spawned process for this mission
        self.initial_ram = 0.0        # snapshot for free_ram missions
        self.initial_disk = 0.0       # snapshot for free_disk missions
        self.initial_services = 0     # snapshot for disable_services missions


class GameEngine(QObject):
    mission_started = pyqtSignal(dict)    # mission defn
    mission_completed = pyqtSignal(dict, int)  # defn, xp earned
    mission_failed = pyqtSignal(dict)
    xp_changed = pyqtSignal(int)
    level_up = pyqtSignal(int)
    toast = pyqtSignal(str, str)          # title, message

    def __init__(self):
        super().__init__()
        self.kernel = VirtualKernel()
        self.xp = 0
        self.level = 1
        self.score = 0
        self.high_score = 0
        self.active_missions = []
        self.completed_ids = set()
        self._mission_cooldown = 0.0
        self._last_mission_time = 0.0
        self._load()
        self.kernel.boot_sequence()

    # ── Save / Load ──────────────────────────────────────────────────────
    def _load(self):
        if not SAVE_PATH.exists():
            return
        try:
            d = json.loads(SAVE_PATH.read_text())
            self.xp = d.get("xp", 0)
            self.level = d.get("level", 1)
            self.high_score = d.get("high_score", 0)
            self.completed_ids = set(d.get("completed_missions", []))
        except (json.JSONDecodeError, OSError):
            # Corrupted or unreadable save — start fresh
            pass

    def save(self):
        d = {
            "xp": self.xp,
            "level": self.level,
            "high_score": self.high_score,
            "completed_missions": list(self.completed_ids),
        }
        SAVE_PATH.write_text(json.dumps(d, indent=2))

    # ── Tick ─────────────────────────────────────────────────────────────
    def tick(self, dt):
        self.kernel.tick(dt)
        self._check_missions()
        self._maybe_spawn_mission()
        self._maybe_random_event()

    # ── Missions ─────────────────────────────────────────────────────────
    def _maybe_spawn_mission(self):
        if len(self.active_missions) >= 2:
            return
        if self.kernel.game_time - self._last_mission_time < 20:
            return
        if random.random() > 0.03:  # ~3% chance per tick (~500ms)
            return

        # Pick a random mission
        available = [m for m in MISSIONS if m["id"] not in
                     {am.defn["id"] for am in self.active_missions}]
        if not available:
            return

        defn = random.choice(available)
        am = ActiveMission(defn, self.kernel.game_time)

        # Spawn required process if mission needs one
        if "spawn" in defn:
            sp = defn["spawn"]
            p = self.kernel.spawn(sp["name"], **sp)
            am.spawned_pid = p.pid
        elif defn["type"] == "kill_malware":
            p = self.kernel.inject_malware()
            am.spawned_pid = p.pid

        # Snapshots for delta-based missions
        am.initial_ram = self.kernel.memory.get_used(self.kernel.processes)
        am.initial_disk = self.kernel.disk.get_used_gb() * 1024  # in MB
        am.initial_services = sum(1 for v in self.kernel.services.values() if v)

        self.active_missions.append(am)
        self._last_mission_time = self.kernel.game_time
        self.mission_started.emit(defn)
        self.toast.emit(f"Mission: {defn['title']}", defn['desc'])

    def _check_missions(self):
        procs = dict(self.kernel.processes)  # snapshot
        for am in list(self.active_missions):
            if am.completed or am.failed:
                continue
            defn = am.defn
            elapsed = self.kernel.game_time - am.start_time

            # Time limit check
            if "time_limit" in defn and elapsed > defn["time_limit"]:
                am.failed = True
                self.active_missions.remove(am)
                self.mission_failed.emit(defn)
                self.toast.emit("Mission Failed", f"{defn['title']} — timed out!")
                self.score = max(0, self.score - 5)
                continue

            completed = False

            if defn["type"] == "launch":
                target = defn.get("target_app", "").lower()
                for p in procs.values():
                    if target in p.description.lower() and p.start_time > am.start_time:
                        completed = True
                        break

            elif defn["type"] == "kill_high_cpu":
                if am.spawned_pid and am.spawned_pid not in procs:
                    completed = True

            elif defn["type"] == "kill_malware":
                if am.spawned_pid and am.spawned_pid not in procs:
                    completed = True

            elif defn["type"] == "free_ram":
                current = self.kernel.memory.get_used(procs)
                freed = am.initial_ram - current
                if freed >= defn.get("target_mb", 200):
                    completed = True

            elif defn["type"] == "free_disk":
                current = self.kernel.disk.get_used_gb() * 1024
                freed = am.initial_disk - current
                if freed >= defn.get("target_mb", 300):
                    completed = True

            elif defn["type"] == "disable_services":
                current = sum(1 for v in self.kernel.services.values() if v)
                disabled = am.initial_services - current
                if disabled >= defn.get("target_count", 2):
                    completed = True

            elif defn["type"] == "set_priority":
                if am.spawned_pid:
                    p = procs.get(am.spawned_pid)
                    if p and p.priority >= defn.get("target_priority", 13):
                        completed = True

            if completed:
                am.completed = True
                self.active_missions.remove(am)
                self.completed_ids.add(defn["id"])
                xp = defn.get("xp", 10)
                # Time bonus
                if elapsed < defn.get("time_limit", 999) * 0.5:
                    xp = int(xp * 1.5)
                self.xp += xp
                self.score += xp
                self.high_score = max(self.high_score, self.score)
                self.mission_completed.emit(defn, xp)
                self.toast.emit("Mission Complete!", f"{defn['title']} — +{xp} XP")
                self._check_level_up()
                self.xp_changed.emit(self.xp)
                self.save()

    def _check_level_up(self):
        thresholds = [0, 50, 120, 220, 350, 500, 700, 950, 1250, 1600, 2000]
        new_level = 1
        for i, t in enumerate(thresholds):
            if self.xp >= t:
                new_level = i + 1
        if new_level > self.level:
            self.level = new_level
            self.level_up.emit(self.level)
            self.toast.emit("Level Up!", f"You are now level {self.level}!")
            # Level perks
            if self.level >= 3:
                self.kernel.cpu_cores = max(self.kernel.cpu_cores, 4)
                self.kernel.total_cpu = 100.0 * self.kernel.cpu_cores
            if self.level >= 5:
                self.kernel.memory.total_mb = max(self.kernel.memory.total_mb, 8192)

    def _maybe_random_event(self):
        if random.random() > 0.005:  # ~0.5% per tick
            return
        events = ["memory_leak", "update_hog", "malware"]
        event = random.choice(events)
        if event == "memory_leak":
            # Pick a random non-system process and inflate its RAM
            candidates = [p for p in self.kernel.processes.values()
                         if not p.is_system and not p.is_malware]
            if candidates:
                p = random.choice(candidates)
                p.ram_base *= 1.8
                p.ram_mb = p.ram_base
                self.kernel.log(f"Memory leak in {p.name} (PID {p.pid})")
        elif event == "update_hog":
            # Windows Update process goes heavy
            for p in self.kernel.processes.values():
                if "Update" in p.description:
                    p.cpu_base = min(40.0, p.cpu_base * 3)
                    self.kernel.log("Windows Update consuming resources")
                    break
        elif event == "malware":
            self.kernel.inject_malware()

    # ── App launching ────────────────────────────────────────────────────
    def launch_app(self, name):
        return self.kernel.launch_app(name)
