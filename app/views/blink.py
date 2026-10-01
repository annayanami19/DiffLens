"""Mode KEDIP (blink): bergantian menampilkan A dan B secara otomatis.

Berguna untuk menangkap perubahan halus: mata lebih mudah melihat
perbedaan saat gambar berganti cepat.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from .base import CompareView


class BlinkCompareView(CompareView):
    """Tampilkan A/B bergantian dengan interval tertentu."""

    stateChanged = Signal(bool)  # True = sedang menampilkan B

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._show_b = False
        self._interval_ms = 500
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._toggle)

    # ------------------------------------------------------------------ API
    def start(self) -> None:
        if self.has_image and not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    def toggle_running(self) -> None:
        if self.is_running():
            self.stop()
        else:
            self.start()

    def set_interval(self, ms: int) -> None:
        self._interval_ms = max(50, int(ms))
        self._timer.setInterval(self._interval_ms)

    def set_images(self, img_a, img_b) -> None:
        super().set_images(img_a, img_b)
        # Timer dijalankan oleh MainWindow hanya saat mode kedip aktif.
        self.stop()
        self._show_b = False
        self.update()

    def _toggle(self) -> None:
        self._show_b = not self._show_b
        self.stateChanged.emit(self._show_b)
        self.update()

    # ------------------------------------------------------------- painting
    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        img = self._img_b if self._show_b else self._img_a
        slot = "b" if self._show_b else "a"
        if img is None:
            img = self._img_b or self._img_a
            slot = "b" if self._img_b is not None else "a"
        if img is None:
            return
        self.paint_image(painter, img, rect, slot)
        self.draw_label(painter, "B" if self._show_b else "A",
                        QPointF(rect.left() + 8, rect.top() + 8))
        if not self.is_running():
            self.draw_label(painter, "PAUSE",
                            QPointF(rect.left() + 8, rect.top() + 40))
