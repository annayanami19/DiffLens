"""Mode BERDAMPINGAN: Gambar A dan B ditampilkan sejajar.

Zoom & pan disinkronkan (satu panel mengendalikan yang lain) sehingga
kedua gambar selalu sejajar saat diperbesar.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QWidget

from .base import CompareView


class _Panel(CompareView):
    """Satu panel yang hanya menampilkan satu gambar (A atau B)."""

    viewChanged = Signal()

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._slot = "a" if label == "A" else "b"

    def set_single(self, image, label: str | None = None) -> None:
        if label is not None:
            self._label = label
        self.set_images(image, None)

    def image_size(self):
        img = self._img_a or self._img_b
        return img.size() if img is not None else super().image_size()

    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        img = self._img_a or self._img_b
        if img is None:
            return
        self.paint_image(painter, img, rect, self._slot)
        self.draw_label(painter, self._label,
                        QPointF(rect.left() + 8, rect.top() + 8))

    # Pancarkan sinyal setiap kali skala / pan berubah.
    def _zoom_to(self, new_scale, anchor) -> None:
        super()._zoom_to(new_scale, anchor)
        self.viewChanged.emit()

    def mouseMoveEvent(self, event) -> None:
        was_panning = self._panning
        super().mouseMoveEvent(event)
        if was_panning:
            self.viewChanged.emit()


class SideBySideView(QWidget):
    """Dua panel berdampingan dengan zoom/pan tersinkron."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.left = _Panel("A", self)
        self.right = _Panel("B", self)
        layout.addWidget(self.left, 1)
        layout.addWidget(self.right, 1)

        self.zoomChanged = self.left.zoomChanged

        self._syncing = False
        self.left.viewChanged.connect(lambda: self._sync(self.left, self.right))
        self.right.viewChanged.connect(lambda: self._sync(self.right, self.left))

    def _sync(self, src: _Panel, dst: _Panel) -> None:
        if self._syncing:
            return
        self._syncing = True
        dst._scale = src._scale
        dst._pan = QPointF(src._pan)
        dst._auto_fit = src._auto_fit
        dst.update()
        self._syncing = False

    # ------------------------------------------------------------------ API
    def set_images(self, img_a, img_b) -> None:
        self.left.set_single(img_a, "A")
        self.right.set_single(img_b, "B")
        self._syncing = True
        self.left.fit()
        self.right.fit()
        self._syncing = False

    def set_checkerboard(self, enabled: bool) -> None:
        self.left.set_checkerboard(enabled)
        self.right.set_checkerboard(enabled)

    @property
    def has_image(self) -> bool:
        return self.left.has_image or self.right.has_image

    def fit(self) -> None:
        self._syncing = True
        self.left.fit()
        self.right.fit()
        self._syncing = False

    def actual_size(self) -> None:
        self._syncing = True
        self.left.actual_size()
        self.right.actual_size()
        self._syncing = False

    def reset_view(self) -> None:
        self.fit()

    def zoom_in(self) -> None:
        self.left.zoom_in()

    def zoom_out(self) -> None:
        self.left.zoom_out()
