"""DiffLens - aplikasi pembanding dua gambar.

Versi aplikasi didefinisikan di sini sebagai SATU-SATUNYA sumber kebenaran
(single source of truth). Modul lain (config.py, main.py) mengimpornya
dari sini agar tidak terjadi perbedaan versi.
"""

from __future__ import annotations

__version__ = "1.0.0"
__app_name__ = "DiffLens"
__author__ = "DiffLens contributors"
__license__ = "MIT"

__all__ = ["__version__", "__app_name__", "__author__", "__license__"]
