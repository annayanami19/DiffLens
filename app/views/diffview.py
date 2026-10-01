"""Mode HEATMAP DIFF: menampilkan peta perbedaan berwarna.

Perbedaan antara A dan B diwarnai (colormap) dan diperkuat dengan
`gain` agar selisih tipis terlihat. `threshold` menentukan area yang
dianggap berubah.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..image_utils import pil_to_qimage
from ..diff import make_heatmap, make_diff_binary
from .base import CompareView


class DiffHeatmapView(CompareView):
    """Tampilkan heatmap perbedaan di atas latar gelap."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._magnitude = None      # numpy (H, W) uint8
        self._gain = 4.0
        self._threshold = 8
        self._heat_qimage: QImage | None = None
        self._binary = False
        self._heat_dirty = True

        # Timer penunda: koalisi perubahan cepat (mis. drag spinbox) menjadi
        # satu pembangunan heatmap saja -> UI tidak tersendat.
        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(60)
        self._rebuild_timer.timeout.connect(self._rebuild_now)

    # ------------------------------------------------------------------ API
    def set_magnitude(self, magnitude) -> None:
        """Set peta magnitudo selisih (numpy array) dari worker."""
        self._magnitude = magnitude
        self._pix_cache.clear()
        self._schedule_rebuild()

    def set_gain(self, gain: float) -> None:
        self._gain = max(0.1, float(gain))
        self._schedule_rebuild()

    def set_threshold(self, threshold: int) -> None:
        self._threshold = int(threshold)
        self._schedule_rebuild()

    def set_binary(self, enabled: bool) -> None:
        self._binary = bool(enabled)
        self._schedule_rebuild()

    def _schedule_rebuild(self) -> None:
        self._heat_dirty = True
        self._rebuild_timer.start()

    def _rebuild_now(self) -> None:
        """Bangun gambar heatmap di luar paintEvent (dipanggil oleh timer)."""
        if self._magnitude is None:
            self._heat_qimage = None
            self._heat_dirty = False
            self.update()
            return
        if self._binary:
            pil = make_diff_binary(self._magnitude, self._threshold)
        else:
            pil = make_heatmap(self._magnitude, self._gain)
        self._heat_qimage = pil_to_qimage(pil)
        self._heat_dirty = False
        self._pix_cache.clear()
        self.update()

    def image_size(self):
        if self._magnitude is not None:
            h, w = self._magnitude.shape[:2]
            from PySide6.QtCore import QSize
            return QSize(w, h)
        return super().image_size()

    @property
    def has_image(self) -> bool:  # type: ignore[override]
        return self._magnitude is not None

    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        if self._magnitude is None:
            return
        if self._heat_qimage is not None:
            self.paint_image(painter, self._heat_qimage, rect, "heat")


        self.draw_label(
            painter,
            f"gain x{self._gain:.1f}  thr {self._threshold}",
            QPointF(rect.left() + 8, rect.top() + 8),
        )
