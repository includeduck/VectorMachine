from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from src.core.debug_log import debug_log
from src.core.export import export_markdown, export_pdf, export_text
from src.core.session import load_session, save_session
from src.core.settings import get_theme, set_theme
from src.ui.compute_worker import ComputeWorker
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.ui.themes import stylesheet_for
from src.ui.visualization_panel import VisualizationPanel


class VectorMachineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VectorMachine")
        self.resize(1000, 700)
        
        self.last_div_steps = None
        self.last_curl_steps = None
        self._compute_worker = None
        self._compute_in_progress = False
        self._input_revision = 0
        self._active_compute_revision = None
        self._current_theme = get_theme()
        self._theme_actions = {}
        
        self.setup_ui()
        self.create_menus()
        self.apply_theme(self._current_theme)
        
    def apply_theme(self, theme_name):
        self._current_theme = theme_name
        self.setStyleSheet(stylesheet_for(theme_name))
        for name, action in self._theme_actions.items():
            action.setChecked(name == theme_name)

        debug_log(
            "app_window.py:apply_theme",
            "theme applied",
            {"theme": theme_name},
            "G",
        )

    def _on_theme_selected(self, theme_name):
        set_theme(theme_name)
        self.apply_theme(theme_name)
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        
        left_layout = QVBoxLayout()
        self.input_panel = InputPanel()
        left_layout.addWidget(self.input_panel)
        
        self.btn_divergence = QPushButton("Compute Divergence")
        self.btn_divergence.setShortcut("Ctrl+Return")
        self.btn_divergence.setToolTip("Compute the divergence of the field (Ctrl+Return)")
        
        self.btn_curl = QPushButton("Compute Curl")
        self.btn_curl.setShortcut("Ctrl+Shift+Return")
        self.btn_curl.setToolTip("Compute the curl of the field (Ctrl+Shift+Return)")
        
        self.btn_cancel = QPushButton("Cancel Computation")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setToolTip("Cancel currently running computation")
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setShortcut("Ctrl+Del")
        self.btn_clear.setToolTip("Clear all inputs and results (Ctrl+Del)")
        
        left_layout.addWidget(self.btn_divergence)
        left_layout.addWidget(self.btn_curl)
        left_layout.addWidget(self.btn_cancel)
        left_layout.addWidget(self.btn_clear)
        left_layout.addStretch()
        
        self.tab_widget = QTabWidget()
        self.results_panel = ResultsPanel()
        self.visualization_panel = VisualizationPanel()
        
        self.tab_widget.addTab(self.results_panel, "Results")
        self.tab_widget.addTab(self.visualization_panel, "Visualization")
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(self.tab_widget, 2)
        
        self.btn_divergence.clicked.connect(self.on_compute_divergence)
        self.btn_curl.clicked.connect(self.on_compute_curl)
        self.btn_cancel.clicked.connect(self.on_cancel_compute)
        self.btn_clear.clicked.connect(self.on_clear)
        self.input_panel.inputChanged.connect(self.update_state)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        self.update_state()
        
    def _on_tab_changed(self, index):
        if self.tab_widget.widget(index) is self.visualization_panel:
            self.visualization_panel.ensure_vtk_initialized()
            if self.input_panel.is_valid():
                P, Q, R = self.input_panel.get_expressions()
                self.visualization_panel.set_expressions(P, Q, R, source="tab_changed")

    def create_menus(self):
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("File")
        
        save_action = QAction("Save Session", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.on_save_session)
        file_menu.addAction(save_action)
        
        open_action = QAction("Open Session", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open_session)
        file_menu.addAction(open_action)
        
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
        
        view_menu = menu_bar.addMenu("View")

        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        for theme_name, label in (
            ("light", "Light"),
            ("dark", "Dark"),
            ("system", "System"),
        ):
            action = QAction(label, self, checkable=True)
            action.setChecked(theme_name == self._current_theme)
            action.triggered.connect(lambda checked, t=theme_name: self._on_theme_selected(t))
            theme_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[theme_name] = action

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
        
    def _set_compute_enabled(self, enabled):
        allowed = enabled and self.input_panel.is_valid() and not self._compute_in_progress
        self.btn_divergence.setEnabled(allowed)
        self.btn_curl.setEnabled(allowed)
        self.btn_cancel.setEnabled(self._compute_in_progress)

    def update_state(self):
        self._input_revision += 1
        is_valid = self.input_panel.is_valid()
        self._set_compute_enabled(is_valid)
        
        had_results = self.last_div_steps is not None or self.last_curl_steps is not None
        P, Q, R = self.input_panel.get_expressions()
        if P is not None:
            debug_log(
                "app_window.py:update_state",
                "scheduling viz update from input change",
                {"hadResults": had_results, "valid": True},
                "B",
            )
            self.visualization_panel.set_expressions(P, Q, R, source="update_state")
        else:
            self.visualization_panel.clear_plot()
            
        self.last_div_steps = None
        self.last_curl_steps = None

        if had_results:
            self.results_panel.clear_results()
            debug_log(
                "app_window.py:update_state",
                "cleared stale results on input change",
                {"hadResults": had_results},
                "A",
            )

    def _cancel_compute_worker(self):
        worker = self._compute_worker
        self._compute_worker = None
        if worker is not None:
            try:
                if isValid(worker) and worker.isRunning():
                    worker.cancel()
            except (RuntimeError, ReferenceError):
                pass

    def _on_compute_worker_finished(self, worker):
        if self._compute_worker is worker:
            self._compute_worker = None

    def _start_compute(self, compute_type):
        P, Q, R = self.input_panel.get_expressions()
        if P is None:
            return

        if self._compute_in_progress:
            return

        self._compute_in_progress = True
        self._active_compute_revision = self._input_revision
        worker = ComputeWorker(compute_type, P, Q, R, timeout_sec=10.0, parent=self)
        self._compute_worker = worker
        worker.finished_ok.connect(self._on_compute_finished)
        worker.finished_err.connect(self._on_compute_error)
        worker.finished.connect(lambda w=worker: self._on_compute_worker_finished(w))
        worker.finished.connect(worker.deleteLater)
        self._set_compute_enabled(False)
        worker.start()

    def on_cancel_compute(self):
        self._cancel_compute_worker()
        self._compute_in_progress = False
        self._active_compute_revision = None
        self._set_compute_enabled(True)
        debug_log(
            "app_window.py:on_cancel_compute",
            "computation cancelled by user",
            {},
            "A",
        )

    def _on_compute_finished(self, compute_type, result):
        is_current = self._active_compute_revision == self._input_revision
        self._compute_in_progress = False
        self._compute_worker = None
        self._active_compute_revision = None
        self._set_compute_enabled(True)
        if not is_current:
            return
        if compute_type == "divergence":
            self.last_div_steps = result
            self.results_panel.display_divergence(result)
        else:
            self.last_curl_steps = result
            self.results_panel.display_curl(result)
        self.tab_widget.setCurrentWidget(self.results_panel)

    def _on_compute_error(self, compute_type, error_msg):
        is_current = self._active_compute_revision == self._input_revision
        self._compute_in_progress = False
        self._compute_worker = None
        self._active_compute_revision = None
        self._set_compute_enabled(True)
        if is_current:
            QMessageBox.critical(self, "Computation Error", error_msg)

    def on_compute_divergence(self):
        self._start_compute("divergence")
            
    def on_compute_curl(self):
        self._start_compute("curl")
            
    def on_clear(self):
        if self._compute_in_progress:
            self.on_cancel_compute()
        self.input_panel.set_texts("", "", "")
        self.results_panel.clear_results()
        self.visualization_panel.clear_plot()
        self.last_div_steps = None
        self.last_curl_steps = None
        
    def load_example(self, p_str, q_str, r_str):
        self.input_panel.set_texts(p_str, q_str, r_str)
        
    def on_save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Session", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        p, q, r = self.input_panel.get_texts()
        has_results = self.last_div_steps is not None or self.last_curl_steps is not None
        try:
            save_session(
                file_path, p, q, r,
                has_results=has_results,
                divergence_steps=self.last_div_steps,
                curl_steps=self.last_curl_steps,
            )
        except OSError as error:
            QMessageBox.critical(self, "Save Error", f"Could not save session: {error}")
            return
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

        results = data.get("results", {})
        self.last_div_steps = results.get("divergence")
        self.last_curl_steps = results.get("curl")

        self.results_panel.display_results(self.last_div_steps, self.last_curl_steps)

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
                if self.tab_widget.currentWidget() is self.visualization_panel:
                    if not self.visualization_panel.export_screenshot(file_path):
                        raise OSError("Could not capture 3D visualization screenshot.")
                else:
                    pixmap = self.results_panel.grab()
                    if not pixmap.save(file_path, "PNG"):
                        raise OSError("Qt could not write the PNG file.")
                
            QMessageBox.information(self, "Export Successful", f"Exported successfully to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e!s}")
