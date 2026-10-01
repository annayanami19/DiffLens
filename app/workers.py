"""Pekerja latar belakang (thread) untuk menghitung perbedaan gambar
tanpa membekukan antarmuka.

Pola: QRunnable + QThreadPool. Sinyal dikirim balik ke thread GUI.
"""

from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .diff import DiffResult, compute_diff
from .image_utils import LoadedImage, match_size


class _WorkerSignals(QObject):
    """Sinyal yang dibawa oleh DiffWorker (QRunnable tidak bisa punya sinyal)."""

    finished = Signal(object)   # DiffResult
    error = Signal(str)


class DiffWorker(QRunnable):
    """Hitung perbedaan dua gambar di thread pool."""

    def __init__(self, image_a: Image.Image, image_b: Image.Image, threshold: int = 8) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._a = image_a
        self._b = image_b
        self._threshold = threshold
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:  # dijalankan di thread terpisah
        try:
            result: DiffResult = compute_diff(self._a, self._b, self._threshold)
            self.signals.finished.emit(result)
        except Exception as exc:  # pragma: no cover - diteruskan ke UI
            self.signals.error.emit(str(exc))


class DiffService(QObject):
    """Pembungkus QThreadPool agar UI cukup menghubungkan sinyalnya."""

    resultReady = Signal(object)   # DiffResult
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._busy = False
        self._workers: list[DiffWorker] = []

    def is_busy(self) -> bool:
        return self._busy

    def compute(self, image_a: Image.Image, image_b: Image.Image, threshold: int = 8) -> None:
        """Jalankan perhitungan. Permintaan terakhir yang menang."""
        worker = DiffWorker(image_a, image_b, threshold)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda _r, w=worker: self._release(w))
        worker.signals.error.connect(lambda _m, w=worker: self._release(w))
        self._workers.append(worker)
        self._busy = True
        self._pool.start(worker)

    def _release(self, worker: "DiffWorker") -> None:
        try:
            self._workers.remove(worker)
        except ValueError:
            pass


    @Slot(object)
    def _on_finished(self, result: object) -> None:
        self._busy = False
        self.resultReady.emit(result)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._busy = False
        self.failed.emit(message)


class _MatchSignals(QObject):
    finished = Signal(object, object)   # matched_a, matched_b
    error = Signal(str)


class MatchWorker(QRunnable):
    """Samakan ukuran dua gambar di thread pool (bisa berat untuk gambar besar)."""

    def __init__(self, a: LoadedImage, b: LoadedImage, fit_mode: str,
                 scale_mode: str) -> None:
        super().__init__()
        self.signals = _MatchSignals()
        self._a = a
        self._b = b
        self._fit = fit_mode
        self._scale = scale_mode
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            ma, mb = match_size(self._a, self._b, self._fit, self._scale)
            self.signals.finished.emit(ma, mb)
        except Exception as exc:  # pragma: no cover
            self.signals.error.emit(str(exc))


class MatchService(QObject):
    """Jalankan penyamaan ukuran tanpa membekukan UI."""

    resultReady = Signal(object, object)   # matched_a, matched_b
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._gen = 0
        self._workers: list[MatchWorker] = []

    def compute(self, a: LoadedImage, b: LoadedImage, fit_mode: str,
                scale_mode: str) -> None:
        self._gen += 1
        gen = self._gen
        worker = MatchWorker(a, b, fit_mode, scale_mode)
        self._workers.append(worker)

        def _done(ma, mb, _gen=gen, _w=worker):
            self._release(_w)
            if _gen == self._gen:      # abaikan hasil usang
                self.resultReady.emit(ma, mb)

        def _fail(msg, _gen=gen, _w=worker):
            self._release(_w)
            if _gen == self._gen:
                self.failed.emit(msg)

        worker.signals.finished.connect(_done)
        worker.signals.error.connect(_fail)
        self._pool.start(worker)

    def _release(self, worker: "MatchWorker") -> None:
        try:
            self._workers.remove(worker)
        except ValueError:
            pass

