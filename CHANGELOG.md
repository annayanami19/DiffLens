# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Rencana: paket instalasi mandiri (PyInstaller) untuk Windows.

## [1.0.0] - 2026-10-02

Rilis publik pertama **DiffLens** — aplikasi desktop pembanding dua gambar.

### Added

- **Mode perbandingan:**
  - **Slider** (utama): garis pembatas digeser; kiri = gambar A (original),
    kanan = gambar B (hasil edit). Bisa drag, klik, dan digeser dengan
    tombol panah kiri/kanan.
  - **Berdampingan**: A dan B sejajar dengan zoom & pan tersinkron.
  - **Kedip (blink)**: bergantian A↔B otomatis untuk melihat perubahan halus.
  - **Overlay**: B ditumpuk di atas A dengan pengatur opasitas.
  - **Heatmap Diff**: peta perbedaan berwarna dengan penguat (gain) dan
    mode biner.
- **Analisis perbedaan:** jumlah & persentase piksel berubah, SSIM, PSNR, MSE,
  RMSE, rata-rata & maksimum selisih, rata-rata per channel, tingkat kemiripan,
  dan histogram selisih. Perhitungan berjalan di thread latar.
- **Tampilan:** zoom (scroll), pan (drag), fit, ukuran asli 1:1, latar
  checkerboard untuk area transparan, dan penyamaan ukuran kanvas
  (skala jaga-rasio / regangkan).
- **Input/Output:** buka gambar via dialog & drag-and-drop, tukar A↔B,
  ekspor heatmap diff (PNG), komposit slider (PNG), komposit berdampingan
  (PNG), dan laporan teks (`.txt`).
- **Antarmuka:** dwibahasa Indonesia/English, tema gelap, panel kiri & kanan
  yang bisa disembunyikan/ditampilkan, status bar, dan pintasan keyboard.
- **Ikon aplikasi** (motif "Slider Split") multi-ukuran (16–256 px) beserta
  generator ikon di `tools/make_icon.py`.
- Pengaturan tersimpan otomatis (folder, bahasa, mode, ukuran jendela,
  tata letak panel).

### Changed

- Penyamaan ukuran gambar kini **menjaga rasio** (tidak lagi menempelkan
  gambar kecil apa adanya), dengan opsi peregangan bila diinginkan.
- Penyamaan ukuran dipindah ke thread latar + debounce agar antarmuka tidak
  membeku.
- Rendering dioptimalkan (cache pixmap + menggambar hanya area terlihat saat
  zoom) untuk mengurangi lag.
- Panel kiri/kanan diberi lebar minimum dan teks tidak lagi terpotong.

### Fixed

- Perbaikan `start.bat` yang gagal dijalankan (line ending CRLF + penghapusan
  blok kurung yang salah di-parse oleh `cmd.exe`).
- Perbaikan nilai metrik dan teks combo yang sebelumnya terpotong.
- Perbaikan buffer gambar (`QImage`) yang berpotensi rusak akibat data NumPy
  tidak disalin.

### Security

- Tidak ada kredensial atau data sensitif yang disertakan. Aplikasi berjalan
  sepenuhnya luring; tidak mengirim data ke layanan eksternal.
