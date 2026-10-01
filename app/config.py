"""Konfigurasi aplikasi DiffLens: konstanta, tema, dan penyimpanan pengaturan.

Pengaturan disimpan sebagai JSON di folder config milik user
(%APPDATA%\\DiffLens di Windows, ~/.config/DiffLens di Linux/mac).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __app_name__, __version__

APP_NAME = __app_name__
APP_TITLE = __app_name__
APP_VERSION = __version__

# Folder project (untuk menemukan aset ikon)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_ICO = ASSETS_DIR / "app_icon.ico"
ICON_PNG = ASSETS_DIR / "app_icon.png"

# Ekstensi gambar yang didukung (untuk filter dialog & drag-and-drop)
SUPPORTED_EXTS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff",
    ".ico", ".ppm", ".pgm", ".jp2", ".heic", ".heif",
}

FILE_DIALOG_FILTER = (
    "Gambar (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.ico *.ppm *.pgm *.jp2);;"
    "Semua file (*.*)"
)

# Mode perbandingan
MODE_SLIDER = "slider"
MODE_SIDE = "side"
MODE_BLINK = "blink"
MODE_OVERLAY = "overlay"
MODE_DIFF = "diff"

MODES = [MODE_SLIDER, MODE_SIDE, MODE_BLINK, MODE_OVERLAY, MODE_DIFF]

# Cara menyamakan ukuran kanvas
FIT_TO_A = "to_a"
FIT_TO_B = "to_b"
FIT_TO_LARGEST = "to_largest"

# Cara gambar disesuaikan ke kanvas
SCALE_CONTAIN = "contain"   # skala jaga rasio (tidak distorsi) - default
SCALE_STRETCH = "stretch"   # regangkan tepat memenuhi kanvas

DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "id",
    "mode": MODE_SLIDER,
    "fit_mode": FIT_TO_LARGEST,
    "scale_mode": SCALE_CONTAIN,
    "checkerboard": True,
    "theme": "dark",
    "diff_threshold": 8,      # 0-255, ambang piksel dianggap "berubah"
    "diff_gain": 4.0,         # pengali amplifikasi heatmap
    "blink_interval_ms": 500,
    "overlay_opacity": 50,    # 0-100
    "window_geometry": None,
    "window_state": None,
    "last_dir": "",
}


def config_dir() -> Path:
    """Kembalikan folder config khusus user (dibuat bila belum ada)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "settings.json"


class Settings:
    """Penyimpan pengaturan sederhana (dict + persist ke JSON)."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        path = settings_path()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                # hanya ambil key yang dikenal agar aman terhadap versi lama
                for key in DEFAULT_SETTINGS:
                    if key in raw:
                        self._data[key] = raw[key]
        except (OSError, ValueError):
            # pengaturan rusak -> pakai default, jangan crash
            self._data = dict(DEFAULT_SETTINGS)

    def save(self) -> None:
        try:
            settings_path().write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value


# QSS tema gelap
DARK_QSS = """
QMainWindow, QDialog { background-color: #1e1f22; }
QWidget { color: #e6e6e6; font-size: 12px; }
QToolBar { background-color: #26272b; border: 0; spacing: 4px; padding: 4px; }
QToolBar QToolButton {
    background: transparent; padding: 5px 9px; border-radius: 5px; color: #e6e6e6;
}
QToolBar QToolButton:hover { background: #3a3d42; }
QToolBar QToolButton:checked { background: #4c8bf5; color: #ffffff; }
QToolBar QToolButton:disabled { color: #6b6f76; }
QMenuBar { background: #26272b; }
QMenuBar::item:selected { background: #3a3d42; }
QMenu { background: #26272b; border: 1px solid #3a3d42; }
QMenu::item:selected { background: #4c8bf5; }
QStatusBar { background: #26272b; color: #b8bcc2; }
QDockWidget { titlebar-close-icon: none; titlebar-normal-icon: none; }
QDockWidget::title { background: #26272b; padding: 6px; }
QGroupBox {
    border: 1px solid #3a3d42; border-radius: 6px; margin-top: 14px; padding-top: 6px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #9aa0a6; }
QPushButton {
    background: #34363b; border: 1px solid #44474d; border-radius: 5px; padding: 6px 12px;
}
QPushButton:hover { background: #3f4248; }
QPushButton:pressed { background: #4c8bf5; }
QPushButton:disabled { color: #6b6f76; background: #2b2c30; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background: #2b2c30; border: 1px solid #44474d; border-radius: 5px; padding: 4px 6px;
}
QComboBox QAbstractItemView { background: #2b2c30; selection-background-color: #4c8bf5; }
QSlider::groove:horizontal { height: 4px; background: #44474d; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #4c8bf5; width: 14px; margin: -6px 0; border-radius: 7px;
}
QScrollArea { border: 0; }
QLabel#metricValue { color: #7fd1a0; font-weight: bold; }
QLabel#metricName { color: #9aa0a6; }
QTabBar::tab { background: #2b2c30; padding: 6px 12px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
QTabBar::tab:selected { background: #4c8bf5; }
"""

LIGHT_QSS = """
QMainWindow, QDialog { background-color: #f4f5f7; }
QWidget { color: #1e1f22; font-size: 12px; }
QToolBar { background-color: #e7e9ed; border: 0; spacing: 4px; padding: 4px; }
QToolBar QToolButton { background: transparent; padding: 5px 9px; border-radius: 5px; }
QToolBar QToolButton:hover { background: #d3d7de; }
QToolBar QToolButton:checked { background: #4c8bf5; color: #ffffff; }
QMenuBar { background: #e7e9ed; }
QMenu { background: #ffffff; border: 1px solid #c9cdd4; }
QMenu::item:selected { background: #4c8bf5; color: #ffffff; }
QStatusBar { background: #e7e9ed; color: #44474d; }
QGroupBox { border: 1px solid #c9cdd4; border-radius: 6px; margin-top: 14px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #5f6368; }
QPushButton { background: #ffffff; border: 1px solid #c9cdd4; border-radius: 5px; padding: 6px 12px; }
QPushButton:hover { background: #eef0f3; }
QPushButton:pressed { background: #4c8bf5; color: #ffffff; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background: #ffffff; border: 1px solid #c9cdd4; border-radius: 5px; padding: 4px 6px;
}
QSlider::groove:horizontal { height: 4px; background: #c9cdd4; border-radius: 2px; }
QSlider::handle:horizontal { background: #4c8bf5; width: 14px; margin: -6px 0; border-radius: 7px; }
QLabel#metricValue { color: #1a7f4b; font-weight: bold; }
QLabel#metricName { color: #5f6368; }
"""


def stylesheet(theme: str) -> str:
    return LIGHT_QSS if theme == "light" else DARK_QSS
