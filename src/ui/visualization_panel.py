import time
import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QGroupBox, QSlider, QLabel, QRadioButton, 
                               QButtonGroup, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from src.core.computation import evaluate_field
from src.core.debug_log import debug_log

MAX_3D_DENSITY = 15

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
        self.scale_slider.setValue(20)
        controls_layout.addWidget(self.scale_slider)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        self._plot_placeholder = QLabel("Open this tab to initialize visualization.")
        self._plot_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._plot_placeholder)

        self.radio_2d.toggled.connect(lambda checked: self.schedule_plot_update("radio_2d") if checked else None)
        self.radio_3d.toggled.connect(lambda checked: self.schedule_plot_update("radio_3d") if checked else None)
        self.domain_spin.valueChanged.connect(lambda _: self.schedule_plot_update("domain"))
        self.density_spin.valueChanged.connect(lambda _: self.schedule_plot_update("density"))
        self.scale_slider.sliderReleased.connect(lambda: self.schedule_plot_update("scale"))

    def ensure_vtk_initialized(self):
        if self._vtk_initialized:
            return True
        if self._vtk_initialization_failed:
            return False

        layout = self.layout()
        try:
            from pyvistaqt import QtInteractor
            import pyvista as pv

            self._plot_placeholder.hide()
            self.vtk_widget = QtInteractor(self)
            layout.addWidget(self.vtk_widget)
            self.plotter = self.vtk_widget
            self.plotter.set_background("white")
            self.plotter.show_axes()
            self._vtk_initialized = True

            debug_log(
                "visualization_panel.py:ensure_vtk_initialized",
                "PyVista initialized lazily",
                {},
                "F",
            )
            return True
        except Exception as e:
            self._plot_placeholder.setText(f"PyVista failed to initialize: {e}")
            self.plotter = None
            self._vtk_initialization_failed = True
            return False
        
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
        
    def clear_plot(self):
        self.p_expr = None
        self.q_expr = None
        self.r_expr = None
        self.plot_timer.stop()
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
        if not self.p_expr:
            return
        # The visualization is intentionally lazy.  Input validation happens
        # on the Results tab too, so it must never spin up VTK in the
        # background merely because text was edited.
        if not self._vtk_initialized or not self.plotter:
            return

        self._plot_run_count += 1
        run_id = self._plot_run_count
        debug_log(
            "visualization_panel.py:_do_update_plot",
            "plot run started",
            {"runId": run_id, "source": self._last_schedule_source, "plotBusy": self._plot_busy},
            "C",
        )

        self._plot_busy = True
        t0 = time.perf_counter()
        try:
            self.plotter.clear()
            self.plotter.show_axes()
            
            domain = self.domain_spin.value()
            density = self._effective_density(
                self.density_spin.value(),
                self.radio_2d.isChecked(),
            )
            scale_factor = self.scale_slider.value() / 100.0
            is_2d = self.radio_2d.isChecked()
            
            x = np.linspace(-domain, domain, density)
            y = np.linspace(-domain, domain, density)
            if is_2d:
                z = np.array([0.0])
            else:
                z = np.linspace(-domain, domain, density)
                
            x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing='ij')
            
            u, v, w = evaluate_field(self.p_expr, self.q_expr, self.r_expr, x_grid, y_grid, z_grid)
            
            points = np.c_[x_grid.ravel(), y_grid.ravel(), z_grid.ravel()]
            vectors = np.c_[u.ravel(), v.ravel(), w.ravel()]

            if np.iscomplexobj(vectors):
                real_vectors = np.real(vectors)
                valid_vectors = np.isclose(np.imag(vectors), 0.0, equal_nan=False)
                valid_mask = np.all(valid_vectors, axis=1)
                vectors = real_vectors
            else:
                valid_mask = np.ones(len(vectors), dtype=bool)
            valid_mask &= np.all(np.isfinite(vectors), axis=1)

            if not np.any(valid_mask):
                self.plotter.add_text(
                    "No finite real vectors in the selected domain.",
                    position="upper_left",
                    font_size=10,
                )
                self.plotter.render()
                return

            points = points[valid_mask]
            vectors = vectors[valid_mask]
            
            import pyvista as pv
            cloud = pv.PolyData(points)
            cloud["vectors"] = vectors
            
            magnitudes = np.linalg.norm(vectors, axis=1)
            cloud["magnitude"] = magnitudes
            
            arrows = cloud.glyph(orient="vectors", scale="magnitude", factor=scale_factor)
            
            self.plotter.add_mesh(arrows, scalars="magnitude", cmap="viridis", show_scalar_bar=True)
            
            if is_2d:
                self.plotter.view_xy()
            else:
                self.plotter.view_isometric()
                
            self.plotter.render()

            elapsed_ms = (time.perf_counter() - t0) * 1000
            debug_log(
                "visualization_panel.py:_do_update_plot",
                "plot updated",
                {
                    "runId": run_id,
                    "source": self._last_schedule_source,
                    "elapsedMs": round(elapsed_ms, 2),
                    "density": density,
                    "is2d": is_2d,
                    "gridPoints": int(x_grid.size),
                },
                "E",
            )
        except Exception as e:
            debug_log(
                "visualization_panel.py:_do_update_plot",
                "plot error",
                {"runId": run_id, "error": str(e)},
                "E",
            )
            QMessageBox.warning(self, "Visualization Error", str(e))
        finally:
            self._plot_busy = False
