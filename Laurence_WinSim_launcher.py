"""Launcher for Laurence_WinSim.exe — handles both frozen (PyInstaller) and dev mode."""
import sys
import os

# For PyInstaller onefile: __file__ is in a temp dir, but sys._MEIPASS has the bundle root
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

if _base not in sys.path:
    sys.path.insert(0, _base)

from winsim.winsim_main import main
main()
