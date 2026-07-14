import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QFileDialog, QMessageBox, QMenuBar, QMenu)
from PySide6.QtGui import QAction
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.core.computation import compute_divergence, compute_curl
from src.core.session import save_session, load_session

class VectorMachineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VectorMachine")
        self.resize(800, 600)
        
        self.setup_ui()
        self.create_menus()
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        
        # Left Panel (Input and Controls)
        left_layout = QVBoxLayout()
        self.input_panel = InputPanel()
        left_layout.addWidget(self.input_panel)
        
        # Buttons
        self.btn_divergence = QPushButton("Compute Divergence")
        self.btn_curl = QPushButton("Compute Curl")
        self.btn_clear = QPushButton("Clear")
        
        left_layout.addWidget(self.btn_divergence)
        left_layout.addWidget(self.btn_curl)
        left_layout.addWidget(self.btn_clear)
        left_layout.addStretch()
        
        # Right Panel (Results)
        self.results_panel = ResultsPanel()
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(self.results_panel, 2)
        
        # Connect signals
        self.btn_divergence.clicked.connect(self.on_compute_divergence)
        self.btn_curl.clicked.connect(self.on_compute_curl)
        self.btn_clear.clicked.connect(self.on_clear)
        self.input_panel.inputChanged.connect(self.update_buttons_state)
        
        self.update_buttons_state()
        
    def create_menus(self):
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("File")
        
        save_action = QAction("Save Session", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.on_save_session)
        file_menu.addAction(save_action)
        
        open_action = QAction("Open Session", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open_session)
        file_menu.addAction(open_action)
        
        # Examples Menu
        examples_menu = menu_bar.addMenu("Examples")
        
        ex1_action = QAction("Example 1: <x, y, z>", self)
        ex1_action.triggered.connect(lambda: self.load_example("x", "y", "z"))
        examples_menu.addAction(ex1_action)
        
        ex2_action = QAction("Example 2: <y*z, x**2, sin(x)>", self)
        ex2_action.triggered.connect(lambda: self.load_example("y*z", "x**2", "sin(x)"))
        examples_menu.addAction(ex2_action)
        
        ex3_action = QAction("Example 3: <exp(x*y), ln(z), x*z>", self)
        ex3_action.triggered.connect(lambda: self.load_example("exp(x*y)", "ln(z)", "x*z"))
        examples_menu.addAction(ex3_action)
        
    def update_buttons_state(self):
        is_valid = self.input_panel.is_valid()
        self.btn_divergence.setEnabled(is_valid)
        self.btn_curl.setEnabled(is_valid)
        
    def on_compute_divergence(self):
        P, Q, R = self.input_panel.get_expressions()
        if P is None:
            return
            
        try:
            steps = compute_divergence(P, Q, R)
            self.results_panel.display_divergence(steps)
        except Exception as e:
            QMessageBox.critical(self, "Computation Error", str(e))
            
    def on_compute_curl(self):
        P, Q, R = self.input_panel.get_expressions()
        if P is None:
            return
            
        try:
            steps = compute_curl(P, Q, R)
            self.results_panel.display_curl(steps)
        except Exception as e:
            QMessageBox.critical(self, "Computation Error", str(e))
            
    def on_clear(self):
        self.input_panel.set_texts("", "", "")
        self.results_panel.clear_results()
        
    def load_example(self, p_str, q_str, r_str):
        self.input_panel.set_texts(p_str, q_str, r_str)
        self.results_panel.clear_results()
        
    def on_save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Session", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        p, q, r = self.input_panel.get_texts()
        save_session(file_path, p, q, r)
        QMessageBox.information(self, "Session Saved", f"Session saved successfully to {file_path}.")
        
    def on_open_session(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Session", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        data, error = load_session(file_path)
        if error:
            QMessageBox.critical(self, "Error Loading Session", error)
            return
            
        p = data.get("P", "")
        q = data.get("Q", "")
        r = data.get("R", "")
        
        self.input_panel.set_texts(p, q, r)
        self.results_panel.clear_results()
        QMessageBox.information(self, "Session Loaded", "Session loaded successfully.")
