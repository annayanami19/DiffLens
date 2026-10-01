"""Widget view untuk berbagai mode perbandingan gambar."""

from __future__ import annotations

from .base import CompareView
from .blink import BlinkCompareView
from .diffview import DiffHeatmapView
from .overlay import OverlayCompareView
from .sidebyside import SideBySideView
from .slider import SliderCompareView

__all__ = [
    "CompareView",
    "SliderCompareView",
    "SideBySideView",
    "BlinkCompareView",
    "OverlayCompareView",
    "DiffHeatmapView",
]
