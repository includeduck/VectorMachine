import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QGroupBox, QSlider, QLabel, QRadioButton, 
                               QButtonGroup, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
from src.core.computation import evaluate_field

class VisualizationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_expr = None
        self.q_expr = None
        self.r_expr = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls Group
        controls_group = QGroupBox("Visualization Settings")
        controls_layout = QHBoxLayout()
        
        # 2D/3D Mode
        self.mode_group = QButtonGroup(self)
        self.radio_2d = QRadioButton("2D")
        self.radio_3d = QRadioButton("3D")
        self.radio_3d.setChecked(True)
        self.mode_group.addButton(self.radio_2d)
        self.mode_group.addButton(self.radio_3d)
        
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.radio_2d)
        controls_layout.addWidget(self.radio_3d)
        
        # Domain bounds
        controls_layout.addWidget(QLabel("Domain (\u00B1):"))
        self.domain_spin = QSpinBox()
        self.domain_spin.setRange(1, 50)
        self.domain_spin.setValue(5)
        controls_layout.addWidget(self.domain_spin)
        
        # Density (resolution)
        controls_layout.addWidget(QLabel("Density:"))
        self.density_spin = QSpinBox()
        self.density_spin.setRange(5, 50)
        self.density_spin.setValue(10)
        controls_layout.addWidget(self.density_spin)
        
        # Scale Slider
        controls_layout.addWidget(QLabel("Scale:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(20)
        controls_layout.addWidget(self.scale_slider)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # PyVista VTK Widget
        try:
            self.vtk_widget = QtInteractor(self)
            layout.addWidget(self.vtk_widget)
            self.plotter = self.vtk_widget
            self.plotter.set_background("white")
            self.plotter.show_axes()
        except Exception as e:
            self.vtk_widget = QLabel(f"PyVista failed to initialize: {e}")
            layout.addWidget(self.vtk_widget)
            self.plotter = None
            
        # Connect signals
        self.radio_2d.toggled.connect(self.update_plot)
        self.radio_3d.toggled.connect(self.update_plot)
        self.domain_spin.valueChanged.connect(self.update_plot)
        self.density_spin.valueChanged.connect(self.update_plot)
        self.scale_slider.valueChanged.connect(self.update_plot)
        
    def set_expressions(self, P, Q, R):
        self.p_expr = P
        self.q_expr = Q
        self.r_expr = R
        self.update_plot()
        
    def clear_plot(self):
        self.p_expr = None
        self.q_expr = None
        self.r_expr = None
        if self.plotter:
            self.plotter.clear()
            self.plotter.show_axes()
            self.plotter.render()
        
    def update_plot(self):
        if not self.plotter or not self.p_expr:
            return
            
        try:
            self.plotter.clear()
            self.plotter.show_axes()
            
            domain = self.domain_spin.value()
            density = self.density_spin.value()
            scale_factor = self.scale_slider.value() / 100.0
            
            is_2d = self.radio_2d.isChecked()
            
            # Generate Grid
            x = np.linspace(-domain, domain, density)
            y = np.linspace(-domain, domain, density)
            if is_2d:
                z = np.array([0.0])
            else:
                z = np.linspace(-domain, domain, density)
                
            x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing='ij')
            
            # Evaluate Field
            u, v, w = evaluate_field(self.p_expr, self.q_expr, self.r_expr, x_grid, y_grid, z_grid)
            
            # Flatten arrays for PyVista
            points = np.c_[x_grid.ravel(), y_grid.ravel(), z_grid.ravel()]
            vectors = np.c_[u.ravel(), v.ravel(), w.ravel()]
            
            # Create a PyVista point cloud with associated vectors
            cloud = pv.PolyData(points)
            cloud["vectors"] = vectors
            
            magnitudes = np.linalg.norm(vectors, axis=1)
            cloud["magnitude"] = magnitudes
            
            # Add Arrows
            arrows = cloud.glyph(orient="vectors", scale="magnitude", factor=scale_factor)
            
            self.plotter.add_mesh(arrows, scalars="magnitude", cmap="viridis", show_scalar_bar=True)
            
            if is_2d:
                self.plotter.view_xy()
            else:
                self.plotter.view_isometric()
                
            self.plotter.render()
        except Exception as e:
            print(f"Plot error: {e}")
