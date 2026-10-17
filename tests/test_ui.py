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

    def test_empty_fields_show_no_errors(self, qapp):
        panel = InputPanel()
        errors = (panel.p_error, panel.q_error, panel.r_error)
        assert [label.text() for label in errors] == ["", "", ""]
        assert panel.preview_label.text() == "Preview: F = <_, _, _>"

        # Partially filled: still invalid, but only real errors are shown.
        panel.set_texts("x +", "", "  ")
        assert not panel.is_valid()
        assert panel.p_error.text() != ""
        assert panel.q_error.text() == "" and panel.r_error.text() == ""
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


class TestArrowScaling:
    def test_arrows_fit_their_grid_cell(self):
        import numpy as np

        from src.ui.visualization_panel import arrow_lengths

        # |F| = x**2 on a +-50 domain used to give arrows ~2500 units long.
        magnitudes = np.linspace(0, 2500, 50)
        lengths = arrow_lengths(magnitudes, spacing=2.0, scale_factor=1.0)
        assert lengths.max() == 2.0
        assert lengths.min() == 0.0

    def test_outliers_do_not_shrink_other_arrows(self):
        import numpy as np

        from src.ui.visualization_panel import arrow_lengths

        magnitudes = np.array([1.0] * 99 + [1e6])  # one sample next to a pole
        lengths = arrow_lengths(magnitudes, spacing=0.5, scale_factor=2.0)
        assert np.allclose(lengths, 1.0)

    def test_all_zero_field(self):
        import numpy as np

        from src.ui.visualization_panel import arrow_lengths

        assert (arrow_lengths(np.zeros(5), spacing=1.0, scale_factor=1.0) == 0).all()


class TestVisualizationWorkerSerialisation:
    def test_only_one_evaluation_runs_at_a_time(self, qapp, monkeypatch):
        import threading

        import src.ui.visualization_worker as visualization_worker

        real_evaluate = visualization_worker.evaluate_field
        lock = threading.Lock()
        state = {"active": 0, "peak": 0, "domains": []}

        def slow_evaluate(p, q, r, x_grid, y_grid, z_grid):
            with lock:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
                state["domains"].append(float(x_grid.max()))
            time.sleep(0.4)
            try:
                return real_evaluate(p, q, r, x_grid, y_grid, z_grid)
            finally:
                with lock:
                    state["active"] -= 1

        monkeypatch.setattr(visualization_worker, "evaluate_field", slow_evaluate)
        p, q, r = (parse_expression(text)[0] for text in ("-y", "x", "0"))
        panel = VisualizationPanel()
        panel._vtk_initialized = True
        panel.plotter = MagicMock()
        panel.p_expr, panel.q_expr, panel.r_expr = p, q, r

        panel._do_update_plot()
        deadline = time.monotonic() + 10
        while state["active"] == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert state["active"] == 1
        for domain in (6, 7, 8):  # rapid setting changes mid-evaluation
            panel.domain_spin.blockSignals(True)
            panel.domain_spin.setValue(domain)
            panel.domain_spin.blockSignals(False)
            panel._do_update_plot()

        deadline = time.monotonic() + 15
        while (panel._running_worker is not None or panel._replot_pending) and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        assert state["peak"] == 1
        # The first run, then one replot with the latest settings.
        assert state["domains"] == [5.0, 8.0]
        assert panel.plotter.add_mesh.called
        panel.deleteLater()
        qapp.processEvents()


class TestSessionLoad:
    _BOGUS_DIVERGENCE = {
        "dP_dx": "1", "dQ_dy": "1", "dR_dz": "1", "formula": "f",
        "unsimplified": "999", "final": "999",
    }
    _BOGUS_CURL = {
        key: "999" for key in (
            "dR_dy", "dQ_dz", "dP_dz", "dR_dx", "dQ_dx", "dP_dy",
            "i_comp_unsimplified", "j_comp_unsimplified", "k_comp_unsimplified",
            "i_comp", "j_comp", "k_comp", "final_i", "final_j", "final_k",
        )
    }

    def _open(self, qapp, monkeypatch, tmp_dir, p_text):
        import json

        import src.ui.app_window as app_window

        path = tmp_dir / "session.json"
        path.write_text(json.dumps({
            "P": p_text, "Q": "y", "R": "z",
            "results": {"divergence": self._BOGUS_DIVERGENCE, "curl": self._BOGUS_CURL},
        }), encoding="utf-8")
        monkeypatch.setattr(
            app_window.QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), "")
        )
        messages = []
        monkeypatch.setattr(
            app_window.QMessageBox, "information", lambda *args: messages.append(args[2])
        )
        window = VectorMachineWindow()
        window.on_open_session()
        return window, messages

    def test_saved_results_are_recomputed_not_trusted(self, qapp, monkeypatch, tmp_dir):
        window, messages = self._open(qapp, monkeypatch, tmp_dir, "x")
        deadline = time.monotonic() + 20
        while (window.last_div_steps is None or window.last_curl_steps is None) \
                and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        assert messages == ["Session loaded successfully."]
        assert window.last_div_steps["final"] == "3"
        assert window.last_curl_steps["final_i"] == "0"
        assert "999" not in window.results_panel.results_text.toPlainText()
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_results_dropped_when_field_is_invalid(self, qapp, monkeypatch, tmp_dir):
        window, messages = self._open(qapp, monkeypatch, tmp_dir, "x +")
        qapp.processEvents()
        assert "not restored" in messages[0]
        assert window.last_div_steps is None and window.last_curl_steps is None
        assert "999" not in window.results_panel.results_text.toPlainText()
        window.close()
        window.deleteLater()
        qapp.processEvents()


class TestThemeColours:
    @staticmethod
    def _contrast(a, b):
        def luminance(hex_colour):
            channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            channels = [
                c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
            ]
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        high, low = sorted((luminance(a), luminance(b)), reverse=True)
        return (high + 0.05) / (low + 0.05)

    def test_palette_text_meets_wcag_aa(self):
        from src.ui.themes import PALETTES

        backgrounds = {"dark": ("#1e1e1e", "#252526"), "light": ("#f3f3f3", "#ffffff")}
        for theme, palette in PALETTES.items():
            for role in ("error", "success", "warning", "muted", "accent"):
                for background in backgrounds[theme]:
                    assert self._contrast(palette[role], background) >= 4.5, (theme, role)
            assert self._contrast(palette["plot_foreground"], palette["plot_background"]) >= 4.5

    def test_results_follow_theme_and_pdf_uses_light_accent(self, qapp, radial_field):
        from src.ui.themes import PALETTES

        window = VectorMachineWindow()
        window.results_panel.display_divergence(compute_divergence(*radial_field))
        dark, light = PALETTES["dark"]["accent"], PALETTES["light"]["accent"]

        window.apply_theme("dark")
        assert dark in window.results_panel.results_text.toHtml()
        window.apply_theme("light")
        assert light in window.results_panel.results_text.toHtml()
        window.apply_theme("dark")
        # Exported PDFs are white pages, whatever the on-screen theme.
        exported = window.results_panel.export_html()
        assert light in exported and dark not in exported
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_no_inline_colours_on_input_labels(self, qapp):
        panel = InputPanel()
        panel.set_texts("x", "y", "z")
        assert panel.preview_label.property("state") == "valid"
        panel.set_texts("x +", "y", "z")
        assert panel.preview_label.property("state") == "invalid"
        for label in (panel.preview_label, panel.p_error, panel.q_error, panel.r_error):
            assert label.styleSheet() == ""
        panel.deleteLater()
        qapp.processEvents()

    def test_plot_calls_match_pyvista_api(self, qapp):
        # An autospec plotter rejects calls that don't match PyVista's real
        # signatures (e.g. ``show_axes`` takes no colour argument).
        from unittest.mock import create_autospec

        import numpy as np
        import pyvista as pv

        from src.ui.themes import PALETTES

        panel = VisualizationPanel()
        panel.plotter = create_autospec(pv.Plotter, instance=True)
        panel._vtk_initialized = True
        panel.apply_palette(PALETTES["light"])
        panel.plotter.set_background.assert_called_with(PALETTES["light"]["plot_background"])

        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        vectors = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        panel._on_visualization_ready(
            panel._viz_revision, points, vectors, np.array([1.0, 1.0]), True, 1.0, 0.0
        )
        panel._on_visualization_ready(
            panel._viz_revision, np.empty((0, 3)), np.empty((0, 3)), np.empty(0), True, 1.0, 0.0
        )
        panel.clear_plot()
        assert panel.plotter.add_mesh.called and panel.plotter.add_text.called
        panel.deleteLater()
        qapp.processEvents()
