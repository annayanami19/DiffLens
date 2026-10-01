"""Mode OVERLAY: Gambar B ditumpuk di atas Gambar A dengan opasitas.

Berguna untuk melihat posisi pergeseran/penempatan objek.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from .base import CompareView


class OverlayCompareView(CompareView):
    """Tumpuk B di atas A dengan opasitas 0..100."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._opacity = 0.5  # 0..1

    def set_opacity_percent(self, percent: int) -> None:
        self._opacity = max(0, min(100, int(percent))) / 100.0
        self.update()

    def opacity_percent(self) -> int:
        return int(round(self._opacity * 100))

    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        img_a = self._img_a
        img_b = self._img_b
        if img_a is None and img_b is None:
            return
        if img_a is None:
            self.paint_image(painter, img_b, rect, "b")
            return
        if img_b is None:
            self.paint_image(painter, img_a, rect, "a")
            return

        painter.setOpacity(1.0)
        self.paint_image(painter, img_a, rect, "a")
        painter.setOpacity(self._opacity)
        self.paint_image(painter, img_b, rect, "b")
        painter.setOpacity(1.0)

        self.draw_label(painter, f"B {self.opacity_percent()}%",
                        QPointF(rect.left() + 8, rect.top() + 8))
