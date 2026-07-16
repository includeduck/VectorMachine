import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QFileDialog, QMessageBox, QMenuBar, QMenu, QTabWidget)
from PySide6.QtGui import QAction
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.ui.visualization_panel import VisualizationPanel
from src.core.computation import compute_divergence, compute_curl
from src.core.session import save_session, load_session
from src.core.export import export_text, export_markdown, export_pdf

class VectorMachineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VectorMachine")
        self.resize(1000, 700)
        self.apply_theme()
        
        self.last_div_steps = None
        self.last_curl_steps = None
        
        self.setup_ui()
        self.create_menus()
        
    def apply_theme(self):
        dark_qss = """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
        QPushButton {
            background-color: #0e639c;
            color: #ffffff;
            border: none;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1177bb;
        }
        QPushButton:disabled {
            background-color: #333333;
            color: #777777;
        }
        QLineEdit, QTextEdit, QSpinBox {
            background-color: #252526;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            padding: 4px;
            border-radius: 2px;
        }
        QGroupBox {
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
        }
        QTabWidget::pane {
            border: 1px solid #3c3c3c;
        }
        QTabBar::tab {
            background: #2d2d2d;
            border: 1px solid #3c3c3c;
            padding: 6px 12px;
            color: #888888;
        }
        QTabBar::tab:selected {
            background: #1e1e1e;
            border-bottom-color: #1e1e1e;
            color: #ffffff;
        }
        """
        self.setStyleSheet(dark_qss)
        
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
        self.btn_divergence.setShortcut("Ctrl+Return")
        self.btn_divergence.setToolTip("Compute the divergence of the field (Ctrl+Return)")
        
        self.btn_curl = QPushButton("Compute Curl")
        self.btn_curl.setShortcut("Ctrl+Shift+Return")
        self.btn_curl.setToolTip("Compute the curl of the field (Ctrl+Shift+Return)")
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setShortcut("Ctrl+Del")
        self.btn_clear.setToolTip("Clear all inputs and results (Ctrl+Del)")
        
        left_layout.addWidget(self.btn_divergence)
        left_layout.addWidget(self.btn_curl)
        left_layout.addWidget(self.btn_clear)
        left_layout.addStretch()
        
        # Right Panel (Tabs for Results and Visualization)
        self.tab_widget = QTabWidget()
        self.results_panel = ResultsPanel()
        self.visualization_panel = VisualizationPanel()
        
        self.tab_widget.addTab(self.results_panel, "Results")
        self.tab_widget.addTab(self.visualization_panel, "Visualization")
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(self.tab_widget, 2)
        
        # Connect signals
        self.btn_divergence.clicked.connect(self.on_compute_divergence)
        self.btn_curl.clicked.connect(self.on_compute_curl)
        self.btn_clear.clicked.connect(self.on_clear)
        self.input_panel.inputChanged.connect(self.update_state)
        
        self.update_state()
        
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
        
        # Export Menu
        export_menu = file_menu.addMenu("Export As...")
        
        export_md = QAction("Markdown (.md)", self)
        export_md.triggered.connect(lambda: self.on_export("md"))
        export_menu.addAction(export_md)
        
        export_txt = QAction("Text (.txt)", self)
        export_txt.triggered.connect(lambda: self.on_export("txt"))
        export_menu.addAction(export_txt)
        
        export_pdf = QAction("PDF (.pdf)", self)
        export_pdf.triggered.connect(lambda: self.on_export("pdf"))
        export_menu.addAction(export_pdf)
        
        export_png = QAction("PNG Image (.png)", self)
        export_png.triggered.connect(lambda: self.on_export("png"))
        export_menu.addAction(export_png)
        
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
        
    def update_state(self):
        is_valid = self.input_panel.is_valid()
        self.btn_divergence.setEnabled(is_valid)
        self.btn_curl.setEnabled(is_valid)
        
        P, Q, R = self.input_panel.get_expressions()
        if P is not None:
            self.visualization_panel.set_expressions(P, Q, R)
        else:
            self.visualization_panel.clear_plot()
            
        # Reset computation steps when inputs change
        self.last_div_steps = None
        self.last_curl_steps = None
        
    def on_compute_divergence(self):
        P, Q, R = self.input_panel.get_expressions()
        if P is None:
            return
            
        try:
            self.last_div_steps = compute_divergence(P, Q, R)
            self.results_panel.display_divergence(self.last_div_steps)
            self.tab_widget.setCurrentWidget(self.results_panel)
        except Exception as e:
            QMessageBox.critical(self, "Computation Error", str(e))
            
    def on_compute_curl(self):
        P, Q, R = self.input_panel.get_expressions()
        if P is None:
            return
            
        try:
            self.last_curl_steps = compute_curl(P, Q, R)
            self.results_panel.display_curl(self.last_curl_steps)
            self.tab_widget.setCurrentWidget(self.results_panel)
        except Exception as e:
            QMessageBox.critical(self, "Computation Error", str(e))
            
    def on_clear(self):
        self.input_panel.set_texts("", "", "")
        self.results_panel.clear_results()
        self.visualization_panel.clear_plot()
        self.last_div_steps = None
        self.last_curl_steps = None
        
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

    def on_export(self, format_type):
        p, q, r = self.input_panel.get_texts()
        if not p or not q or not r:
            QMessageBox.warning(self, "Export Error", "Vector field is incomplete.")
            return

        filters = {
            "md": "Markdown Files (*.md)",
            "txt": "Text Files (*.txt)",
            "pdf": "PDF Files (*.pdf)",
            "png": "PNG Images (*.png)"
        }
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export As", "", filters[format_type])
        if not file_path:
            return
            
        try:
            if format_type == "txt":
                export_text(file_path, p, q, r, self.last_div_steps, self.last_curl_steps)
            elif format_type == "md":
                export_markdown(file_path, p, q, r, self.last_div_steps, self.last_curl_steps)
            elif format_type == "pdf":
                html = self.results_panel.results_text.toHtml()
                export_pdf(file_path, html)
            elif format_type == "png":
                pixmap = self.tab_widget.currentWidget().grab()
                pixmap.save(file_path, "PNG")
                
            QMessageBox.information(self, "Export Successful", f"Exported successfully to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
