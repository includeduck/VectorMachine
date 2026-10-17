import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from src.core.debug_log import debug_log
from src.ui.themes import PALETTES
from src.ui.visualization_worker import VisualizationWorker

MAX_3D_DENSITY = 15
# The scale slider's value divided by this is the length of the longest
# arrows in grid spacings, so the default (20) makes them one spacing long.
SCALE_SLIDER_UNIT = 20.0
# Arrow lengths are relative to this percentile of |F|, so a few huge
# samples near a singularity don't shrink every other arrow to a dot.
ARROW_REFERENCE_PERCENTILE = 95


def arrow_lengths(magnitudes, spacing, scale_factor):
    """Glyph length per sample: ``|F|`` relative to a robust maximum.

    Lengths are capped at ``spacing * scale_factor`` so arrows stay inside
    their grid cell regardless of the domain or of outliers; colour still
    shows the true magnitude.
    """
    magnitudes = np.asarray(magnitudes, dtype=float)
    if magnitudes.size == 0:
        return magnitudes
    reference = float(np.percentile(magnitudes, ARROW_REFERENCE_PERCENTILE))
    if reference <= 0:
        reference = float(magnitudes.max())
    if reference <= 0:
        return np.zeros_like(magnitudes)
    return np.minimum(magnitudes / reference, 1.0) * spacing * scale_factor


class VisualizationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_expr = None
        self.q_expr = None
        self.r_expr = None
        self.plotter = None
        self.vtk_widget = None
        self._vtk_initialized = False
        self._vtk_initialization_failed = False
        self._plot_placeholder = None
        self._plot_busy = False
        self._schedule_count = 0
        self._plot_run_count = 0
        self._last_schedule_source = "init"
        self._viz_revision = 0
        self._current_worker = None
        # The thread actually executing, which can differ from
        # ``_current_worker`` once that result is no longer wanted.  At most
        # one runs at a time; a request made meanwhile replots after it.
        self._running_worker = None
        self._replot_pending = False
        self._arrow_spacing = 2 * 5 / (10 - 1)
        self._palette = PALETTES["dark"]
        self._status_label = None

        self.plot_timer = QTimer(self)
        self.plot_timer.setSingleShot(True)
        self.plot_timer.setInterval(300)
        self.plot_timer.timeout.connect(self._do_update_plot)

        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        controls_group = QGroupBox("Visualization Settings")
        controls_layout = QHBoxLayout()
        
        self.mode_group = QButtonGroup(self)
        self.radio_2d = QRadioButton("2D")
        self.radio_3d = QRadioButton("3D")
        self.radio_3d.setChecked(True)
        self.mode_group.addButton(self.radio_2d)
        self.mode_group.addButton(self.radio_3d)
        
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.radio_2d)
        controls_layout.addWidget(self.radio_3d)
        
        controls_layout.addWidget(QLabel("Domain (±):"))
        self.domain_spin = QSpinBox()
        self.domain_spin.setRange(1, 50)
        self.domain_spin.setValue(5)
        controls_layout.addWidget(self.domain_spin)
        
        controls_layout.addWidget(QLabel("Density:"))
        self.density_spin = QSpinBox()
        self.density_spin.setRange(5, 50)
        self.density_spin.setValue(10)
        self.density_spin.setToolTip(
            f"3D mode is capped at {MAX_3D_DENSITY} for performance."
        )
        controls_layout.addWidget(self.density_spin)
        
        controls_layout.addWidget(QLabel("Scale:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(int(SCALE_SLIDER_UNIT))
        self.scale_slider.setToolTip("Arrow length; the default makes the longest arrows one grid step long.")
        controls_layout.addWidget(self.scale_slider)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        self._status_label = QLabel("")
        self._status_label.setObjectName("vizStatus")
        layout.addWidget(self._status_label)

        self._plot_placeholder = QLabel("Open this tab to initialize visualization.")
        self._plot_placeholder.setAlignment(Qt.AlignCenter)
        self._plot_placeholder.setWordWrap(True)
        layout.addWidget(self._plot_placeholder)

        # Shown only after a failed VTK start (missing OpenGL driver, remote
        # desktop, ...), so the user can retry without restarting the app.
        self._retry_button = QPushButton("Retry 3D view")
        self._retry_button.setToolTip("Try to start the 3D renderer again")
        self._retry_button.hide()
        self._retry_button.clicked.connect(self.retry_vtk_initialization)
        layout.addWidget(self._retry_button, alignment=Qt.AlignCenter)

        self.radio_2d.toggled.connect(lambda checked: self.schedule_plot_update("radio_2d") if checked else None)
        self.radio_3d.toggled.connect(lambda checked: self.schedule_plot_update("radio_3d") if checked else None)
        self.domain_spin.valueChanged.connect(lambda _: self.schedule_plot_update("domain"))
        self.density_spin.valueChanged.connect(lambda _: self.schedule_plot_update("density"))
        # Keyboard, wheel and groove clicks only emit valueChanged; drags emit
        # it on every step, so those wait for sliderReleased instead.
        self.scale_slider.valueChanged.connect(
            lambda _: None if self.scale_slider.isSliderDown() else self.schedule_plot_update("scale")
        )
        self.scale_slider.sliderReleased.connect(lambda: self.schedule_plot_update("scale"))

    def export_screenshot(self, file_path: str) -> bool:
        """Export 3D viewport screenshot directly via PyVista/VTK, or fallback to QWidget.grab."""
        if self._vtk_initialized and self.plotter:
            try:
                self.plotter.screenshot(file_path)
                return True
            except Exception as e:
                debug_log(
                    "visualization_panel.py:export_screenshot",
                    "native screenshot failed, falling back to grab",
                    {"error": str(e)},
                    "E",
                )
        pixmap = self.grab()
        return pixmap.save(file_path, "PNG")

    def apply_palette(self, palette):
        """Match the 3D viewport to the application theme."""
        self._palette = palette
        if self.plotter:
            self.plotter.set_background(palette["plot_background"])
            self._add_axes()
            self.plotter.render()

    def _add_axes(self):
        # ``add_axes`` replaces any existing axes widget; ``show_axes`` (used
        # after ``clear``) just re-enables it, keeping the label colour.
        self.plotter.add_axes(color=self._palette["plot_foreground"])

    def ensure_vtk_initialized(self):
        if self._vtk_initialized:
            return True
        if self._vtk_initialization_failed:
            return False

        layout = self.layout()
        try:
            from pyvistaqt import QtInteractor

            self.vtk_widget = QtInteractor(self)
            layout.addWidget(self.vtk_widget)
            self.plotter = self.vtk_widget
            self.plotter.set_background(self._palette["plot_background"])
            self._add_axes()
            self._vtk_initialized = True
            # Hidden only once the viewport exists; hiding it first meant a
            # failure's message landed on an invisible label.
            self._plot_placeholder.hide()
            self._retry_button.hide()

            debug_log(
                "visualization_panel.py:ensure_vtk_initialized",
                "PyVista initialized lazily",
                {},
                "F",
            )
            return True
        except Exception as e:
            if self.vtk_widget is not None:
                layout.removeWidget(self.vtk_widget)
                self.vtk_widget.deleteLater()
                self.vtk_widget = None
            self.plotter = None
            self._vtk_initialization_failed = True
            self._plot_placeholder.setText(
                f"The 3D view could not start: {e}\n\n"
                "This usually means OpenGL is unavailable (missing graphics "
                "drivers, a remote desktop or a virtual machine). Results and "
                "exports still work."
            )
            self._plot_placeholder.show()
            self._retry_button.show()
            return False

    def retry_vtk_initialization(self):
        """Clear a previous failure and try to start the 3D view again."""
        self._vtk_initialization_failed = False
        self._plot_placeholder.setText("Starting the 3D view...")
        if self.ensure_vtk_initialized() and self.p_expr is not None:
            self.schedule_plot_update("retry")
        return self._vtk_initialized
        
    def set_expressions(self, P, Q, R, source="set_expressions"):
        unchanged = (P, Q, R) == (self.p_expr, self.q_expr, self.r_expr)
        self.p_expr = P
        self.q_expr = Q
        self.r_expr = R
        debug_log(
            "visualization_panel.py:set_expressions",
            "expressions updated",
            {"source": source, "unchanged": unchanged},
            "B",
        )
        self.schedule_plot_update(source)
        
    def _cancel_active_worker(self):
        worker = self._current_worker
        self._current_worker = None
        if worker is not None:
            try:
                if isValid(worker) and worker.isRunning():
                    worker.cancel()
            except (RuntimeError, ReferenceError):
                pass

    @staticmethod
    def _is_running(worker):
        try:
            return isValid(worker) and worker.isRunning()
        except (RuntimeError, ReferenceError):
            return False

    def stop_workers(self, timeout_ms=2000):
        """Cancel any pending plot and wait (bounded) for its worker to exit."""
        worker = self._running_worker
        self.plot_timer.stop()
        self._replot_pending = False
        self._cancel_active_worker()
        try:
            if worker is not None and isValid(worker):
                worker.wait(timeout_ms)
        except (RuntimeError, ReferenceError):
            pass

    def _on_worker_finished(self, worker):
        if self._current_worker is worker:
            self._current_worker = None
        if self._running_worker is worker:
            self._running_worker = None
            if self._replot_pending:
                self._replot_pending = False
                self._do_update_plot()

    def clear_plot(self):
        self.p_expr = None
        self.q_expr = None
        self.r_expr = None
        self._viz_revision += 1
        self.plot_timer.stop()
        self._replot_pending = False
        self._cancel_active_worker()
        if self._status_label:
            self._status_label.setText("")
        self._plot_busy = False
        if self.plotter:
            self.plotter.clear()
            self.plotter.show_axes()
            self.plotter.render()
        
    def schedule_plot_update(self, source="unknown"):
        self._schedule_count += 1
        self._last_schedule_source = source
        debug_log(
            "visualization_panel.py:schedule_plot_update",
            "plot update scheduled",
            {
                "source": source,
                "scheduleCount": self._schedule_count,
                "plotBusy": self._plot_busy,
                "timerActive": self.plot_timer.isActive(),
            },
            "C",
        )
        self.plot_timer.start()

    def _effective_density(self, density, is_2d):
        if is_2d:
            return density
        return min(density, MAX_3D_DENSITY)

    def _do_update_plot(self):
        # Compare against None: a SymPy zero (e.g. F = <0, x, 0>) is falsy.
        if self.p_expr is None:
            return
        # The visualization is intentionally lazy.  Input validation happens
        # on the Results tab too, so it must never spin up VTK in the
        # background merely because text was edited.
        if not self._vtk_initialized or not self.plotter:
            return

        if self._running_worker is not None and self._is_running(self._running_worker):
            # A cancelled worker keeps evaluating until it finishes, so
            # starting another would stack threads.  Drop its result and
            # replot with the latest settings once it exits.
            self._viz_revision += 1
            self._cancel_active_worker()
            self._replot_pending = True
            if self._status_label:
                self._status_label.setText("Computing vector field in background...")
            return

        self._plot_run_count += 1
        run_id = self._plot_run_count
        self._viz_revision += 1
        revision = self._viz_revision

        # Cancel prior worker whose result is no longer wanted
        self._cancel_active_worker()

        debug_log(
            "visualization_panel.py:_do_update_plot",
            "plot run started (async)",
            {"runId": run_id, "revision": revision, "source": self._last_schedule_source},
            "C",
        )

        domain = self.domain_spin.value()
        density = self._effective_density(
            self.density_spin.value(),
            self.radio_2d.isChecked(),
        )
        scale_factor = self.scale_slider.value() / SCALE_SLIDER_UNIT
        is_2d = self.radio_2d.isChecked()
        self._arrow_spacing = 2 * domain / (density - 1)

        self._plot_busy = True
        if self._status_label:
            self._status_label.setText("Computing vector field in background...")

        worker = VisualizationWorker(
            revision_id=revision,
            p_expr=self.p_expr,
            q_expr=self.q_expr,
            r_expr=self.r_expr,
            domain=domain,
            density=density,
            scale_factor=scale_factor,
            is_2d=is_2d,
            parent=self,
        )
        self._current_worker = worker
        self._running_worker = worker
        worker.finished_ok.connect(self._on_visualization_ready)
        worker.finished_err.connect(self._on_visualization_error)
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_visualization_ready(
        self, revision_id, points, vectors, magnitudes, is_2d, scale_factor, elapsed_ms
    ):
        if revision_id != self._viz_revision:
            return

        if self._current_worker is not None:
            try:
                if isValid(self._current_worker) and not self._current_worker.isRunning():
                    self._current_worker = None
            except (RuntimeError, ReferenceError):
                self._current_worker = None

        self._plot_busy = False
        if self._status_label:
            self._status_label.setText("")

        if not self._vtk_initialized or not self.plotter:
            return

        try:
            self.plotter.clear()
            self.plotter.show_axes()

            if len(points) == 0:
                self.plotter.add_text(
                    "No finite real vectors in the selected domain.",
                    position="upper_left",
                    font_size=10,
                    color=self._palette["plot_foreground"],
                )
                self.plotter.render()
                return

            import pyvista as pv

            cloud = pv.PolyData(points)
            cloud["vectors"] = vectors
            cloud["magnitude"] = magnitudes
            cloud["arrow_length"] = arrow_lengths(magnitudes, self._arrow_spacing, scale_factor)

            arrows = cloud.glyph(orient="vectors", scale="arrow_length", factor=1.0)
            self.plotter.add_mesh(
                arrows,
                scalars="magnitude",
                cmap="viridis",
                show_scalar_bar=True,
                scalar_bar_args={"color": self._palette["plot_foreground"]},
            )

            if is_2d:
                self.plotter.view_xy()
            else:
                self.plotter.view_isometric()

            self.plotter.render()

            debug_log(
                "visualization_panel.py:_on_visualization_ready",
                "plot updated (async)",
                {
                    "revision": revision_id,
                    "elapsedMs": round(elapsed_ms, 2),
                    "points": len(points),
                },
                "E",
            )
        except Exception as e:
            debug_log(
                "visualization_panel.py:_on_visualization_ready",
                "plot render error",
                {"revision": revision_id, "error": str(e)},
                "E",
            )
            QMessageBox.warning(self, "Visualization Error", str(e))

    def _on_visualization_error(self, revision_id, error_msg):
        if revision_id != self._viz_revision:
            return

        if self._current_worker is not None:
            try:
                if isValid(self._current_worker) and not self._current_worker.isRunning():
                    self._current_worker = None
            except (RuntimeError, ReferenceError):
                self._current_worker = None

        self._plot_busy = False
        if self._status_label:
            self._status_label.setText("")

        debug_log(
            "visualization_panel.py:_on_visualization_error",
            "worker error",
            {"revision": revision_id, "error": error_msg},
            "E",
        )
        QMessageBox.warning(self, "Visualization Error", error_msg)
