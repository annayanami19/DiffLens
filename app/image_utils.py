"""Utilitas gambar: memuat file, menyamakan ukuran, konversi PIL <-> QImage,
dan pembuatan latar checkerboard.

Semua fungsi di sini bebas dari Qt kecuali yang menyebut QImage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

try:
    from PySide6.QtGui import QImage
except ImportError:  # pragma: no cover - Qt wajib ada saat runtime
    QImage = None  # type: ignore


@dataclass
class LoadedImage:
    """Satu gambar yang sudah dimuat beserta metadata asalnya."""

    path: str
    original: Image.Image          # gambar asli (mode asli, mungkin ada alpha)
    rgb: Image.Image               # versi RGBA/RGB siap dibandingkan
    width: int
    height: int
    mode: str                      # mode asli (mis. "RGB", "RGBA", "L")
    file_size: int                 # byte

    @property
    def name(self) -> str:
        return Path(self.path).name


def load_image(path: str) -> LoadedImage:
    """Muat gambar dari path. Melempar exception bila gagal."""
    p = Path(path)
    img = Image.open(p)
    img.load()  # paksa baca data sekarang agar file bisa ditutup
    original = img.copy()
    mode = original.mode

    # Normalisasi orientasi EXIF (foto dari kamera/HP)
    original = ImageOps.exif_transpose(original)

    # Untuk perbandingan kita pakai RGBA agar transparansi tetap utuh.
    if original.mode == "P":
        rgb = original.convert("RGBA")
    elif original.mode in ("RGB", "RGBA", "L", "LA"):
        rgb = original.convert("RGBA") if original.mode != "RGBA" else original.copy()
    else:
        rgb = original.convert("RGBA")

    size = p.stat().st_size if p.exists() else 0
    return LoadedImage(
        path=str(p),
        original=original,
        rgb=rgb,
        width=original.width,
        height=original.height,
        mode=mode,
        file_size=size,
    )


def _on_checkerboard(img: Image.Image, tile: int = 16) -> Image.Image:
    """Tempelkan gambar RGBA di atas pola checkerboard (untuk area transparan)."""
    if img.mode != "RGBA":
        return img.convert("RGBA")
    w, h = img.size
    # pola papan catur abu-abu
    yy, xx = np.mgrid[0:h, 0:w]
    checker = ((xx // tile + yy // tile) % 2).astype(np.uint8)
    bg = np.empty((h, w, 3), dtype=np.uint8)
    bg[checker == 0] = 200
    bg[checker == 1] = 150
    bg_img = Image.fromarray(bg, mode="RGB").convert("RGBA")
    return Image.alpha_composite(bg_img, img)


def to_display_image(img: Image.Image, checkerboard: bool = False) -> Image.Image:
    """Siapkan gambar RGBA untuk ditampilkan (opsional dengan checkerboard)."""
    rgba = img if img.mode == "RGBA" else img.convert("RGBA")
    if checkerboard:
        return _on_checkerboard(rgba)
    return rgba


def pil_to_qimage(img: Image.Image) -> "QImage":
    """Konversi PIL.Image (RGB/RGBA) ke QImage dengan salinan data yang aman."""
    if QImage is None:  # pragma: no cover
        raise RuntimeError("PySide6 tidak tersedia")

    if img.mode == "RGBA":
        arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
        h, w, _ = arr.shape
        # simpan referensi bytes selama QImage dibuat & disalin
        buf = arr.tobytes()
        qimg = QImage(buf, w, h, 4 * w, QImage.Format.Format_RGBA8888)
        return qimg.copy()
    else:
        rgb = img.convert("RGB")
        arr = np.ascontiguousarray(np.asarray(rgb, dtype=np.uint8))
        h, w, _ = arr.shape
        buf = arr.tobytes()
        qimg = QImage(buf, w, h, 3 * w, QImage.Format.Format_RGB888)
        return qimg.copy()


def image_to_array(img: Image.Image) -> np.ndarray:
    """PIL.Image -> numpy array uint8 (H, W, 3) RGB."""
    rgb = img.convert("RGB")
    return np.asarray(rgb, dtype=np.uint8)


def match_size(
    a: LoadedImage,
    b: LoadedImage,
    fit_mode: str,
    scale_mode: str = "contain",
    bg: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> tuple[Image.Image, Image.Image]:
    """Kembalikan pasangan gambar RGBA dengan ukuran kanvas yang sama.

    fit_mode:
        "to_a"       -> kanvas = ukuran A
        "to_b"       -> kanvas = ukuran B
        "to_largest" -> kanvas = max(lebar), max(tinggi)

    scale_mode:
        "contain" (default) -> gambar yang lebih kecil DISKALAKAN membesar
                    (jaga rasio) agar sebanding dengan yang lain, lalu
                    diletakkan di tengah. Tidak ada distorsi.
        "stretch"   -> gambar diregangkan tepat memenuhi kanvas (bisa distorsi).

    Contoh kasus nyata: A 1920x1080, B 640x360. Dengan "contain" + "to_a",
    B akan diperbesar ke 1920x1080 (rasio sama) sehingga presisi pikselnya
    tetap sebanding dengan A — bukan ditempel mungil di tengah.
    """
    if fit_mode == "to_a":
        target = (a.width, a.height)
    elif fit_mode == "to_b":
        target = (b.width, b.height)
    else:
        target = (max(a.width, b.width), max(a.height, b.height))

    if scale_mode == "stretch":
        return (_resize_to(a.rgb, target), _resize_to(b.rgb, target))
    return (_contain(a.rgb, target, bg), _contain(b.rgb, target, bg))


def _resize_to(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Regangkan tepat ke target (bisa mengubah rasio)."""
    rgba = img.convert("RGBA")
    if rgba.size == target:
        return rgba
    return rgba.resize(target, Image.Resampling.LANCZOS)


def _contain(img: Image.Image, target: tuple[int, int], bg) -> Image.Image:
    """Skalakan gambar jaga-rasio agar muat di target, lalu center."""
    rgba = img.convert("RGBA")
    tw, th = target
    if rgba.size == target:
        return rgba
    ratio = min(tw / rgba.width, th / rgba.height)
    new_w = max(1, int(round(rgba.width * ratio)))
    new_h = max(1, int(round(rgba.height * ratio)))
    resample = (Image.Resampling.LANCZOS if ratio <= 1.0
                else Image.Resampling.BICUBIC)
    scaled = rgba.resize((new_w, new_h), resample)
    if (new_w, new_h) == target:
        return scaled
    canvas = Image.new("RGBA", target, bg)
    canvas.paste(scaled, ((tw - new_w) // 2, (th - new_h) // 2), scaled)
    return canvas


def _letterbox(img: Image.Image, target: tuple[int, int], bg) -> Image.Image:
    """Letakkan gambar apa adanya (tanpa skala) di tengah kanvas target."""
    tw, th = target
    if img.size == target:
        return img.convert("RGBA")
    canvas = Image.new("RGBA", target, bg)
    x = (tw - img.width) // 2
    y = (th - img.height) // 2
    canvas.paste(img.convert("RGBA"), (x, y))
    return canvas


def make_checkerboard_image(size: tuple[int, int], tile: int = 16) -> Image.Image:
    """Buat gambar pola checkerboard (dipakai untuk komposit ekspor)."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    checker = ((xx // tile + yy // tile) % 2).astype(np.uint8)
    bg = np.empty((h, w, 3), dtype=np.uint8)
    bg[checker == 0] = 200
    bg[checker == 1] = 150
    return Image.fromarray(bg, mode="RGB")


def human_size(num_bytes: int) -> str:
    """Format ukuran byte menjadi teks ramah (KB/MB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"
