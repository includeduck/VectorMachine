"""Application identity: name, links, logo and icon.

The images in ``src/ui/assets`` are generated from ``assets/logo-master.png``
by ``tools/build_brand_assets.py``; edit the master and rerun that script
rather than editing them by hand.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from src.version import __version__

APP_NAME = "VectorMachine"
APP_VERSION = __version__
REPO_URL = "https://github.com/includeduck/VectorMachine"
ASSETS = Path(__file__).resolve().parent / "assets"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
# Windows groups taskbar buttons by this ID; without one, a script shows the
# python.exe icon in the taskbar instead of the app's own.
WINDOWS_APP_ID = "includeduck.VectorMachine"


def asset(name):
    return ASSETS / name


def app_icon():
    """The window/taskbar icon, with a hand-built image per size."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addFile(str(asset(f"icon-{size}.png")), QSize(size, size))
    return icon


def logo_tile_path():
    """The full logo on a rounded dark tile (readable on any background)."""
    return asset("logo-tile.png")


def set_windows_app_id():
    """Give the process its own taskbar identity (Windows only; no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass  # cosmetic: the app works without it
