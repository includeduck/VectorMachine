from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
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

from src.core.compute_process import get_compute_process
from src.core.debug_log import debug_log
from src.ui import branding, vtk_probe
from src.ui.about_dialog import AboutDialog
from src.ui.compute_controller import ComputeController
from src.ui.export_controller import FILE_FILTERS, ExportController
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.ui.session_controller import SessionController, SessionLoadError
from src.ui.theme_manager import ThemeManager
from src.ui.themes import palette_for
from src.ui.visualization_panel import VisualizationPanel

EXAMPLES = (
    ("Example 1: <x, y, z>", ("x", "y", "z")),
    ("Example 2: <y*z, x**2, sin(x)>", ("y*z", "x**2", "sin(x)")),
    ("Example 3: <exp(x*y), ln(z), x*z>", ("exp(x*y)", "ln(z)", "x*z")),
)


class VectorMachineWindow(QMainWindow):
    """Top-level window: builds the layout and menus and wires the parts.

    The work is delegated: ``compute`` runs and tracks computations,
    ``sessions`` saves and opens sessions, ``exports`` writes files and
    ``theme`` owns the theme.  The window keeps the dialogs and the results
    currently shown.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(branding.APP_NAME)
        self.setWindowIcon(branding.app_icon())
        self.resize(1000, 700)

        self.last_div_steps = None
        self.last_curl_steps = None

        self.compute = ComputeController(self)
        self.setup_ui()
        self.sessions = SessionController(self.input_panel, self.compute)
        self.exports = ExportController(
            self.input_panel,
            self.results_panel,
            self.visualization_panel,
            is_visualization_active=lambda: self.tab_widget.currentWidget() is self.visualization_panel,
        )
        self.theme = ThemeManager(self, self.results_panel, self.visualization_panel)
        self.create_menus()
        self.theme.apply(self.theme.current)

        self.compute.busyChanged.connect(lambda _busy: self._refresh_buttons())
        self.compute.resultReady.connect(self._on_compute_result)
        self.compute.failed.connect(self._on_compute_failed)
        self.input_panel.inputChanged.connect(self.update_state)
        self.update_state()

        # The OpenGL check runs on its own thread, so start it now for the
        # biggest head start; spawn the SymPy child once the window is up.
        # Neither then delays the first plot or computation.
        vtk_probe.start()
        QTimer.singleShot(0, get_compute_process().start)

    def closeEvent(self, event):
        self.compute.shutdown()
        self.visualization_panel.stop_workers()
        super().closeEvent(event)

    def apply_theme(self, theme_name):
        self.theme.apply(theme_name)

    # -- layout -------------------------------------------------------------
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

        for button in (self.btn_divergence, self.btn_curl, self.btn_cancel, self.btn_clear):
            left_layout.addWidget(button)
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
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def create_menus(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        self._add_action(file_menu, "Save Session", self.on_save_session, "Ctrl+S")
        self._add_action(file_menu, "Open Session", self.on_open_session, "Ctrl+O")
        export_menu = file_menu.addMenu("Export As...")
        for label, format_type in (
            ("Markdown (.md)", "md"),
            ("Text (.txt)", "txt"),
            ("PDF (.pdf)", "pdf"),
            ("PNG Image (.png)", "png"),
        ):
            self._add_action(export_menu, label, lambda f=format_type: self.on_export(f))

        view_menu = menu_bar.addMenu("View")
        self.theme.build_menu(view_menu.addMenu("Theme"))

        examples_menu = menu_bar.addMenu("Examples")
        for label, texts in EXAMPLES:
            self._add_action(examples_menu, label, lambda t=texts: self.load_example(*t))

        help_menu = menu_bar.addMenu("Help")
        about = self._add_action(help_menu, f"About {branding.APP_NAME}", self.on_about)
        about.setMenuRole(QAction.AboutRole)  # macOS puts it in the app menu

    def _add_action(self, menu, label, slot, shortcut=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda _checked=False: slot())
        menu.addAction(action)
        return action

    # -- state --------------------------------------------------------------
    def _refresh_buttons(self):
        busy = self.compute.is_busy
        allowed = self.input_panel.is_valid() and not busy
        self.btn_divergence.setEnabled(allowed)
        self.btn_curl.setEnabled(allowed)
        self.btn_cancel.setEnabled(busy)

    def update_state(self):
        """The field changed: invalidate results and refresh the plot."""
        self.compute.invalidate()
        self._refresh_buttons()

        had_results = self.last_div_steps is not None or self.last_curl_steps is not None
        P, Q, R = self.input_panel.get_expressions()
        if P is not None:
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

    def _on_tab_changed(self, index):
        if self.tab_widget.widget(index) is self.visualization_panel:
            self.visualization_panel.ensure_vtk_initialized()
            if self.input_panel.is_valid():
                P, Q, R = self.input_panel.get_expressions()
                self.visualization_panel.set_expressions(P, Q, R, source="tab_changed")

    # -- computation --------------------------------------------------------
    def on_compute_divergence(self):
        self.compute.start("divergence", *self.input_panel.get_expressions())

    def on_compute_curl(self):
        self.compute.start("curl", *self.input_panel.get_expressions())

    def on_cancel_compute(self):
        self.compute.cancel()
        debug_log("app_window.py:on_cancel_compute", "computation cancelled by user", {}, "A")

    def _on_compute_result(self, compute_type, result):
        if compute_type == "divergence":
            self.last_div_steps = result
        else:
            self.last_curl_steps = result
        # Render everything computed for this field, not just the latest
        # result: PDF/PNG export captures the panel, TXT/MD use both steps.
        self.results_panel.display_results(self.last_div_steps, self.last_curl_steps)
        self.tab_widget.setCurrentWidget(self.results_panel)

    def _on_compute_failed(self, compute_type, message):
        QMessageBox.critical(self, "Computation Error", message)

    # -- input --------------------------------------------------------------
    def on_clear(self):
        if self.compute.is_busy:
            self.on_cancel_compute()
        self.input_panel.set_texts("", "", "")
        self.results_panel.clear_results()
        self.visualization_panel.clear_plot()
        self.last_div_steps = None
        self.last_curl_steps = None

    def load_example(self, p_str, q_str, r_str):
        self.input_panel.set_texts(p_str, q_str, r_str)

    # -- files --------------------------------------------------------------
    def on_save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Session", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            self.sessions.save(file_path, self.last_div_steps, self.last_curl_steps)
        except OSError as error:
            QMessageBox.critical(self, "Save Error", f"Could not save session: {error}")
            return
        QMessageBox.information(self, "Session Saved", f"Session saved successfully to {file_path}.")

    def on_open_session(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Session", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            message = self.sessions.open(file_path)
        except SessionLoadError as error:
            QMessageBox.critical(self, "Error Loading Session", str(error))
            return
        QMessageBox.information(self, "Session Loaded", message)

    def on_about(self):
        AboutDialog(self, accent=palette_for(self.theme.current)["accent"]).exec()

    def on_export(self, format_type):
        if self.exports.incomplete_field():
            QMessageBox.warning(self, "Export Error", "Vector field is incomplete.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export As", "", FILE_FILTERS[format_type])
        if not file_path:
            return
        try:
            self.exports.export(format_type, file_path, self.last_div_steps, self.last_curl_steps)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e!s}")
            return
        QMessageBox.information(self, "Export Successful", f"Exported successfully to {file_path}")
