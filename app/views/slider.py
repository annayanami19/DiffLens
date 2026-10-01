"""Mode SLIDER: garis pembatas yang bisa digeser.

Kiri garis menampilkan Gambar A (original), kanan garis menampilkan
Gambar B (hasil edit). Garis bisa digeser dengan drag, klik, atau
tombol panah kiri/kanan.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from .base import CompareView

HANDLE_RADIUS = 14
HIT_TOLERANCE = 16  # jarak klik untuk mulai drag handle


class SliderCompareView(CompareView):
    """Perbandingan before/after dengan pembatas geser."""

    positionChanged = Signal(float)  # 0.0 .. 1.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._position = 0.5          # rasio 0..1 dari lebar gambar
        self._dragging = False
        self._hover_handle = False
        self.setCursor(Qt.CursorShape.SplitHCursor)

    # ------------------------------------------------------------- posisi
    def position(self) -> float:
        return self._position

    def set_position(self, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        if abs(value - self._position) < 1e-6:
            return
        self._position = value
        self.positionChanged.emit(self._position)
        self.update()

    def nudge(self, delta: float) -> None:
        """Geser sedikit (untuk tombol panah). delta dalam rasio."""
        self.set_position(self._position + delta)

    def _split_x(self) -> float:
        rect = self.image_rect()
        return rect.left() + rect.width() * self._position

    # ------------------------------------------------------------- event
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.has_image:
            rect = self.image_rect()
            if rect.contains(event.position()) or abs(event.position().x() - self._split_x()) <= HIT_TOLERANCE:
                self._dragging = True
                self._update_position_from_x(event.position().x())
                self.setCursor(Qt.CursorShape.SplitHCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._update_position_from_x(event.position().x())
            event.accept()
            return
        # hover feedback pada handle
        if self.has_image:
            near = abs(event.position().x() - self._split_x()) <= HIT_TOLERANCE
            if near != self._hover_handle:
                self._hover_handle = near
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Ctrl+scroll = zoom; scroll biasa tetap zoom (perilaku dasar).
        super().wheelEvent(event)

    def _update_position_from_x(self, x: float) -> None:
        rect = self.image_rect()
        if rect.width() <= 0:
            return
        self.set_position((x - rect.left()) / rect.width())

    # ------------------------------------------------------------- painting
    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        img_a = self._img_a
        img_b = self._img_b

        # Bila hanya satu gambar tersedia, tampilkan itu saja.
        if img_a is None and img_b is None:
            return
        if img_a is None:
            self.paint_image(painter, img_b, rect, "b")
            return
        if img_b is None:
            self.paint_image(painter, img_a, rect, "a")
            return

        split_x = rect.left() + rect.width() * self._position

        # --- sisi kiri: gambar A (hanya area kiri garis) ---
        left_clip = QRectF(rect.left(), rect.top(),
                           max(0.0, split_x - rect.left()), rect.height())
        self.paint_image(painter, img_a, rect, "a", clip=left_clip)

        # --- sisi kanan: gambar B (hanya area kanan garis) ---
        right_clip = QRectF(split_x, rect.top(),
                            max(0.0, rect.right() - split_x), rect.height())
        self.paint_image(painter, img_b, rect, "b", clip=right_clip)

        # --- garis pembatas ---
        self._draw_divider(painter, rect, split_x)

        # --- label A / B ---
        if rect.width() > 160:
            self.draw_label(painter, "A", QPointF(rect.left() + 8, rect.top() + 8))
            self.draw_label(painter, "B", QPointF(rect.right() - 40, rect.top() + 8))

    def _draw_divider(self, painter: QPainter, rect: QRectF, split_x: float) -> None:
        pen = QPen(QColor(255, 255, 255, 235), 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(split_x, rect.top()), QPointF(split_x, rect.bottom()))

        # handle bundar di tengah vertikal
        cy = rect.center().y()
        radius = HANDLE_RADIUS + (2 if (self._hover_handle or self._dragging) else 0)

        # bayangan lembut
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.drawEllipse(QPointF(split_x + 1, cy + 2), radius, radius)

        grad = QLinearGradient(split_x, cy - radius, split_x, cy + radius)
        grad.setColorAt(0.0, QColor(255, 255, 255, 245))
        grad.setColorAt(1.0, QColor(210, 214, 220, 245))
        painter.setBrush(grad)
        painter.setPen(QPen(QColor(120, 124, 130), 1))
        painter.drawEllipse(QPointF(split_x, cy), radius, radius)

        # panah < > di dalam handle
        painter.setPen(QPen(QColor(40, 42, 46), 2))
        arrow_dx = 5
        arrow_dy = 5
        painter.drawLine(QPointF(split_x - arrow_dx, cy - arrow_dy),
                         QPointF(split_x - arrow_dx - 1, cy))
        painter.drawLine(QPointF(split_x - arrow_dx - 1, cy),
                         QPointF(split_x - arrow_dx, cy + arrow_dy))
        painter.drawLine(QPointF(split_x + arrow_dx, cy - arrow_dy),
                         QPointF(split_x + arrow_dx + 1, cy))
        painter.drawLine(QPointF(split_x + arrow_dx + 1, cy),
                         QPointF(split_x + arrow_dx, cy + arrow_dy))

    # dukungan tombol panah dari MainWindow
    def keyPressEvent(self, event) -> None:
        step = 0.005
        if event.key() == Qt.Key.Key_Left:
            self.nudge(-step)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self.nudge(step)
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            self.set_position(0.0)
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            self.set_position(1.0)
            event.accept()
        else:
            super().keyPressEvent(event)
