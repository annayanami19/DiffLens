"""Jendela utama aplikasi DiffLens.

Merangkai: toolbar, menu, panel gambar (kiri), panel metrik (kanan),
stacked view untuk tiap mode, drag & drop, ekspor, dan dwibahasa.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

from PIL import Image
from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt, QTimer, Slot
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .config import (
    APP_NAME,
    APP_TITLE,
    DEFAULT_SETTINGS,
    FILE_DIALOG_FILTER,
    FIT_TO_A,
    FIT_TO_B,
    FIT_TO_LARGEST,
    ICON_ICO,
    ICON_PNG,
    MODE_BLINK,
    MODE_DIFF,
    MODE_OVERLAY,
    MODE_SIDE,
    MODE_SLIDER,
    MODES,
    SCALE_CONTAIN,
    SCALE_STRETCH,
    Settings,
    stylesheet,
)
from .diff import (
    DiffResult,
    diff_side_by_side,
    make_heatmap,
    slider_composite,
)
from .i18n import get_language, set_language, tr
from .image_utils import (
    LoadedImage,
    human_size,
    load_image,
    pil_to_qimage,
)
from .views import (
    BlinkCompareView,
    DiffHeatmapView,
    OverlayCompareView,
    SideBySideView,
    SliderCompareView,
)
from .workers import DiffService, MatchService


def _load_app_icon():
    """Muat QIcon aplikasi dari file .ico (fallback ke .png)."""
    from PySide6.QtGui import QIcon
    for path in (ICON_ICO, ICON_PNG):
        try:
            if path.exists():
                icon = QIcon(str(path))
                if not icon.isNull():
                    return icon
        except Exception:
            pass
    return None


def _set_windows_app_id() -> None:
    """Set AppUserModelID agar taskbar Windows memakai ikon aplikasi kita,
    bukan ikon default Python."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"DiffLens.ImageComparator.1"
        )
    except Exception:
        pass


class HistogramWidget(QWidget):
    """Widget kecil untuk menampilkan histogram selisih (0..255)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hist: list[int] = []

    def set_histogram(self, hist) -> None:
        if hist is None:
            self._hist = []
        else:
            self._hist = [int(v) for v in hist]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 31, 35))
        if not self._hist:
            painter.setPen(QColor(120, 124, 130))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "-")
            painter.end()
            return

        w = self.width()
        h = self.height()
        n = len(self._hist)
        # batasi tampilan ke 0..64 (selisih besar jarang) agar terlihat
        shown = self._hist[:65]
        mx = max(shown) or 1
        bar_w = w / len(shown)
        painter.setPen(Qt.PenStyle.NoPen)
        for i, v in enumerate(shown):
            bh = int((v / mx) * (h - 4))
            painter.setBrush(QColor(76, 139, 245))
            painter.drawRect(QRectF(i * bar_w, h - bh, max(1.0, bar_w - 0.5), bh))
        painter.setPen(QPen(QColor(90, 94, 100), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        set_language(self.settings.get("language", "id"))

        self.image_a: LoadedImage | None = None
        self.image_b: LoadedImage | None = None
        self.matched_a: Image.Image | None = None
        self.matched_b: Image.Image | None = None
        self.last_result: DiffResult | None = None

        self.diff_service = DiffService(self)
        self.diff_service.resultReady.connect(self._on_diff_ready)
        self.diff_service.failed.connect(self._on_diff_failed)

        self.match_service = MatchService(self)
        self.match_service.resultReady.connect(self._on_match_ready)
        self.match_service.failed.connect(self._on_match_failed)

        # Timer penunda untuk pekerjaan berat (menyamakan ukuran gambar).
        # Menggabungkan beberapa perubahan cepat menjadi satu eksekusi.
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(120)
        self._fit_timer.timeout.connect(self._apply_fit_change)

        self._threshold_timer = QTimer(self)
        self._threshold_timer.setSingleShot(True)
        self._threshold_timer.setInterval(180)
        self._threshold_timer.timeout.connect(self.recompute)

        self.setWindowTitle(tr("app_title"))
        self.resize(1360, 860)
        self.setAcceptDrops(True)

        icon = _load_app_icon()
        if icon is not None:
            self.setWindowIcon(icon)

        self._build_views()
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_statusbar()

        # Beri lebar awal yang cukup untuk panel kiri/kanan.
        self.resizeDocks(
            [self.dock_left, self.dock_right],
            [300, 320],
            Qt.Orientation.Horizontal,
        )

        self._restore_geometry()
        self.apply_theme(self.settings.get("theme", "dark"))
        self.retranslate()
        self._update_enabled_states()
        # Samakan status tombol panel dengan kondisi nyata setelah restore.
        self._on_left_visibility(not self.dock_left.isHidden())
        self._on_right_visibility(not self.dock_right.isHidden())
        self._update_panel_toggle_text()

    # ================================================================ views
    def _build_views(self) -> None:
        self.slider_view = SliderCompareView(self)
        self.side_view = SideBySideView(self)
        self.blink_view = BlinkCompareView(self)
        self.overlay_view = OverlayCompareView(self)
        self.diff_view = DiffHeatmapView(self)

        self.slider_view.positionChanged.connect(self._on_slider_moved)
        self.blink_view.stateChanged.connect(lambda _b: None)

        self.stack = QStackedWidget(self)
        self._mode_index = {
            MODE_SLIDER: 0,
            MODE_SIDE: 1,
            MODE_BLINK: 2,
            MODE_OVERLAY: 3,
            MODE_DIFF: 4,
        }
        for view in (self.slider_view, self.side_view, self.blink_view,
                     self.overlay_view, self.diff_view):
            self.stack.addWidget(view)

    def _build_central(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.stack, 1)

        # baris kontrol mode tambahan (interval kedip / opasitas / slider)
        self.extra_bar = QWidget(container)
        self.extra_bar.setMinimumHeight(34)
        self.extra_layout = QHBoxLayout(self.extra_bar)
        self.extra_layout.setContentsMargins(0, 0, 0, 0)
        self.extra_layout.setSpacing(8)

        self.lbl_slider_hint = QLabel("", self.extra_bar)

        # kontrol kedip
        self.lbl_blink = QLabel("", self.extra_bar)
        self.spin_blink = QSpinBox(self.extra_bar)
        self.spin_blink.setRange(50, 5000)
        self.spin_blink.setSingleStep(50)
        self.spin_blink.setValue(int(self.settings.get("blink_interval_ms", 500)))
        self.spin_blink.valueChanged.connect(self._on_blink_interval)
        self.btn_blink_toggle = QPushButton("", self.extra_bar)
        self.btn_blink_toggle.clicked.connect(self._toggle_blink)

        # kontrol overlay
        self.lbl_opacity = QLabel("", self.extra_bar)
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal, self.extra_bar)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(int(self.settings.get("overlay_opacity", 50)))
        self.slider_opacity.setFixedWidth(180)
        self.slider_opacity.valueChanged.connect(self._on_opacity)

        # kontrol diff
        self.lbl_gain2 = QLabel("", self.extra_bar)
        self.spin_gain2 = QDoubleSpinBox(self.extra_bar)
        self.spin_gain2.setRange(0.5, 40.0)
        self.spin_gain2.setSingleStep(0.5)
        self.spin_gain2.setValue(float(self.settings.get("diff_gain", 4.0)))
        self.spin_gain2.valueChanged.connect(self._on_gain)

        self.chk_binary = QCheckBox("", self.extra_bar)
        self.chk_binary.toggled.connect(lambda v: self.diff_view.set_binary(v))

        for w in (self.lbl_slider_hint, self.lbl_blink, self.spin_blink,
                  self.btn_blink_toggle, self.lbl_opacity, self.slider_opacity,
                  self.lbl_gain2, self.spin_gain2, self.chk_binary):
            self.extra_layout.addWidget(w)
        self.extra_layout.addStretch(1)

        layout.addWidget(self.extra_bar)
        self.setCentralWidget(container)

    # ================================================================ docks
    def _build_docks(self) -> None:
        # ---- panel kiri: gambar ----
        self.dock_left = QDockWidget(self)
        self.dock_left.setObjectName("dockLeft")
        self.dock_left.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        # Cegah panel mengecil sampai kontennya "tenggelam".
        self.dock_left.setMinimumWidth(288)
        self.dock_left.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        left = QWidget(self.dock_left)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        # Lebar minimum: mencegah panel "tenggelam"/terpotong saat splitter digeser.
        # Bila jendela lebih sempit, QScrollArea akan menampilkan scrollbar, bukan memotong.
        left.setMinimumWidth(272)

        # grup gambar A
        self.group_a = QGroupBox(left)
        ga = QVBoxLayout(self.group_a)
        self.lbl_info_a = QLabel("", self.group_a)
        self.lbl_info_a.setWordWrap(True)
        self.lbl_info_a.setObjectName("metricName")
        self.btn_open_a = QPushButton("", self.group_a)
        self.btn_open_a.clicked.connect(self.open_a)
        ga.addWidget(self.lbl_info_a)
        ga.addWidget(self.btn_open_a)

        # grup gambar B
        self.group_b = QGroupBox(left)
        gb = QVBoxLayout(self.group_b)
        self.lbl_info_b = QLabel("", self.group_b)
        self.lbl_info_b.setWordWrap(True)
        self.lbl_info_b.setObjectName("metricName")
        self.btn_open_b = QPushButton("", self.group_b)
        self.btn_open_b.clicked.connect(self.open_b)
        gb.addWidget(self.lbl_info_b)
        gb.addWidget(self.btn_open_b)

        self.btn_swap = QPushButton("", left)
        self.btn_swap.clicked.connect(self.swap_images)

        # baris tombol: tukar + kosongkan
        row_actions = QHBoxLayout()
        row_actions.setSpacing(6)
        self.btn_clear = QPushButton("", left)
        self.btn_clear.clicked.connect(self.clear_images)
        row_actions.addWidget(self.btn_swap, 1)
        row_actions.addWidget(self.btn_clear, 1)

        self.lbl_drop = QLabel("", left)
        self.lbl_drop.setWordWrap(True)
        self.lbl_drop.setObjectName("metricName")

        # grup kanvas
        self.group_canvas = QGroupBox(left)
        gc = QVBoxLayout(self.group_canvas)
        gc.setSpacing(4)

        self.lbl_fit = QLabel("", self.group_canvas)
        self.combo_fit = QComboBox(self.group_canvas)
        self.combo_fit.addItem("", FIT_TO_LARGEST)
        self.combo_fit.addItem("", FIT_TO_A)
        self.combo_fit.addItem("", FIT_TO_B)
        idx = self.combo_fit.findData(self.settings.get("fit_mode", FIT_TO_LARGEST))
        if idx >= 0:
            self.combo_fit.setCurrentIndex(idx)
        self.combo_fit.currentIndexChanged.connect(self._on_fit_mode)

        self.lbl_scale = QLabel("", self.group_canvas)
        self.combo_scale = QComboBox(self.group_canvas)
        self.combo_scale.addItem("", SCALE_CONTAIN)
        self.combo_scale.addItem("", SCALE_STRETCH)
        sidx = self.combo_scale.findData(self.settings.get("scale_mode", SCALE_CONTAIN))
        if sidx >= 0:
            self.combo_scale.setCurrentIndex(sidx)
        self.combo_scale.currentIndexChanged.connect(self._on_scale_mode)

        self.chk_checker = QCheckBox("", self.group_canvas)
        self.chk_checker.setChecked(bool(self.settings.get("checkerboard", True)))
        self.chk_checker.toggled.connect(self._on_checkerboard)
        gc.addWidget(self.lbl_fit)
        gc.addWidget(self.combo_fit)
        gc.addWidget(self.lbl_scale)
        gc.addWidget(self.combo_scale)
        gc.addWidget(self.chk_checker)

        left_layout.addWidget(self.group_a)
        left_layout.addWidget(self.group_b)
        left_layout.addLayout(row_actions)
        left_layout.addWidget(self.group_canvas)
        left_layout.addWidget(self.lbl_drop)
        left_layout.addStretch(1)

        scroll_left = QScrollArea(self.dock_left)
        scroll_left.setWidgetResizable(True)
        scroll_left.setWidget(left)
        self.dock_left.setWidget(scroll_left)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_left)

        # ---- panel kanan: metrik ----
        self.dock_right = QDockWidget(self)
        self.dock_right.setObjectName("dockRight")
        self.dock_right.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.dock_right.setMinimumWidth(384)
        self.dock_right.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        right = QWidget(self.dock_right)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)
        right.setMinimumWidth(384)

        self.group_metrics = QGroupBox(right)
        form = QFormLayout(self.group_metrics)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.metric_labels: dict[str, QLabel] = {}
        for key in (
            "metric_changed_px", "metric_changed_pct", "metric_similarity",
            "metric_ssim", "metric_psnr", "metric_mse", "metric_rmse",
            "metric_mean", "metric_max",
        ):
            name = QLabel("", self.group_metrics)
            name.setObjectName("metricName")
            value = QLabel("-", self.group_metrics)
            value.setObjectName("metricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setMinimumWidth(116)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.metric_labels[key] = value
            form.addRow(name, value)

        self.lbl_hist = QLabel("", right)
        self.lbl_hist.setObjectName("metricName")
        self.hist_widget = HistogramWidget(right)

        # opsi diff
        self.group_diffopts = QGroupBox(right)
        df = QVBoxLayout(self.group_diffopts)
        df.setSpacing(4)
        self.lbl_threshold = QLabel("", self.group_diffopts)
        self.spin_threshold = QSpinBox(self.group_diffopts)
        self.spin_threshold.setRange(0, 255)
        self.spin_threshold.setValue(int(self.settings.get("diff_threshold", 8)))
        self.spin_threshold.valueChanged.connect(self._on_threshold)
        df.addWidget(self.lbl_threshold)
        df.addWidget(self.spin_threshold)

        self.lbl_gain = QLabel("", self.group_diffopts)
        self.spin_gain = QDoubleSpinBox(self.group_diffopts)
        self.spin_gain.setRange(0.5, 40.0)
        self.spin_gain.setSingleStep(0.5)
        self.spin_gain.setValue(float(self.settings.get("diff_gain", 4.0)))
        self.spin_gain.valueChanged.connect(self._on_gain)
        df.addWidget(self.lbl_gain)
        df.addWidget(self.spin_gain)

        self.btn_recompute = QPushButton("", right)
        self.btn_recompute.clicked.connect(self.recompute)

        self.lbl_no_data = QLabel("", right)
        self.lbl_no_data.setWordWrap(True)
        self.lbl_no_data.setObjectName("metricName")

        right_layout.addWidget(self.group_metrics)
        right_layout.addWidget(self.lbl_hist)
        right_layout.addWidget(self.hist_widget)
        right_layout.addWidget(self.group_diffopts)
        right_layout.addWidget(self.btn_recompute)
        right_layout.addWidget(self.lbl_no_data)
        right_layout.addStretch(1)

        scroll_right = QScrollArea(self.dock_right)
        scroll_right.setWidgetResizable(True)
        scroll_right.setWidget(right)
        self.dock_right.setWidget(scroll_right)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_right)

        # Sinkronkan status tombol menu saat panel ditutup lewat tombol X
        # (atau dipulihkan dari tata letak tersimpan).
        self.dock_left.visibilityChanged.connect(self._on_left_visibility)
        self.dock_right.visibilityChanged.connect(self._on_right_visibility)

    def _on_left_visibility(self, visible: bool) -> None:
        act = getattr(self, "act_show_left", None)
        if act is not None and act.isChecked() != visible:
            act.blockSignals(True)
            act.setChecked(visible)
            act.blockSignals(False)

    def _on_right_visibility(self, visible: bool) -> None:
        act = getattr(self, "act_show_right", None)
        if act is not None and act.isChecked() != visible:
            act.blockSignals(True)
            act.setChecked(visible)
            act.blockSignals(False)

    def _toggle_all_panels(self) -> None:
        """Sembunyikan kedua panel; bila sudah tersembunyi, tampilkan kembali."""
        any_visible = self._panels_visible()
        self.dock_left.setVisible(not any_visible)
        self.dock_right.setVisible(not any_visible)
        self._update_panel_toggle_text()

    def _panels_visible(self) -> bool:
        # isHidden() mencerminkan status logis (tidak bergantung jendela tampil).
        return not self.dock_left.isHidden() or not self.dock_right.isHidden()

    def _update_panel_toggle_text(self) -> None:
        key = ("menu_hide_all_panels" if self._panels_visible()
               else "menu_show_all_panels")
        self.act_hide_all_panels.setText(tr(key))

    # ================================================================ actions
    def _build_actions(self) -> None:
        menubar = self.menuBar()

        # --- File ---
        self.menu_file = menubar.addMenu("")
        self.act_open_a = QAction(self)
        self.act_open_a.setShortcut(QKeySequence("Ctrl+O"))
        self.act_open_a.triggered.connect(self.open_a)

        self.act_open_b = QAction(self)
        self.act_open_b.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.act_open_b.triggered.connect(self.open_b)

        self.act_swap = QAction(self)
        self.act_swap.setShortcut(QKeySequence("Ctrl+T"))
        self.act_swap.triggered.connect(self.swap_images)

        self.act_clear = QAction(self)
        self.act_clear.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.act_clear.triggered.connect(self.clear_images)

        self.act_export_heat = QAction(self)
        self.act_export_heat.triggered.connect(self.export_heatmap)
        self.act_export_slider = QAction(self)
        self.act_export_slider.triggered.connect(self.export_slider_composite)
        self.act_export_side = QAction(self)
        self.act_export_side.triggered.connect(self.export_side_composite)
        self.act_export_report = QAction(self)
        self.act_export_report.triggered.connect(self.export_report)

        self.act_quit = QAction(self)
        self.act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_quit.triggered.connect(self.close)

        self.menu_file.addAction(self.act_open_a)
        self.menu_file.addAction(self.act_open_b)
        self.menu_file.addAction(self.act_swap)
        self.menu_file.addAction(self.act_clear)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_export_heat)
        self.menu_file.addAction(self.act_export_slider)
        self.menu_file.addAction(self.act_export_side)
        self.menu_file.addAction(self.act_export_report)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_quit)

        # --- Tampilan ---
        self.menu_view = menubar.addMenu("")
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_actions: dict[str, QAction] = {}
        for i, mode in enumerate(MODES, start=1):
            act = QAction(self)
            act.setCheckable(True)
            act.setShortcut(QKeySequence(str(i)))
            act.triggered.connect(lambda _c=False, m=mode: self.set_mode(m))
            self.mode_group.addAction(act)
            self.menu_view.addAction(act)
            self.mode_actions[mode] = act
        self.menu_view.addSeparator()

        self.act_zoom_in = QAction(self)
        self.act_zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        self.act_zoom_in.triggered.connect(lambda: self._current_view().zoom_in())
        self.act_zoom_out = QAction(self)
        self.act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.act_zoom_out.triggered.connect(lambda: self._current_view().zoom_out())
        self.act_fit = QAction(self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.triggered.connect(lambda: self._current_view().fit())
        self.act_actual = QAction(self)
        self.act_actual.setShortcut(QKeySequence("Ctrl+1"))
        self.act_actual.triggered.connect(lambda: self._current_view().actual_size())

        self.act_checker = QAction(self)
        self.act_checker.setCheckable(True)
        self.act_checker.setChecked(bool(self.settings.get("checkerboard", True)))
        self.act_checker.toggled.connect(self._on_checkerboard)

        # --- toggle panel kiri/kanan ---
        self.act_show_left = QAction(self)
        self.act_show_left.setCheckable(True)
        self.act_show_left.setChecked(True)
        self.act_show_left.setShortcut(QKeySequence("Ctrl+Shift+1"))
        self.act_show_left.toggled.connect(
            lambda vis: self.dock_left.setVisible(vis)
        )

        self.act_show_right = QAction(self)
        self.act_show_right.setCheckable(True)
        self.act_show_right.setChecked(True)
        self.act_show_right.setShortcut(QKeySequence("Ctrl+Shift+2"))
        self.act_show_right.toggled.connect(
            lambda vis: self.dock_right.setVisible(vis)
        )

        self.act_hide_all_panels = QAction(self)
        self.act_hide_all_panels.setShortcut(QKeySequence("Ctrl+Shift+H"))
        self.act_hide_all_panels.triggered.connect(self._toggle_all_panels)

        self.menu_view.addAction(self.act_zoom_in)
        self.menu_view.addAction(self.act_zoom_out)
        self.menu_view.addAction(self.act_fit)
        self.menu_view.addAction(self.act_actual)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_checker)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_show_left)
        self.menu_view.addAction(self.act_show_right)
        self.menu_view.addAction(self.act_hide_all_panels)

        # --- Bahasa ---
        self.menu_lang = menubar.addMenu("")
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        self.act_lang_id = QAction(self)
        self.act_lang_id.setCheckable(True)
        self.act_lang_id.setChecked(get_language() == "id")
        self.act_lang_id.triggered.connect(lambda: self.set_language_ui("id"))
        self.act_lang_en = QAction(self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setChecked(get_language() == "en")
        self.act_lang_en.triggered.connect(lambda: self.set_language_ui("en"))
        self.lang_group.addAction(self.act_lang_id)
        self.lang_group.addAction(self.act_lang_en)
        self.menu_lang.addAction(self.act_lang_id)
        self.menu_lang.addAction(self.act_lang_en)

        # --- Bantuan ---
        self.menu_help = menubar.addMenu("")
        self.act_about = QAction(self)
        self.act_about.triggered.connect(self.show_about)
        self.act_shortcuts = QAction(self)
        self.act_shortcuts.triggered.connect(self.show_shortcuts)
        self.menu_help.addAction(self.act_about)
        self.menu_help.addAction(self.act_shortcuts)

        # --- toolbar ---
        tb = self.addToolBar("main")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.addAction(self.act_open_a)
        tb.addAction(self.act_open_b)
        tb.addAction(self.act_swap)
        tb.addAction(self.act_clear)
        tb.addSeparator()
        for mode in MODES:
            tb.addAction(self.mode_actions[mode])
        tb.addSeparator()
        tb.addAction(self.act_fit)
        tb.addAction(self.act_actual)
        tb.addAction(self.act_export_heat)
        tb.addSeparator()
        tb.addAction(self.act_show_left)
        tb.addAction(self.act_show_right)
        self.toolbar = tb

        self.mode_actions[self.settings.get("mode", MODE_SLIDER)].setChecked(True)
        self.set_mode(self.settings.get("mode", MODE_SLIDER))

    def _build_statusbar(self) -> None:
        self.lbl_status = QLabel("", self)
        self.statusBar().addWidget(self.lbl_status, 1)
        self.lbl_zoom = QLabel("", self)
        self.statusBar().addPermanentWidget(self.lbl_zoom)
        self.slider_view.zoomChanged.connect(self._on_zoom_changed)

    # ================================================================ i18n
    def retranslate(self) -> None:
        self.setWindowTitle(tr("app_title"))
        self.menu_file.setTitle(tr("menu_file"))
        self.menu_view.setTitle(tr("menu_view"))
        self.menu_lang.setTitle(tr("menu_language"))
        self.menu_help.setTitle(tr("menu_help"))

        self.act_open_a.setText(tr("menu_open_a"))
        self.act_open_b.setText(tr("menu_open_b"))
        self.act_swap.setText(tr("menu_swap"))
        self.act_clear.setText(tr("menu_clear"))
        self.act_export_heat.setText(tr("menu_export_heatmap"))
        self.act_export_slider.setText(tr("menu_export_slider"))
        self.act_export_side.setText(tr("menu_export_side"))
        self.act_export_report.setText(tr("menu_export_report"))
        self.act_quit.setText(tr("menu_quit"))
        self.act_zoom_in.setText(tr("menu_zoom_in"))
        self.act_zoom_out.setText(tr("menu_zoom_out"))
        self.act_fit.setText(tr("menu_fit"))
        self.act_actual.setText(tr("menu_actual"))
        self.act_checker.setText(tr("menu_checkerboard"))
        self.act_show_left.setText(tr("menu_show_left"))
        self.act_show_right.setText(tr("menu_show_right"))
        self.act_hide_all_panels.setText(tr("menu_hide_all_panels"))
        self.act_show_left.setToolTip(tr("tb_toggle_left"))
        self.act_show_right.setToolTip(tr("tb_toggle_right"))
        self._update_panel_toggle_text()
        self.act_lang_id.setText(tr("menu_lang_id"))
        self.act_lang_en.setText(tr("menu_lang_en"))
        self.act_about.setText(tr("menu_about"))
        self.act_shortcuts.setText(tr("menu_shortcuts"))

        mode_names = {
            MODE_SLIDER: "mode_slider",
            MODE_SIDE: "mode_side",
            MODE_BLINK: "mode_blink",
            MODE_OVERLAY: "mode_overlay",
            MODE_DIFF: "mode_diff",
        }
        for mode, act in self.mode_actions.items():
            act.setText(tr(mode_names[mode]))

        self.toolbar.setWindowTitle(tr("menu_tools"))
        self.dock_left.setWindowTitle(tr("panel_images"))
        self.dock_right.setWindowTitle(tr("panel_metrics"))

        self.group_a.setTitle(tr("group_image_a"))
        self.group_b.setTitle(tr("group_image_b"))
        self.group_canvas.setTitle(tr("group_canvas"))
        self.group_metrics.setTitle(tr("group_metrics"))
        self.group_diffopts.setTitle(tr("group_diff_opts"))

        self.btn_open_a.setText(tr("btn_open_a"))
        self.btn_open_b.setText(tr("btn_open_b"))
        self.btn_swap.setText(tr("btn_swap"))
        self.btn_clear.setText(tr("btn_clear"))
        self.btn_clear.setToolTip(tr("tb_clear"))
        self.lbl_drop.setText(tr("lbl_drop_hint"))
        self.lbl_fit.setText(tr("lbl_fit_mode"))
        self.chk_checker.setText(tr("chk_checkerboard"))
        self.combo_fit.setItemText(0, tr("fit_to_largest"))
        self.combo_fit.setItemText(1, tr("fit_to_a"))
        self.combo_fit.setItemText(2, tr("fit_to_b"))
        self.lbl_scale.setText(tr("lbl_scale_mode"))
        self.combo_scale.setItemText(0, tr("scale_contain"))
        self.combo_scale.setItemText(1, tr("scale_stretch"))

        self.lbl_hist.setText(tr("lbl_histogram"))
        self.lbl_threshold.setText(tr("lbl_threshold"))
        self.lbl_gain.setText(tr("lbl_gain"))
        self.btn_recompute.setText(tr("btn_recompute"))
        self.lbl_no_data.setText(tr("lbl_no_data"))

        self.lbl_slider_hint.setText(tr("lbl_slider_hint"))
        self.lbl_blink.setText(tr("lbl_blink_interval"))
        self.lbl_opacity.setText(tr("lbl_opacity"))
        self.lbl_gain2.setText(tr("lbl_gain"))
        self.chk_binary.setText(tr("mode_diff") + " (binary)")

        # nama metrik (label kiri pada form)
        metric_names = {
            "metric_changed_px": "metric_changed_px",
            "metric_changed_pct": "metric_changed_pct",
            "metric_similarity": "metric_similarity",
            "metric_ssim": "metric_ssim",
            "metric_psnr": "metric_psnr",
            "metric_mse": "metric_mse",
            "metric_rmse": "metric_rmse",
            "metric_mean": "metric_mean",
            "metric_max": "metric_max",
        }
        form: QFormLayout = self.group_metrics.layout()  # type: ignore[assignment]
        for row, key in enumerate(metric_names):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            if item and item.widget():
                item.widget().setText(tr(metric_names[key]))

        self._refresh_image_info()
        if not (self.image_a or self.image_b):
            self.lbl_status.setText(tr("status_ready"))
        self._update_extra_visibility()

    def set_language_ui(self, lang: str) -> None:
        set_language(lang)
        self.settings.set("language", lang)
        self.settings.save()
        self.act_lang_id.setChecked(lang == "id")
        self.act_lang_en.setChecked(lang == "en")
        self.retranslate()

    def apply_theme(self, theme: str) -> None:
        self.settings.set("theme", theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet(theme))

    # ================================================================ loading
    def open_a(self) -> None:
        path = self._ask_open(tr("dlg_open_a_title"), self.settings.get("last_dir", ""))
        if path:
            self._load_into("a", path)

    def open_b(self) -> None:
        path = self._ask_open(tr("dlg_open_b_title"), self.settings.get("last_dir", ""))
        if path:
            self._load_into("b", path)

    def _ask_open(self, title: str, start_dir: str) -> str:
        path, _ = QFileDialog.getOpenFileName(self, title, start_dir, FILE_DIALOG_FILTER)
        return path

    def _load_into(self, slot: str, path: str) -> None:
        try:
            loaded = load_image(path)
        except Exception as exc:
            QMessageBox.critical(self, tr("err_title"), f"{tr('err_load')}\n{exc}")
            return
        if slot == "a":
            self.image_a = loaded
        else:
            self.image_b = loaded
        self.settings.set("last_dir", os.path.dirname(path))
        self.settings.save()
        self._after_images_changed()

    def swap_images(self) -> None:
        self.image_a, self.image_b = self.image_b, self.image_a
        self._after_images_changed()

    def clear_images(self) -> None:
        """Kosongkan kedua gambar dan reset seluruh tampilan/analisis."""
        if self.image_a is None and self.image_b is None:
            return
        answer = QMessageBox.question(
            self,
            tr("confirm_clear_title"),
            tr("confirm_clear_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._do_clear()

    def _do_clear(self) -> None:
        # batalkan pekerjaan latar yang mungkin masih berjalan
        self._fit_timer.stop()
        self._threshold_timer.stop()

        self.image_a = None
        self.image_b = None
        self.matched_a = None
        self.matched_b = None
        self.last_result = None

        self._refresh_image_info()
        self._push_to_views()
        self._clear_metrics()
        self._update_enabled_states()

        # reset posisi slider ke tengah
        self.slider_view.set_position(0.5)
        self.lbl_status.setText(tr("status_cleared"))

    def _after_images_changed(self) -> None:
        self._refresh_image_info()
        self._update_enabled_states()
        if self.image_a is not None and self.image_b is not None:
            self.lbl_status.setText(tr("status_computing"))
            self._request_match()
        else:
            self.matched_a = None
            self.matched_b = None
            self._push_to_views()
            self._clear_metrics()

    def _request_match(self) -> None:
        """Minta penyamaan ukuran di thread latar (tidak membekukan UI)."""
        if self.image_a is None or self.image_b is None:
            return
        fit_mode = self.combo_fit.currentData()
        scale_mode = (self.combo_scale.currentData()
                      if hasattr(self, "combo_scale") else SCALE_CONTAIN)
        self.match_service.compute(self.image_a, self.image_b, fit_mode, scale_mode)

    @Slot(object, object)
    def _on_match_ready(self, matched_a: object, matched_b: object) -> None:
        self.matched_a = matched_a   # type: ignore[assignment]
        self.matched_b = matched_b   # type: ignore[assignment]
        self._push_to_views()
        self._update_enabled_states()
        self.recompute()

    @Slot(str)
    def _on_match_failed(self, message: str) -> None:
        self.lbl_status.setText(tr("err_title"))
        QMessageBox.warning(self, tr("err_title"), message)

    def _push_to_views(self) -> None:
        qa = qb = None
        if self.matched_a is not None:
            qa = pil_to_qimage(self.matched_a)
        if self.matched_b is not None:
            qb = pil_to_qimage(self.matched_b)
        checker = self.chk_checker.isChecked()
        for view in (self.slider_view, self.side_view, self.blink_view, self.overlay_view):
            view.set_checkerboard(checker)
        self.slider_view.set_images(qa, qb)
        self.side_view.set_images(qa, qb)
        self.blink_view.set_images(qa, qb)
        self.overlay_view.set_images(qa, qb)

    def _refresh_image_info(self) -> None:
        self.lbl_info_a.setText(self._describe(self.image_a, "A"))
        self.lbl_info_b.setText(self._describe(self.image_b, "B"))

    def _describe(self, img: LoadedImage | None, slot: str) -> str:
        if img is None:
            return f"{slot}: {tr('lbl_none')}"
        return (f"{slot}: {img.name}\n"
                f"{img.width} x {img.height} px  |  {img.mode}  |  {human_size(img.file_size)}")

    # ================================================================ diff
    def recompute(self) -> None:
        if self.matched_a is None or self.matched_b is None:
            return
        self.lbl_status.setText(tr("status_computing"))
        self.diff_service.compute(
            self.matched_a, self.matched_b, int(self.spin_threshold.value())
        )

    @Slot(object)
    def _on_diff_ready(self, result: object) -> None:
        assert isinstance(result, DiffResult)
        self.last_result = result
        self.diff_view.set_magnitude(result.magnitude)
        self.diff_view.set_gain(self.spin_gain.value())
        self.diff_view.set_threshold(self.spin_threshold.value())
        self._update_metrics(result)
        self.lbl_status.setText(tr("status_done"))
        self.lbl_no_data.setVisible(False)

    @Slot(str)
    def _on_diff_failed(self, message: str) -> None:
        self.lbl_status.setText(tr("err_title"))
        QMessageBox.warning(self, tr("err_title"), message)

    def _update_metrics(self, r: DiffResult) -> None:
        vals = {
            "metric_changed_px": f"{r.changed_pixels:,}".replace(",", "."),
            "metric_changed_pct": f"{r.changed_percent:.3f} %",
            "metric_similarity": f"{r.similarity_percent:.2f} %",
            "metric_ssim": f"{r.ssim:.5f}",
            "metric_psnr": ("∞ dB" if r.psnr == float("inf") else f"{r.psnr:.2f} dB"),
            "metric_mse": f"{r.mse:.3f}",
            "metric_rmse": f"{r.rmse:.3f}",
            "metric_mean": f"{r.mean_diff:.3f}",
            "metric_max": str(r.max_diff),
        }
        for key, text in vals.items():
            self.metric_labels[key].setText(text)
        self.hist_widget.set_histogram(r.histogram)

    def _clear_metrics(self) -> None:
        for lbl in self.metric_labels.values():
            lbl.setText("-")
        self.hist_widget.set_histogram(None)
        self.diff_view.set_magnitude(None)
        self.last_result = None
        self.lbl_no_data.setVisible(True)
        self.lbl_status.setText(tr("status_ready"))

    # ================================================================ mode
    def set_mode(self, mode: str) -> None:
        if mode not in self._mode_index:
            return
        self.stack.setCurrentIndex(self._mode_index[mode])
        self.settings.set("mode", mode)
        act = self.mode_actions.get(mode)
        if act is not None and not act.isChecked():
            act.setChecked(True)
        self._update_extra_visibility()
        self._update_enabled_states()
        if mode == MODE_BLINK and self.blink_view.has_image:
            self.blink_view.start()
        else:
            self.blink_view.stop()
        self.settings.save()

    def _current_view(self):
        idx = self.stack.currentIndex()
        return self.stack.widget(idx)

    def _update_extra_visibility(self) -> None:
        mode = self.settings.get("mode", MODE_SLIDER)
        is_blink = mode == MODE_BLINK
        is_overlay = mode == MODE_OVERLAY
        is_diff = mode == MODE_DIFF
        is_slider = mode == MODE_SLIDER

        self.lbl_slider_hint.setVisible(is_slider)
        self.lbl_blink.setVisible(is_blink)
        self.spin_blink.setVisible(is_blink)
        self.btn_blink_toggle.setVisible(is_blink)
        self.lbl_opacity.setVisible(is_overlay)
        self.slider_opacity.setVisible(is_overlay)
        self.lbl_gain2.setVisible(is_diff)
        self.spin_gain2.setVisible(is_diff)
        self.chk_binary.setVisible(is_diff)
        self.btn_blink_toggle.setText(
            "⏸" if self.blink_view.is_running() else "▶"
        )

    def _update_enabled_states(self) -> None:
        has_two = self.matched_a is not None and self.matched_b is not None
        for act in (self.act_swap, self.act_export_heat, self.act_export_slider,
                    self.act_export_side, self.act_export_report):
            act.setEnabled(has_two)
        self.btn_swap.setEnabled(has_two)
        self.btn_recompute.setEnabled(has_two)
        self.spin_threshold.setEnabled(has_two)
        self.spin_gain.setEnabled(has_two)
        has_any = self.matched_a is not None or self.matched_b is not None
        for act in (self.act_fit, self.act_actual, self.act_zoom_in, self.act_zoom_out):
            act.setEnabled(has_any)
        # tombol/menu kosongkan aktif bila ada minimal satu gambar
        has_image = self.image_a is not None or self.image_b is not None
        self.act_clear.setEnabled(has_image)
        self.btn_clear.setEnabled(has_image)

    # ================================================================ handlers
    def _on_slider_moved(self, value: float) -> None:
        pass

    def _on_fit_mode(self) -> None:
        self.settings.set("fit_mode", self.combo_fit.currentData())
        self.settings.save()
        # Tunda agar perubahan cepat (klik bolak-balik) tidak menumpuk beban.
        self.lbl_status.setText(tr("status_computing"))
        self._fit_timer.start()

    def _on_scale_mode(self) -> None:
        self.settings.set("scale_mode", self.combo_scale.currentData())
        self.settings.save()
        self.lbl_status.setText(tr("status_computing"))
        self._fit_timer.start()

    def _apply_fit_change(self) -> None:
        """Dijalankan setelah penundaan: samakan ukuran lalu perbarui tampilan."""
        if self.image_a is None or self.image_b is None:
            return
        self._request_match()

    def _on_checkerboard(self, enabled: bool) -> None:
        self.settings.set("checkerboard", bool(enabled))
        self.settings.save()
        if self.chk_checker.isChecked() != enabled:
            self.chk_checker.setChecked(enabled)
        if self.act_checker.isChecked() != enabled:
            self.act_checker.setChecked(enabled)
        for view in (self.slider_view, self.side_view, self.blink_view, self.overlay_view):
            view.set_checkerboard(enabled)

    def _on_blink_interval(self, value: int) -> None:
        self.blink_view.set_interval(value)
        self.settings.set("blink_interval_ms", value)
        self.settings.save()

    def _toggle_blink(self) -> None:
        self.blink_view.toggle_running()
        self._update_extra_visibility()

    def _on_opacity(self, value: int) -> None:
        self.overlay_view.set_opacity_percent(value)
        self.settings.set("overlay_opacity", value)
        self.settings.save()

    def _on_gain(self, value: float) -> None:
        self.diff_view.set_gain(value)
        if self.spin_gain.value() != value:
            self.spin_gain.setValue(value)
        if self.spin_gain2.value() != value:
            self.spin_gain2.setValue(value)
        self.settings.set("diff_gain", float(value))
        self.settings.save()

    def _on_threshold(self, value: int) -> None:
        self.diff_view.set_threshold(value)
        self.settings.set("diff_threshold", value)
        self.settings.save()
        if self.matched_a is not None and self.matched_b is not None:
            self.lbl_status.setText(tr("status_computing"))
            self._threshold_timer.start()

    def _on_zoom_changed(self, scale: float) -> None:
        self.lbl_zoom.setText(f"{tr('status_zoom')}: {scale * 100:.0f}%")

    # ================================================================ export
    def _require_two(self) -> bool:
        if self.matched_a is None or self.matched_b is None:
            QMessageBox.information(self, tr("err_title"), tr("err_need_two"))
            return False
        return True

    def _ask_save(self, default_name: str) -> str:
        start = os.path.join(self.settings.get("last_dir", ""), default_name)
        path, _ = QFileDialog.getSaveFileName(self, tr("dlg_export_title"), start,
                                              "PNG (*.png);;Semua file (*.*)")
        return path

    def _notify_saved(self, path: str) -> None:
        QMessageBox.information(self, tr("status_done"), tr("info_export_ok", path=path))

    def export_heatmap(self) -> None:
        if not self._require_two():
            return
        if self.last_result is None or self.last_result.magnitude is None:
            self.recompute()
            QMessageBox.information(self, tr("err_title"), tr("status_computing"))
            return
        path = self._ask_save("heatmap_diff.png")
        if not path:
            return
        heat = make_heatmap(self.last_result.magnitude, self.spin_gain.value())
        # komposit di atas gambar A agar mudah dibaca
        base = self.matched_a.convert("RGBA")
        out = Image.alpha_composite(base, heat)
        out.save(path)
        self._notify_saved(path)

    def export_slider_composite(self) -> None:
        if not self._require_two():
            return
        path = self._ask_save("slider_composite.png")
        if not path:
            return
        out = slider_composite(self.matched_a, self.matched_b,
                               self.slider_view.position())
        out.save(path)
        self._notify_saved(path)

    def export_side_composite(self) -> None:
        if not self._require_two():
            return
        path = self._ask_save("sidebyside_composite.png")
        if not path:
            return
        heat = None
        if self.last_result is not None and self.last_result.magnitude is not None:
            heat = make_heatmap(self.last_result.magnitude, self.spin_gain.value())
        if heat is not None:
            out = diff_side_by_side(self.matched_a, self.matched_b, heat)
        else:
            out = diff_side_by_side(
                self.matched_a, self.matched_b,
                Image.new("RGBA", self.matched_a.size, (0, 0, 0, 0)),
            )
        out.save(path)
        self._notify_saved(path)

    def export_report(self) -> None:
        if not self._require_two():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg_report_title"),
            os.path.join(self.settings.get("last_dir", ""), "laporan_perbedaan.txt"),
            "Text (*.txt);;Semua file (*.*)",
        )
        if not path:
            return
        r = self.last_result
        lines = []
        lines.append("=" * 60)
        lines.append(tr("app_title"))
        lines.append(f"Waktu: {datetime.now():%Y-%m-%d %H:%M:%S}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"A (original): {self.image_a.path if self.image_a else '-'}")
        lines.append(f"B (edited)  : {self.image_b.path if self.image_b else '-'}")
        lines.append(f"Kanvas      : {self.matched_a.width} x {self.matched_a.height} px")
        lines.append(f"Threshold   : {self.spin_threshold.value()}")
        lines.append("")
        if r is not None:
            lines.append("--- METRIK ---")
            lines.append(f"Total piksel        : {r.total_pixels}")
            lines.append(f"Piksel berubah      : {r.changed_pixels}")
            lines.append(f"Persentase berubah  : {r.changed_percent:.4f} %")
            lines.append(f"Tingkat kemiripan   : {r.similarity_percent:.4f} %")
            lines.append(f"SSIM ({r.ssim_source:>13}) : {r.ssim:.6f}")
            psnr = "inf" if r.psnr == float("inf") else f"{r.psnr:.4f}"
            lines.append(f"PSNR                : {psnr} dB")
            lines.append(f"MSE                 : {r.mse:.4f}")
            lines.append(f"RMSE                : {r.rmse:.4f}")
            lines.append(f"Rata-rata selisih   : {r.mean_diff:.4f}")
            lines.append(f"Selisih maksimum    : {r.max_diff}")
            lines.append(f"Rata2 per channel   : R={r.per_channel_mean[0]:.3f} "
                         f"G={r.per_channel_mean[1]:.3f} B={r.per_channel_mean[2]:.3f}")
        else:
            lines.append("(metrik belum dihitung)")
        lines.append("")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
        except OSError as exc:
            QMessageBox.critical(self, tr("err_title"), str(exc))
            return
        self._notify_saved(path)

    # ================================================================ dialogs
    def show_about(self) -> None:
        QMessageBox.about(self, tr("about_title"),
                          tr("about_text", version=__version__))

    def show_shortcuts(self) -> None:
        QMessageBox.information(self, tr("shortcuts_title"), tr("shortcuts_text"))

    # ================================================================ dnd
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            return
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                p = url.toLocalFile()
                if os.path.isfile(p):
                    paths.append(p)
        if not paths:
            return
        if len(paths) >= 2:
            self._load_into("a", paths[0])
            self._load_into("b", paths[1])
        else:
            # satu file: isi slot A bila kosong, jika tidak isi B
            if self.image_a is None:
                self._load_into("a", paths[0])
            elif self.image_b is None:
                self._load_into("b", paths[0])
            else:
                self._load_into("a", paths[0])
        event.acceptProposedAction()

    # ================================================================ keys
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            if self.settings.get("mode") == MODE_BLINK:
                self._toggle_blink()
                event.accept()
                return
        super().keyPressEvent(event)

    # ================================================================ geometry
    def _restore_geometry(self) -> None:
        geo = self.settings.get("window_geometry")
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
            except Exception:
                pass
        state = self.settings.get("window_state")
        if state:
            try:
                self.restoreState(QByteArray.fromBase64(state.encode("ascii")))
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        try:
            self.settings.set(
                "window_geometry",
                bytes(self.saveGeometry().toBase64()).decode("ascii"),
            )
            self.settings.set(
                "window_state",
                bytes(self.saveState().toBase64()).decode("ascii"),
            )
            self.settings.save()
        except Exception:
            pass
        self.blink_view.stop()
        super().closeEvent(event)


def run() -> int:
    _set_windows_app_id()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)
    app.setDesktopFileName("DiffLens")
    icon = _load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    settings = Settings()
    window = MainWindow(settings)
    window.show()
    return app.exec()
