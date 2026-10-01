"""Perhitungan perbedaan gambar dan metrik kualitas.

Modul ini murni NumPy/Pillow. SSIM memakai scikit-image bila tersedia,
jika tidak ada akan memakai implementasi cadangan berbasis NumPy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# Coba impor scikit-image untuk SSIM/PSNR berkualitas tinggi.
try:
    from skimage.metrics import structural_similarity as _sk_ssim

    _HAVE_SKIMAGE = True
except Exception:  # pragma: no cover - fallback bila belum terpasang
    _HAVE_SKIMAGE = False


@dataclass
class DiffResult:
    """Hasil analisis perbedaan dua gambar (ukuran sama)."""

    total_pixels: int = 0
    changed_pixels: int = 0
    changed_percent: float = 0.0
    mse: float = 0.0
    rmse: float = 0.0
    psnr: float = 0.0
    ssim: float = 0.0
    similarity_percent: float = 0.0
    mean_diff: float = 0.0
    max_diff: int = 0
    per_channel_mean: list[float] = field(default_factory=list)
    histogram: np.ndarray | None = None          # (256,) jumlah piksel per nilai selisih
    magnitude: np.ndarray | None = None          # (H, W) uint8, selisih maksimum antar channel
    ssim_source: str = "numpy"                   # "scikit-image" atau "numpy"


def _to_rgb_arrays(a: Image.Image, b: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    if a.size != b.size:
        raise ValueError("Ukuran gambar harus sama sebelum dihitung perbedaannya.")
    aa = np.asarray(a.convert("RGB"), dtype=np.int16)
    bb = np.asarray(b.convert("RGB"), dtype=np.int16)
    return aa, bb


def _fallback_ssim(gray_a: np.ndarray, gray_b: np.ndarray, data_range: float = 255.0) -> float:
    """SSIM sederhana (window seragam) bila scikit-image tidak tersedia."""
    win = 7
    if gray_a.shape[0] < win or gray_a.shape[1] < win:
        # gambar terlalu kecil -> pakai korelasi global sederhana
        x = gray_a.astype(np.float64).ravel()
        y = gray_b.astype(np.float64).ravel()
        mx, my = x.mean(), y.mean()
        vx, vy = x.var(), y.var()
        cxy = ((x - mx) * (y - my)).mean()
        c1 = (0.01 * data_range) ** 2
        c2 = (0.03 * data_range) ** 2
        return float(((2 * mx * my + c1) * (2 * cxy + c2)) /
                     ((mx ** 2 + my ** 2 + c1) * (vx + vy + c2)))

    a = gray_a.astype(np.float64)
    b = gray_b.astype(np.float64)
    from numpy.lib.stride_tricks import sliding_window_view

    wa = sliding_window_view(a, (win, win))
    wb = sliding_window_view(b, (win, win))
    mu_a = wa.mean(axis=(-1, -2))
    mu_b = wb.mean(axis=(-1, -2))
    va = wa.var(axis=(-1, -2))
    vb = wb.var(axis=(-1, -2))
    cov = ((wa - mu_a[..., None, None]) * (wb - mu_b[..., None, None])).mean(axis=(-1, -2))
    c1 = (0.01 * data_range) ** 2
    c2 = (0.03 * data_range) ** 2
    ssim_map = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / \
               ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2))
    return float(ssim_map.mean())


def compute_diff(a: Image.Image, b: Image.Image, threshold: int = 8) -> DiffResult:
    """Hitung semua metrik perbedaan antara dua gambar berukuran sama."""
    aa, bb = _to_rgb_arrays(a, b)
    diff = np.abs(aa - bb)                                  # (H, W, 3) int16

    h, w, _ = diff.shape
    total = h * w

    # Magnitudo selisih = nilai maksimum antar channel
    magnitude = diff.max(axis=2).astype(np.uint8)           # (H, W)
    changed_mask = magnitude > threshold
    changed = int(np.count_nonzero(changed_mask))

    # MSE / RMSE dihitung dari semua channel (float)
    diff_f = diff.astype(np.float64)
    mse = float(np.mean(diff_f ** 2))
    rmse = float(np.sqrt(mse))
    if mse <= 1e-12:
        psnr = float("inf")
    else:
        psnr = float(10.0 * np.log10((255.0 ** 2) / mse))

    mean_diff = float(diff_f.mean())
    max_diff = int(diff.max())

    # Rata-rata per channel (R, G, B)
    per_channel = [float(diff_f[:, :, c].mean()) for c in range(3)]

    # Histogram magnitudo selisih
    histogram = np.bincount(magnitude.ravel(), minlength=256).astype(np.int64)

    # SSIM
    ssim_source = "numpy"
    ssim_val = 0.0
    if _HAVE_SKIMAGE:
        try:
            ssim_val = float(_sk_ssim(
                np.asarray(a.convert("RGB")),
                np.asarray(b.convert("RGB")),
                channel_axis=2,
                data_range=255,
            ))
            ssim_source = "scikit-image"
        except Exception:
            ssim_val = _fallback_ssim(
                np.asarray(a.convert("L"), dtype=np.float64),
                np.asarray(b.convert("L"), dtype=np.float64),
            )
    else:
        ssim_val = _fallback_ssim(
            np.asarray(a.convert("L"), dtype=np.float64),
            np.asarray(b.convert("L"), dtype=np.float64),
        )

    changed_percent = (changed / total * 100.0) if total else 0.0
    similarity_percent = max(0.0, 100.0 - mean_diff / 255.0 * 100.0)

    return DiffResult(
        total_pixels=total,
        changed_pixels=changed,
        changed_percent=changed_percent,
        mse=mse,
        rmse=rmse,
        psnr=psnr,
        ssim=ssim_val,
        similarity_percent=similarity_percent,
        mean_diff=mean_diff,
        max_diff=max_diff,
        per_channel_mean=per_channel,
        histogram=histogram,
        magnitude=magnitude,
        ssim_source=ssim_source,
    )


# --- Colormap untuk heatmap (ramp hitam->biru->sian->hijau->kuning->merah) ---
_STOPS = np.array([
    [0, 0, 0],
    [0, 0, 128],
    [0, 128, 255],
    [0, 255, 200],
    [120, 255, 60],
    [255, 220, 0],
    [255, 120, 0],
    [255, 0, 0],
], dtype=np.float32)


def _build_lut() -> np.ndarray:
    """Bangun lookup table 256x3 dari stop warna."""
    n = len(_STOPS) - 1
    xs = np.linspace(0, 1, len(_STOPS))
    lut = np.zeros((256, 3), dtype=np.uint8)
    t = np.linspace(0, 1, 256)
    for c in range(3):
        lut[:, c] = np.clip(np.interp(t, xs, _STOPS[:, c]), 0, 255).astype(np.uint8)
    return lut


_COLOR_LUT = _build_lut()


def make_heatmap(magnitude: np.ndarray, gain: float = 4.0) -> Image.Image:
    """Ubah peta magnitudo selisih menjadi gambar heatmap berwarna (RGBA)."""
    if magnitude is None:
        raise ValueError("magnitude kosong")
    amp = np.clip(magnitude.astype(np.float32) * float(gain), 0, 255)
    idx = amp.astype(np.uint8)
    rgb = _COLOR_LUT[idx]                                   # (H, W, 3)
    # area tanpa perbedaan -> transparan agar latar terlihat
    alpha = np.where(idx > 0, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba, mode="RGBA")


def make_diff_binary(magnitude: np.ndarray, threshold: int = 8,
                     color: tuple[int, int, int] = (255, 40, 40)) -> Image.Image:
    """Mask biner area yang berubah (RGBA, transparan di area sama)."""
    mask = magnitude > threshold
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[mask] = (*color, 200)
    return Image.fromarray(rgba, mode="RGBA")


def diff_side_by_side(a: Image.Image, b: Image.Image, heat: Image.Image,
                      gap: int = 12, bg=(40, 40, 44, 255)) -> Image.Image:
    """Komposit tiga panel: A | B | heatmap, untuk ekspor."""
    w, h = a.size
    canvas = Image.new("RGBA", (w * 3 + gap * 2, h), bg)
    canvas.paste(a.convert("RGBA"), (0, 0))
    canvas.paste(b.convert("RGBA"), (w + gap, 0))
    canvas.paste(heat.convert("RGBA"), (w * 2 + gap * 2, 0), heat.convert("RGBA"))
    return canvas


def slider_composite(a: Image.Image, b: Image.Image, position: float,
                     bg=(0, 0, 0, 0)) -> Image.Image:
    """Komposit mode slider: kiri A, kanan B, dipisah pada `position` (0..1)."""
    w, h = a.size
    split = int(max(0.0, min(1.0, position)) * w)
    left = a.convert("RGBA").crop((0, 0, split, h))
    right = b.convert("RGBA").crop((split, 0, w, h))
    canvas = Image.new("RGBA", (w, h), bg)
    canvas.paste(left, (0, 0))
    canvas.paste(right, (split, 0))
    return canvas
