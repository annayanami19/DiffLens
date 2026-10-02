"""Internasionalisasi sederhana (Indonesia / English).

Penggunaan:
    from app.i18n import tr
    tr("open_a")  ->  "Buka Gambar A" / "Open Image A"

Bahasa aktif diubah lewat set_language("id" | "en").
"""

from __future__ import annotations

LANGUAGES = ("id", "en")

_current = "id"


def set_language(lang: str) -> None:
    global _current
    if lang in LANGUAGES:
        _current = lang


def get_language() -> str:
    return _current


# Kamus terjemahan. Setiap key harus punya versi id & en.
_STRINGS: dict[str, dict[str, str]] = {
    # Jendela & menu
    "app_title": {"id": "DiffLens - Pembanding Gambar", "en": "DiffLens - Image Comparator"},
    "menu_file": {"id": "Berkas", "en": "File"},
    "menu_view": {"id": "Tampilan", "en": "View"},
    "menu_tools": {"id": "Alat", "en": "Tools"},
    "menu_help": {"id": "Bantuan", "en": "Help"},
    "menu_open_a": {"id": "Buka Gambar A (Original)\tCtrl+O", "en": "Open Image A (Original)\tCtrl+O"},
    "menu_open_b": {"id": "Buka Gambar B (Hasil Edit)\tCtrl+Shift+O", "en": "Open Image B (Edited)\tCtrl+Shift+O"},
    "menu_swap": {"id": "Tukar A \u2194 B\tCtrl+T", "en": "Swap A \u2194 B\tCtrl+T"},
    "menu_export_heatmap": {"id": "Ekspor Heatmap Perbedaan...", "en": "Export Difference Heatmap..."},
    "menu_export_slider": {"id": "Ekspor Komposit Slider...", "en": "Export Slider Composite..."},
    "menu_export_side": {"id": "Ekspor Komposit Berdampingan...", "en": "Export Side-by-Side Composite..."},
    "menu_export_report": {"id": "Ekspor Laporan (.txt)...", "en": "Export Report (.txt)..."},
    "menu_quit": {"id": "Keluar\tCtrl+Q", "en": "Quit\tCtrl+Q"},
    "menu_mode": {"id": "Mode Perbandingan", "en": "Comparison Mode"},
    "menu_zoom": {"id": "Zoom", "en": "Zoom"},
    "menu_zoom_in": {"id": "Perbesar\tCtrl++", "en": "Zoom In\tCtrl++"},
    "menu_zoom_out": {"id": "Perkecil\tCtrl+-", "en": "Zoom Out\tCtrl+-"},
    "menu_fit": {"id": "Sesuaikan Jendela\tCtrl+0", "en": "Fit to Window\tCtrl+0"},
    "menu_actual": {"id": "Ukuran Asli (1:1)\tCtrl+1", "en": "Actual Size (1:1)\tCtrl+1"},
    "menu_checkerboard": {"id": "Latar Transparan (Checkerboard)", "en": "Transparent Background (Checkerboard)"},
    "menu_panels": {"id": "Panel", "en": "Panels"},
    "menu_show_left": {"id": "Panel Gambar (kiri)", "en": "Images Panel (left)"},
    "menu_show_right": {"id": "Panel Analisis (kanan)", "en": "Analysis Panel (right)"},
    "menu_hide_all_panels": {"id": "Sembunyikan Semua Panel", "en": "Hide All Panels"},
    "menu_show_all_panels": {"id": "Tampilkan Semua Panel", "en": "Show All Panels"},
    "tb_toggle_left": {"id": "Sembunyikan/tampilkan panel kiri", "en": "Toggle left panel"},
    "tb_toggle_right": {"id": "Sembunyikan/tampilkan panel kanan", "en": "Toggle right panel"},
    "menu_language": {"id": "Bahasa", "en": "Language"},
    "menu_lang_id": {"id": "Indonesia", "en": "Indonesian"},
    "menu_lang_en": {"id": "Inggris", "en": "English"},
    "menu_about": {"id": "Tentang Aplikasi", "en": "About"},
    "menu_shortcuts": {"id": "Pintasan Keyboard", "en": "Keyboard Shortcuts"},

    # Toolbar
    "tb_open_a": {"id": "Buka A (original)", "en": "Open A (original)"},
    "tb_open_b": {"id": "Buka B (hasil edit)", "en": "Open B (edited)"},
    "tb_swap": {"id": "Tukar A dan B", "en": "Swap A and B"},
    "tb_fit": {"id": "Sesuaikan jendela", "en": "Fit to window"},
    "tb_actual": {"id": "Ukuran asli 1:1", "en": "Actual size 1:1"},
    "tb_export": {"id": "Ekspor hasil", "en": "Export result"},

    # Mode
    "mode_slider": {"id": "Slider", "en": "Slider"},
    "mode_side": {"id": "Berdampingan", "en": "Side by Side"},
    "mode_blink": {"id": "Kedip", "en": "Blink"},
    "mode_overlay": {"id": "Overlay", "en": "Overlay"},
    "mode_diff": {"id": "Heatmap Diff", "en": "Diff Heatmap"},

    # Panel kiri
    "panel_images": {"id": "Gambar", "en": "Images"},
    "group_image_a": {"id": "Gambar A - Original", "en": "Image A - Original"},
    "group_image_b": {"id": "Gambar B - Hasil Edit", "en": "Image B - Edited"},
    "lbl_none": {"id": "(belum ada gambar)", "en": "(no image)"},
    "btn_open_a": {"id": "Pilih Gambar A...", "en": "Choose Image A..."},
    "btn_open_b": {"id": "Pilih Gambar B...", "en": "Choose Image B..."},
    "btn_swap": {"id": "Tukar A \u2194 B", "en": "Swap A \u2194 B"},
    "btn_clear": {"id": "Kosongkan Semua Gambar", "en": "Clear All Images"},
    "menu_clear": {"id": "Kosongkan Semua Gambar\tCtrl+Shift+C", "en": "Clear All Images\tCtrl+Shift+C"},
    "tb_clear": {"id": "Kosongkan kedua gambar", "en": "Clear both images"},
    "confirm_clear_title": {"id": "Konfirmasi", "en": "Confirm"},
    "confirm_clear_text": {
        "id": "Kosongkan kedua gambar? Tampilan dan analisis akan direset.",
        "en": "Clear both images? The view and analysis will be reset.",
    },
    "status_cleared": {"id": "Gambar dikosongkan.", "en": "Images cleared."},
    "lbl_drop_hint": {
        "id": "Tarik & lepas gambar ke sini.\nLepas 1 file = isi slot A, 2 file = A dan B.",
        "en": "Drag & drop images here.\nDrop 1 file = fills slot A, 2 files = A and B.",
    },
    "group_canvas": {"id": "Kanvas & Ukuran", "en": "Canvas & Size"},
    "lbl_fit_mode": {"id": "Samakan ukuran ke:", "en": "Match size to:"},
    "fit_to_largest": {"id": "Yang terbesar", "en": "Largest"},
    "fit_to_a": {"id": "Gambar A", "en": "Image A"},
    "fit_to_b": {"id": "Gambar B", "en": "Image B"},
    "lbl_scale_mode": {"id": "Penyesuaian:", "en": "Adjustment:"},
    "scale_contain": {"id": "Skala (jaga rasio)", "en": "Scale (keep ratio)"},
    "scale_stretch": {"id": "Regangkan (paksa)", "en": "Stretch (force)"},
    "chk_checkerboard": {"id": "Latar transparan", "en": "Transparent bg"},

    # Panel kanan / metrik
    "panel_metrics": {"id": "Analisis Perbedaan", "en": "Difference Analysis"},
    "group_metrics": {"id": "Metrik", "en": "Metrics"},
    "group_diff_opts": {"id": "Opsi Perbedaan", "en": "Difference Options"},
    "metric_changed_px": {"id": "Piksel berubah", "en": "Changed pixels"},
    "metric_changed_pct": {"id": "Persentase berubah", "en": "Changed percent"},
    "metric_mse": {"id": "MSE", "en": "MSE"},
    "metric_rmse": {"id": "RMSE", "en": "RMSE"},
    "metric_psnr": {"id": "PSNR", "en": "PSNR"},
    "metric_ssim": {"id": "SSIM", "en": "SSIM"},
    "metric_mean": {"id": "Rata-rata selisih", "en": "Mean difference"},
    "metric_max": {"id": "Selisih maksimum", "en": "Max difference"},
    "metric_similarity": {"id": "Tingkat kemiripan", "en": "Similarity"},
    "lbl_threshold": {"id": "Ambang piksel berubah:", "en": "Changed-pixel threshold:"},
    "lbl_gain": {"id": "Amplifikasi heatmap:", "en": "Heatmap gain:"},
    "lbl_blink_interval": {"id": "Interval kedip (ms):", "en": "Blink interval (ms):"},
    "lbl_opacity": {"id": "Opasitas overlay:", "en": "Overlay opacity:"},
    "btn_recompute": {"id": "Hitung Ulang", "en": "Recompute"},
    "lbl_histogram": {"id": "Histogram selisih", "en": "Difference histogram"},
    "lbl_no_data": {"id": "Muat dua gambar untuk melihat analisis.", "en": "Load two images to see the analysis."},

    # Overlay slider pada mode slider
    "lbl_slider_hint": {"id": "Geser garis pembatas untuk membandingkan.", "en": "Drag the divider line to compare."},

    # Status bar
    "status_ready": {"id": "Siap. Buka dua gambar untuk memulai.", "en": "Ready. Open two images to start."},
    "status_computing": {"id": "Menghitung perbedaan...", "en": "Computing differences..."},
    "status_done": {"id": "Selesai.", "en": "Done."},
    "status_loaded_a": {"id": "Gambar A dimuat", "en": "Image A loaded"},
    "status_loaded_b": {"id": "Gambar B dimuat", "en": "Image B loaded"},
    "status_zoom": {"id": "Zoom", "en": "Zoom"},

    # Dialog & pesan
    "dlg_open_a_title": {"id": "Pilih Gambar A (Original)", "en": "Select Image A (Original)"},
    "dlg_open_b_title": {"id": "Pilih Gambar B (Hasil Edit)", "en": "Select Image B (Edited)"},
    "dlg_export_title": {"id": "Simpan Hasil", "en": "Save Result"},
    "err_title": {"id": "Kesalahan", "en": "Error"},
    "err_load": {"id": "Gagal memuat gambar:", "en": "Failed to load image:"},
    "err_need_two": {
        "id": "Muat Gambar A dan Gambar B terlebih dahulu.",
        "en": "Load both Image A and Image B first.",
    },
    "err_need_a": {"id": "Muat Gambar A terlebih dahulu.", "en": "Load Image A first."},
    "err_need_b": {"id": "Muat Gambar B terlebih dahulu.", "en": "Load Image B first."},
    "info_export_ok": {"id": "Berhasil disimpan ke:\n{path}", "en": "Saved to:\n{path}"},
    "dlg_report_title": {"id": "Simpan Laporan", "en": "Save Report"},

    # Tentang
    "about_title": {"id": "Tentang DiffLens", "en": "About DiffLens"},
    "about_text": {
        "id": (
            "DiffLens {version}\n\n"
            "Aplikasi pembanding dua gambar dengan slider geser, mode berdampingan,\n"
            "kedip, overlay, dan heatmap perbedaan. Dilengkapi metrik MSE, RMSE,\n"
            "PSNR, dan SSIM.\n\n"
            "Dibuat dengan Python + PySide6.\n\n"
            "Lisensi: MIT License."
        ),
        "en": (
            "DiffLens {version}\n\n"
            "Compare two images with a draggable slider, side-by-side, blink,\n"
            "overlay, and difference heatmap modes. Includes MSE, RMSE, PSNR,\n"
            "and SSIM metrics.\n\n"
            "Built with Python + PySide6.\n\n"
            "License: MIT License."
        ),
    },
    "shortcuts_title": {"id": "Pintasan Keyboard", "en": "Keyboard Shortcuts"},
    "shortcuts_text": {
        "id": (
            "Ctrl+O        Buka Gambar A\n"
            "Ctrl+Shift+O  Buka Gambar B\n"
            "Ctrl+T        Tukar A \u2194 B\n"
            "Ctrl+Shift+C  Kosongkan semua gambar\n"
            "Ctrl+1        Ukuran asli 1:1\n"
            "Ctrl+0        Sesuaikan jendela\n"
            "Ctrl++ / -    Zoom in / out\n"
            "1..5          Ganti mode perbandingan\n"
            "Panah Kiri/Kanan  Geser pembatas slider\n"
            "Spasi         Jeda/lanjut kedip (mode Kedip)\n"
            "Ctrl+Shift+1  Sembunyikan/tampilkan panel kiri\n"
            "Ctrl+Shift+2  Sembunyikan/tampilkan panel kanan\n"
            "Ctrl+Shift+H  Sembunyikan/tampilkan semua panel\n"
            "Ctrl+Q        Keluar"
        ),
        "en": (
            "Ctrl+O        Open Image A\n"
            "Ctrl+Shift+O  Open Image B\n"
            "Ctrl+T        Swap A \u2194 B\n"
            "Ctrl+Shift+C  Clear all images\n"
            "Ctrl+1        Actual size 1:1\n"
            "Ctrl+0        Fit to window\n"
            "Ctrl++ / -    Zoom in / out\n"
            "1..5          Switch comparison mode\n"
            "Left/Right Arrow  Move slider divider\n"
            "Space         Pause/resume blink (Blink mode)\n"
            "Ctrl+Shift+1  Toggle left panel\n"
            "Ctrl+Shift+2  Toggle right panel\n"
            "Ctrl+Shift+H  Toggle all panels\n"
            "Ctrl+Q        Quit"
        ),
    },
}


def tr(key: str, **kwargs) -> str:
    """Terjemahkan key ke bahasa aktif. Format {placeholder} bila ada kwargs."""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
