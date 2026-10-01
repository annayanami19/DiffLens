"""DiffLens - entry point.

Jalankan aplikasi pembanding gambar.
Biasanya dipanggil oleh start.bat, tapi bisa juga:
    python run.py
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from app.main import run
    except ImportError as exc:  # dependency belum terpasang
        print("[ERROR] Gagal mengimpor aplikasi:", exc)
        print("Jalankan start.bat agar dependency terpasang otomatis,")
        print("atau install manual: pip install -r requirements.txt")
        return 1
    return run()


if __name__ == "__main__":
    sys.exit(main())
