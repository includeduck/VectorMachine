"""Tests for UI panels, main window, and widget interactions."""

import time
from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

import src.ui.compute_worker as compute_worker
from src.core.computation import compute_curl, compute_divergence, parse_expression
from src.core.compute_process import get_compute_process
from src.ui.app_window import VectorMachineWindow
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.ui.visualization_panel import VisualizationPanel
from src.ui.visualization_worker import VisualizationWorker
from tests.slow_helpers import slow_compute


class TestInputPanel:
    """Test suite for user input handling and syntax validation."""

    def test_input_valid_field(self, qapp):
        panel = InputPanel()
        panel.set_texts("x", "y", "z")
        assert panel.is_valid()
        p, q, r = panel.get_expressions()
        assert p is not None and q is not None and r is not None
        panel.deleteLater()
        qapp.processEvents()

    def test_input_invalidation_on_syntax_error(self, qapp):
        panel = InputPanel()
        panel.set_texts("x", "y", "z")
        assert panel.is_valid()

        panel.p_input.setText("x+")
        panel.do_validate_inputs()
        assert not panel.is_valid()
        assert panel.get_expressions() == (None, None, None)
        panel.deleteLater()
        qapp.processEvents()

    def test_input_clearing(self, qapp):
        panel = InputPanel()
        panel.set_texts("x", "y", "z")
        assert panel.is_valid()

        panel.set_texts("", "", "")
        assert panel.p_input.text() == ""
        assert not panel.is_valid()
        panel.deleteLater()
        qapp.processEvents()


class TestResultsPanel:
    """Test suite for computation results formatting and display."""

    def test_display_divergence_html(self, qapp, radial_field):
        p, q, r = radial_field
        div = compute_divergence(p, q, r)

        panel = ResultsPanel()
        panel.display_divergence(div)
        html = panel.results_text.toHtml()
        assert "Divergence" in html
        assert "3" in html
        panel.deleteLater()
        qapp.processEvents()

    def test_display_curl_html(self, qapp, rotational_field):
        p, q, r = rotational_field
        curl = compute_curl(p, q, r)

        panel = ResultsPanel()
        panel.display_curl(curl)
        html = panel.results_text.toHtml()
        assert "Curl" in html
        assert "2" in html
        panel.deleteLater()
        qapp.processEvents()

    def test_clear_results(self, qapp, radial_field):
        p, q, r = radial_field
        div = compute_divergence(p, q, r)

        panel = ResultsPanel()
        panel.display_divergence(div)
        panel.clear_results()
        assert panel.results_text.toPlainText().strip() == ""
        panel.deleteLater()
        qapp.processEvents()


class TestVisualizationPanel:
    """Test suite for the visualization panel and offscreen render fallback."""

    def test_clear_plot(self, qapp, radial_field):
        p, q, r = radial_field
        panel = VisualizationPanel()
        panel.set_expressions(p, q, r)
        assert panel.p_expr is not None

        panel.clear_plot()
        assert panel.p_expr is None
        assert panel.q_expr is None
        assert panel.r_expr is None
        panel.deleteLater()
        qapp.processEvents()

    def test_zero_first_component_still_plots(self, qapp):
        # A SymPy zero is falsy; F = <0, x, 0> used to skip plotting entirely.
        p, q, r = (parse_expression(text)[0] for text in ("0", "x", "0"))
        panel = VisualizationPanel()
        panel._vtk_initialized = True
        panel.plotter = MagicMock()
        panel.p_expr, panel.q_expr, panel.r_expr = p, q, r

        panel._do_update_plot()
        worker = panel._current_worker
        assert worker is not None
        worker.wait(3000)
        qapp.processEvents()
        panel.deleteLater()
        qapp.processEvents()

    def test_scale_slider_keyboard_change_redraws(self, qapp):
        panel = VisualizationPanel()
        panel.show()
        scheduled = []
        panel.schedule_plot_update = lambda source="unknown": scheduled.append(source)

        panel.scale_slider.setFocus()
        QTest.keyClick(panel.scale_slider, Qt.Key_PageUp)
        assert panel.scale_slider.value() > 20
        assert "scale" in scheduled
        panel.deleteLater()
        qapp.processEvents()

    def test_screenshot_export(self, qapp, tmp_dir):
        panel = VisualizationPanel()
        shot_path = tmp_dir / "viewport.png"
        ok = panel.export_screenshot(str(shot_path))
        assert ok
        assert shot_path.is_file()
        assert shot_path.stat().st_size > 0
        panel.deleteLater()
        qapp.processEvents()

    def test_worker_shiboken_safety(self, qapp, radial_field):
        p, q, r = radial_field
        panel = VisualizationPanel()

        worker = VisualizationWorker(
            revision_id=1,
            p_expr=p,
            q_expr=q,
            r_expr=r,
            domain=2,
            density=3,
            scale_factor=0.2,
            is_2d=False,
            parent=panel,
        )
        panel._current_worker = worker
        worker.finished_ok.connect(panel._on_visualization_ready)
        worker.finished_err.connect(panel._on_visualization_error)
        worker.finished.connect(lambda w=worker: panel._on_worker_finished(w))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        worker.wait(3000)
        qapp.sendPostedEvents(None, 0)
        qapp.processEvents()

        # Clear plot and worker cancellation must never throw libshiboken error
        panel.clear_plot()
        panel._cancel_active_worker()
        panel.deleteLater()
        qapp.processEvents()


class TestVectorMachineWindow:
    """Test suite for VectorMachineWindow end-to-end user workflows."""

    def test_window_initialization(self, qapp):
        window = VectorMachineWindow()
        assert window.windowTitle() == "VectorMachine"
        assert not window.btn_divergence.isEnabled()
        assert not window.btn_cancel.isEnabled()
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_example_loading(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        assert window.input_panel.is_valid()
        assert window.btn_divergence.isEnabled()
        assert window.btn_curl.isEnabled()
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_interactive_computation_and_cancel(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()

        assert window._compute_in_progress
        assert window.btn_cancel.isEnabled()
        assert not window.btn_divergence.isEnabled()

        window.on_cancel_compute()
        assert not window._compute_in_progress
        assert not window.btn_cancel.isEnabled()
        assert window.btn_divergence.isEnabled()

        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_stale_worker_signal_does_not_clobber_active_compute(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()
        stale_worker = window._compute_worker
        window.on_cancel_compute()
        window.on_compute_divergence()
        active_worker = window._compute_worker
        assert active_worker is not stale_worker

        # The cancelled worker's result arrives after its replacement started.
        stale_worker.finished_ok.emit("divergence", {"stale": True})
        assert window._compute_in_progress
        assert window._compute_worker is active_worker
        assert window.last_div_steps is None

        for _ in range(300):
            qapp.processEvents()
            if window.last_div_steps is not None:
                break
            time.sleep(0.01)
        assert window.last_div_steps is not None
        assert window.last_div_steps["final"] == "3"
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_panel_keeps_both_results_after_curl(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x*y", "y*z", "z*x")
        P, Q, R = window.input_panel.get_expressions()
        for compute_type, func in (("divergence", compute_divergence), ("curl", compute_curl)):
            window._active_compute_revision = window._input_revision
            window._on_compute_finished(compute_type, func(P, Q, R))

        # PDF/PNG export captures this panel, so it must match TXT/MD output.
        text = window.results_panel.results_text.toPlainText()
        assert "Divergence" in text
        assert "Curl" in text
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_close_stops_running_computation(self, qapp, monkeypatch):
        monkeypatch.setitem(compute_worker._COMPUTATIONS, "divergence", slow_compute)
        process = get_compute_process()
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()
        worker = window._compute_worker
        deadline = time.monotonic() + 15
        while process._busy_job is not worker and time.monotonic() < deadline:
            time.sleep(0.02)
        assert process._busy_job is worker
        child = process._process

        started = time.monotonic()
        window.close()
        assert time.monotonic() - started < 5
        assert not worker.isRunning()
        assert not child.is_alive()
        window.deleteLater()
        qapp.processEvents()

    def test_stale_computation_discarded_on_input_edit(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()

        # Edit input while compute is running
        window.input_panel.p_input.setText("x**2")
        for _ in range(50):
            qapp.processEvents()
            time.sleep(0.01)

        # Stale results must be discarded
        assert window.last_div_steps is None
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_clear_flow_resets_state(self, qapp):
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_clear()

        assert window.input_panel.p_input.text() == ""
        assert not window.input_panel.is_valid()
        assert window.last_div_steps is None
        assert window.last_curl_steps is None
        assert not window.btn_divergence.isEnabled()

        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_theme_selection(self, qapp):
        window = VectorMachineWindow()
        for theme in ("dark", "light", "system"):
            window.apply_theme(theme)
            assert window._current_theme == theme
        window.close()
        window.deleteLater()
        qapp.processEvents()
