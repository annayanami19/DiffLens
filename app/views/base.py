"""View dasar untuk perbandingan gambar.

Menyediakan: penyimpanan dua gambar (QImage), zoom (scroll), pan
(drag tombol tengah / kanan), mode sesuaikan jendela & ukuran asli,
serta latar checkerboard untuk area transparan.

OPTIMASI PENTING:
- Saat seluruh gambar terlihat (pas di jendela), gambar diskalakan SEKALI
  ke ukuran target lalu di-cache sebagai QPixmap. Pan tidak mengubah ukuran,
  jadi cache dipakai ulang -> repaint sangat murah.
- Saat gambar lebih besar dari jendela (zoom-in), hanya bagian yang TERLIHAT
  yang digambar (source-rect), sehingga tidak memproses piksel di luar layar.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

MIN_SCALE = 0.02
MAX_SCALE = 64.0


class CompareView(QWidget):
    """Widget dasar menampilkan dua gambar dengan zoom & pan."""

    zoomChanged = Signal(float)   # skala saat ini (1.0 = 100%)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)

        self._img_a: QImage | None = None
        self._img_b: QImage | None = None

        self._scale: float = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._auto_fit = True

        self._checkerboard = True
        self._checker_brush: QBrush | None = None

        # cache pixmap hasil skala: slot -> (lebar, tinggi, QPixmap)
        self._pix_cache: dict[str, tuple[int, int, QPixmap]] = {}

        # status pan
        self._panning = False
        self._pan_start = QPointF()
        self._pan_origin = QPointF()

        self._label_font = QFont("Segoe UI", 10, QFont.Weight.Bold)

    # ------------------------------------------------------------------ data
    def set_images(self, img_a: QImage | None, img_b: QImage | None) -> None:
        self._img_a = img_a
        self._img_b = img_b
        self._pix_cache.clear()
        self._pan = QPointF(0.0, 0.0)
        self._auto_fit = True
        self.fit()
        self.update()

    def set_checkerboard(self, enabled: bool) -> None:
        self._checkerboard = enabled
        self.update()

    @property
    def has_image(self) -> bool:
        return self._img_a is not None or self._img_b is not None

    def image_size(self) -> QSize:
        """Ukuran kanvas (dari gambar yang tersedia)."""
        for img in (self._img_a, self._img_b):
            if img is not None:
                return img.size()
        return QSize(0, 0)

    # --------------------------------------------------------------- geometri
    def image_rect(self) -> QRectF:
        """Posisi & ukuran area gambar di koordinat widget."""
        size = self.image_size()
        if size.isEmpty():
            return QRectF()
        w = size.width() * self._scale
        h = size.height() * self._scale
        x = (self.width() - w) / 2.0 + self._pan.x()
        y = (self.height() - h) / 2.0 + self._pan.y()
        return QRectF(x, y, w, h)

    def widget_to_image(self, pos: QPointF) -> QPointF:
        """Konversi titik widget ke koordinat piksel gambar."""
        rect = self.image_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return QPointF(0, 0)
        return QPointF(
            (pos.x() - rect.left()) / self._scale,
            (pos.y() - rect.top()) / self._scale,
        )

    # ----------------------------------------------------------------- zoom
    def fit(self) -> None:
        size = self.image_size()
        if size.isEmpty():
            return
        margin = 12
        avail_w = max(1, self.width() - margin * 2)
        avail_h = max(1, self.height() - margin * 2)
        scale = min(avail_w / size.width(), avail_h / size.height())
        self._scale = max(MIN_SCALE, min(MAX_SCALE, scale))
        self._pan = QPointF(0.0, 0.0)
        self._auto_fit = True
        self._pix_cache.clear()
        self.zoomChanged.emit(self._scale)
        self.update()

    def actual_size(self) -> None:
        self._scale = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._auto_fit = False
        self._pix_cache.clear()
        self.zoomChanged.emit(self._scale)
        self.update()

    def reset_view(self) -> None:
        self.fit()

    def zoom_in(self) -> None:
        self._zoom_to(self._scale * 1.25, QPointF(self.width() / 2, self.height() / 2))

    def zoom_out(self) -> None:
        self._zoom_to(self._scale / 1.25, QPointF(self.width() / 2, self.height() / 2))

    def _zoom_to(self, new_scale: float, anchor: QPointF) -> None:
        new_scale = max(MIN_SCALE, min(MAX_SCALE, new_scale))
        if abs(new_scale - self._scale) < 1e-9:
            return
        size = self.image_size()
        if size.isEmpty():
            self._scale = new_scale
            self.zoomChanged.emit(self._scale)
            self.update()
            return
        # titik gambar di bawah kursor harus tetap
        img_pt = self.widget_to_image(anchor)
        self._scale = new_scale
        w = size.width() * new_scale
        h = size.height() * new_scale
        base_x = (self.width() - w) / 2.0
        base_y = (self.height() - h) / 2.0
        self._pan = QPointF(
            anchor.x() - img_pt.x() * new_scale - base_x,
            anchor.y() - img_pt.y() * new_scale - base_y,
        )
        self._auto_fit = False
        self._pix_cache.clear()
        self.zoomChanged.emit(self._scale)
        self.update()

    # --------------------------------------------------------------- event
    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.has_image:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        self._zoom_to(self._scale * factor, event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = True
            self._pan_start = event.position()
            self._pan_origin = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan = self._pan_origin + delta
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._panning and event.button() in (
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.RightButton,
        ):
            self._panning = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._auto_fit and self.has_image:
            self.fit()

    # --------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor(24, 25, 28))

        if not self.has_image:
            self._draw_placeholder(painter)
            painter.end()
            return

        rect = self.image_rect()
        if self._checkerboard:
            self._draw_checkerboard(painter, rect)

        self.draw_content(painter, rect)
        painter.end()

    def draw_content(self, painter: QPainter, rect: QRectF) -> None:
        """Override di subclass. Default: gambar A bila ada, jika tidak B."""
        img = self._img_a or self._img_b
        if img is not None:
            self.paint_image(painter, img, rect, "a")

    # ------------------------------------------------------ gambar teroptimasi
    def paint_image(self, painter: QPainter, img: QImage, rect: QRectF,
                    slot: str, clip: QRectF | None = None) -> None:
        """Gambar `img` ke `rect` dengan cache pixmap / source-rect.

        `slot` hanya untuk membedakan cache antara gambar A, B, dan heatmap.
        `clip` membatasi area gambar (dipakai mode slider).
        """
        if img is None or rect.width() < 1 or rect.height() < 1:
            return

        region = QRectF(self.rect())
        if clip is not None:
            region = region.intersected(clip)
        region = region.intersected(rect)
        if region.isEmpty():
            return

        # Seluruh gambar muat di jendela? -> gambar versi ter-skala yang di-cache.
        whole_visible = (rect.width() <= self.width() + 2
                         and rect.height() <= self.height() + 2)
        if whole_visible:
            tw = max(1, int(round(rect.width())))
            th = max(1, int(round(rect.height())))
            pix = self._scaled_pixmap(img, tw, th, slot)
            painter.save()
            painter.setClipRect(clip if clip is not None else QRectF(self.rect()))
            painter.drawPixmap(rect.topLeft(), pix)
            painter.restore()
        else:
            # Zoom-in: hanya gambar bagian yang terlihat.
            iw = img.width()
            ih = img.height()
            sx = (region.left() - rect.left()) / rect.width() * iw
            sy = (region.top() - rect.top()) / rect.height() * ih
            sw = region.width() / rect.width() * iw
            sh = region.height() / rect.height() * ih
            painter.drawImage(region, img, QRectF(sx, sy, sw, sh))

    def _scaled_pixmap(self, img: QImage, tw: int, th: int, slot: str) -> QPixmap:
        entry = self._pix_cache.get(slot)
        if entry is not None and entry[0] == tw and entry[1] == th:
            return entry[2]
        ratio = tw / max(1, img.width())
        tmode = (Qt.TransformationMode.SmoothTransformation if ratio >= 0.5
                 else Qt.TransformationMode.FastTransformation)
        pix = QPixmap.fromImage(img).scaled(
            tw, th, Qt.AspectRatioMode.IgnoreAspectRatio, tmode
        )
        self._pix_cache[slot] = (tw, th, pix)
        return pix

    def _draw_placeholder(self, painter: QPainter) -> None:
        painter.setPen(QColor(120, 124, 130))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                         "Belum ada gambar\n(No image)")

    def _draw_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        if self._checker_brush is None:
            tile = 16
            pm = QPixmap(tile * 2, tile * 2)
            pm.fill(QColor(150, 150, 150))
            p = QPainter(pm)
            p.fillRect(0, 0, tile, tile, QColor(200, 200, 200))
            p.fillRect(tile, tile, tile, tile, QColor(200, 200, 200))
            p.end()
            self._checker_brush = QBrush(pm)
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, self._checker_brush)
        painter.restore()

    # --------------------------------------------------------------- helpers
    def draw_label(self, painter: QPainter, text: str, pos: QPointF,
                   color: QColor = QColor(255, 255, 255, 220)) -> None:
        """Gambar label kecil dengan latar semi transparan."""
        painter.save()
        painter.setFont(self._label_font)
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(text) + 12
        th = metrics.height() + 6
        rect = QRectF(pos.x(), pos.y(), tw, th)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()
