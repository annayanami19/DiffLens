"""Generator ikon aplikasi DiffLens.

Menghasilkan:
    assets/app_icon.png   (512x512, RGBA)
    assets/app_icon.ico   (multi-ukuran: 16/24/32/48/64/128/256)

Motif "Slider Split": dua panel gambar dipisah garis slider dengan
handle bundar — melambangkan fitur utama pembanding gambar.

Gambar digambar pada resolusi 4x (supersampling) lalu diperkecil
dengan LANCZOS agar tepi halus.

Jalankan:  python tools/make_icon.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

# --- Palet warna (selaras tema aplikasi) ---
BLUE = (76, 139, 245, 255)          # #4c8bf5 aksen utama
BLUE_DARK = (38, 84, 168, 255)
BG_TOP = (38, 40, 46, 255)          # panel gelap
BG_BOTTOM = (24, 25, 28, 255)
LEFT_TINT = (58, 78, 122, 255)      # kiri agak kebiruan
RIGHT_TINT = (150, 158, 172, 255)   # kanan lebih terang
HANDLE = (245, 247, 250, 255)
HANDLE_EDGE = (176, 184, 196, 255)

S = 4            # faktor supersampling
BASE = 512       # ukuran akhir PNG
SZ = BASE * S    # kanvas kerja


def _rounded_mask(size: int, radius: int) -> Image.Image:
    """Mask sudut membulat (mode L)."""
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def build_icon() -> Image.Image:
    """Gambar ikon pada kanvas besar, kembalikan RGBA ukuran BASE."""
    img = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1) Latar membulat dengan gradien vertikal sederhana
    radius = int(SZ * 0.22)
    bg = Image.new("RGBA", (SZ, SZ), BG_BOTTOM)
    top = Image.new("RGBA", (SZ, SZ), BG_TOP)
    grad = Image.new("RGBA", (SZ, SZ))
    for y in range(SZ):
        t = y / (SZ - 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        grad.paste((r, g, b, 255), (0, y, SZ, y + 1))
    del top, bg
    mask = _rounded_mask(SZ, radius)
    img.paste(grad, (0, 0), mask)

    # 2) Dua panel gambar di dalam (kiri gelap, kanan terang)
    pad = int(SZ * 0.16)
    inner = SZ - pad * 2
    inner_radius = int(inner * 0.10)
    panel_box = (pad, pad, pad + inner, pad + inner)

    # panel kiri (warna kebiruan gelap)
    left_layer = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
    ld = ImageDraw.Draw(left_layer)
    ld.rounded_rectangle(panel_box, radius=inner_radius, fill=LEFT_TINT)
    # panel kanan (lebih terang)
    right_layer = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
    rd = ImageDraw.Draw(right_layer)
    rd.rounded_rectangle(panel_box, radius=inner_radius, fill=RIGHT_TINT)

    # gabung: kiri setengah, kanan setengah (dipotong di tengah)
    mid = SZ // 2
    img.paste(left_layer, (0, 0), left_layer)
    right_crop = right_layer.crop((mid, 0, SZ, SZ))
    img.paste(right_crop, (mid, 0), right_crop)

    # 3) Bingkai tipis panel agar tegas
    draw.rounded_rectangle(panel_box, radius=inner_radius,
                           outline=(90, 96, 106, 220), width=max(1, SZ // 256))

    # 4) Garis pembatas slider (vertikal, di tengah)
    line_w = max(2, int(SZ * 0.018))
    draw.rectangle((mid - line_w // 2, pad, mid + line_w // 2, pad + inner),
                   fill=HANDLE)

    # 5) Handle bundar di tengah
    hr = int(inner * 0.16)
    cy = pad + inner // 2
    # bayangan
    draw.ellipse((mid - hr + line_w, cy - hr + line_w,
                  mid + hr + line_w, cy + hr + line_w),
                 fill=(0, 0, 0, 90))
    # lingkaran utama
    draw.ellipse((mid - hr, cy - hr, mid + hr, cy + hr),
                 fill=HANDLE, outline=HANDLE_EDGE, width=max(1, SZ // 320))

    # 6) Panah < > di dalam handle (biru)
    aw = int(hr * 0.40)
    ah = int(hr * 0.50)
    lw = max(3, int(SZ * 0.022))
    # panah kiri
    draw.line((mid - aw + lw, cy - ah, mid - aw - lw, cy),
              fill=BLUE, width=lw)
    draw.line((mid - aw - lw, cy, mid - aw + lw, cy + ah),
              fill=BLUE, width=lw)
    # panah kanan
    draw.line((mid + aw - lw, cy - ah, mid + aw + lw, cy),
              fill=BLUE, width=lw)
    draw.line((mid + aw + lw, cy, mid + aw - lw, cy + ah),
              fill=BLUE, width=lw)

    # perkecil ke ukuran akhir
    return img.resize((BASE, BASE), Image.Resampling.LANCZOS)


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "assets")
    os.makedirs(out_dir, exist_ok=True)

    icon = build_icon()

    png_path = os.path.join(out_dir, "app_icon.png")
    ico_path = os.path.join(out_dir, "app_icon.ico")

    icon.save(png_path, "PNG")

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(ico_path, "ICO", sizes=sizes)

    print("Ikon dibuat:")
    print(" -", png_path, os.path.getsize(png_path), "bytes")
    print(" -", ico_path, os.path.getsize(ico_path), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
