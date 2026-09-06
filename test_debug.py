"""Headless debug checks for VectorMachine core computation."""

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from src.core.computation import (
    clear_lambdify_cache,
    compute_curl,
    compute_divergence,
    evaluate_field,
    parse_expression,
)
from src.core.export import export_markdown, export_pdf, export_text
from src.core.session import load_session, save_session


def test_parse_and_compute():
    p, err = parse_expression("-y")
    q, err2 = parse_expression("x")
    r, err3 = parse_expression("0")
    assert err is None and err2 is None and err3 is None, (err, err2, err3)

    div = compute_divergence(p, q, r)
    assert div["final"] == "0", div

    curl = compute_curl(p, q, r)
    assert curl["final_k"] == "2", curl
    print("parse/compute: OK")


def test_expression_validation():
    valid, error = parse_expression("2sin(x) + ln(z) + x y")
    assert error is None and str(valid) == "x*y + log(z) + 2*sin(x)", (valid, error)

    for expression in ("foo", "__import__('os').system('echo unsafe')", "x; y"):
        value, error = parse_expression(expression)
        assert value is None and error, (expression, value, error)

    print("expression validation: OK")


def test_evaluate_field_cache():
    clear_lambdify_cache()
    p, _ = parse_expression("-y")
    q, _ = parse_expression("x")
    r, _ = parse_expression("0")

    x = np.linspace(-1, 1, 10)
    y = np.linspace(-1, 1, 10)
    z = np.array([0.0])
    x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing="ij")

    for _ in range(3):
        u, v, w = evaluate_field(p, q, r, x_grid, y_grid, z_grid)
        assert u.shape == x_grid.shape
        assert v.shape == x_grid.shape
        assert w.shape == x_grid.shape

    print("evaluate_field/cache: OK")


def test_session_round_trip():
    p, _ = parse_expression("x")
    q, _ = parse_expression("y")
    r, _ = parse_expression("z")
    divergence = compute_divergence(p, q, r)

    with tempfile.TemporaryDirectory() as temporary_directory:
        session_path = Path(temporary_directory) / "session.json"
        save_session(session_path, "x", "y", "z", True, divergence, None)
        data, error = load_session(session_path)
        assert error is None and data["results"]["divergence"] == divergence, error

        session_path.write_text('{"P": 5, "Q": "y", "R": "z"}', encoding="utf-8")
        data, error = load_session(session_path)
        assert data is None and "expressions" in error, error

    print("session persistence: OK")


def test_exports_accept_paths():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    p, _ = parse_expression("x")
    q, _ = parse_expression("y")
    r, _ = parse_expression("z")
    divergence = compute_divergence(p, q, r)
    curl = compute_curl(p, q, r)

    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        export_text(directory / "report.txt", "x", "y", "z", divergence, curl)
        export_markdown(directory / "report.md", "x", "y", "z", divergence, curl)
        export_pdf(directory / "report.pdf", "<h1>VectorMachine</h1>")
        for report_name in ("report.txt", "report.md", "report.pdf"):
            report = directory / report_name
            assert report.is_file() and report.stat().st_size > 0

    app.processEvents()
    print("exports: OK")


def test_input_invalidation():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from src.ui.input_panel import InputPanel

    app = QApplication.instance() or QApplication([])
    panel = InputPanel()
    panel.set_texts("x", "y", "z")
    assert panel.is_valid()

    panel.p_input.setText("x+")
    assert not panel.is_valid()
    assert panel.get_expressions() == (None, None, None)
    panel.validation_timer.stop()
    panel.deleteLater()
    app.processEvents()
    print("input invalidation: OK")


def test_stale_compute_is_discarded():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from src.ui.app_window import VectorMachineWindow

    app = QApplication.instance() or QApplication([])
    window = VectorMachineWindow()
    window.input_panel.set_texts("x", "y", "z")
    window.on_compute_divergence()
    window.input_panel.p_input.setText("x**2")

    for _ in range(100):
        app.processEvents()
        time.sleep(0.01)

    assert window.last_div_steps is None
    assert window.input_panel.is_valid()
    assert window.btn_divergence.isEnabled()
    assert not window.visualization_panel._vtk_initialized
    window.close()
    window.deleteLater()
    app.processEvents()
    print("stale compute suppression: OK")


def test_compute_worker_timeout_and_cancel():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from src.ui.app_window import VectorMachineWindow
    from src.ui.compute_worker import ComputeWorker

    app = QApplication.instance() or QApplication([])
    p, _ = parse_expression("x")
    q, _ = parse_expression("y")
    r, _ = parse_expression("z")

    # 1. Test normal execution
    worker = ComputeWorker("divergence", p, q, r, timeout_sec=5.0)
    results = []
    errors = []
    worker.finished_ok.connect(lambda t, res: results.append(res))
    worker.finished_err.connect(lambda t, err: errors.append(err))
    worker.start()
    worker.wait(3000)
    app.processEvents()
    assert len(results) == 1 and not errors, (results, errors)

    # 2. Test cancellation before finish
    worker_cancel = ComputeWorker("divergence", p, q, r, timeout_sec=5.0)
    cancelled_results = []
    worker_cancel.finished_ok.connect(lambda t, res: cancelled_results.append(res))
    worker_cancel.cancel()
    worker_cancel.start()
    worker_cancel.wait(3000)
    app.processEvents()
    assert len(cancelled_results) == 0

    # 3. Test interactive cancellation via VectorMachineWindow
    window = VectorMachineWindow()
    window.input_panel.set_texts("x", "y", "z")
    window.on_compute_divergence()
    assert window.btn_cancel.isEnabled()
    assert window._compute_in_progress
    window.on_cancel_compute()
    assert not window._compute_in_progress
    assert not window.btn_cancel.isEnabled()
    assert window.btn_divergence.isEnabled()

    window.close()
    window.deleteLater()
    app.processEvents()
    print("compute worker timeout/cancellation: OK")


def test_visualization_worker_async_evaluation():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from src.ui.visualization_panel import VisualizationPanel
    from src.ui.visualization_worker import VisualizationWorker

    app = QApplication.instance() or QApplication([])
    p, _ = parse_expression("-y")
    q, _ = parse_expression("x")
    r, _ = parse_expression("0")

    # 1. Test worker background evaluation
    worker = VisualizationWorker(
        revision_id=1,
        p_expr=p,
        q_expr=q,
        r_expr=r,
        domain=3,
        density=4,
        scale_factor=0.2,
        is_2d=False,
    )
    results = []
    errors = []
    worker.finished_ok.connect(
        lambda rev, pts, vecs, mags, is_2d, scale, elapsed: results.append(
            (rev, pts, vecs, mags, is_2d, scale)
        )
    )
    worker.finished_err.connect(lambda rev, err: errors.append(err))
    worker.start()
    worker.wait(5000)
    app.processEvents()

    assert not errors, errors
    assert len(results) == 1
    rev, pts, vecs, mags, is_2d, scale = results[0]
    assert rev == 1
    assert len(pts) == 4 * 4 * 4  # 64 grid points
    assert len(vecs) == 64
    assert len(mags) == 64
    assert not is_2d

    # 2. Test worker cancellation
    worker_cancel = VisualizationWorker(
        revision_id=2,
        p_expr=p,
        q_expr=q,
        r_expr=r,
        domain=3,
        density=4,
        scale_factor=0.2,
        is_2d=True,
    )
    cancel_results = []
    worker_cancel.finished_ok.connect(lambda *args: cancel_results.append(args))
    worker_cancel.cancel()
    worker_cancel.start()
    worker_cancel.wait(5000)
    app.processEvents()
    assert len(cancel_results) == 0

    # 3. Test screenshot export method on panel
    panel = VisualizationPanel()
    with tempfile.TemporaryDirectory() as temp_dir:
        shot_path = Path(temp_dir) / "test_shot.png"
        ok = panel.export_screenshot(str(shot_path))
        assert ok and shot_path.is_file() and shot_path.stat().st_size > 0

    panel.deleteLater()
    app.processEvents()
    print("visualization worker async & screenshot: OK")


def test_worker_lifecycle_libshiboken_safety():
    """Verify that finished/deleted QThreads don't trigger libshiboken C++ object deleted crashes."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from src.ui.app_window import VectorMachineWindow
    from src.ui.visualization_panel import VisualizationPanel
    from src.ui.visualization_worker import VisualizationWorker

    app = QApplication.instance() or QApplication([])

    # 1. Panel level lifecycle test
    p, _ = parse_expression("x")
    q, _ = parse_expression("y")
    r, _ = parse_expression("z")

    panel = VisualizationPanel()
    worker = VisualizationWorker(
        revision_id=1,
        p_expr=p,
        q_expr=q,
        r_expr=r,
        domain=3,
        density=4,
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
    app.sendPostedEvents(None, 0)
    app.processEvents()

    # Neither clear_plot nor repeated worker start/cancel should crash on deleted C++ object
    panel.clear_plot()
    worker2 = VisualizationWorker(
        revision_id=2,
        p_expr=p,
        q_expr=q,
        r_expr=r,
        domain=3,
        density=4,
        scale_factor=0.2,
        is_2d=False,
        parent=panel,
    )
    panel._current_worker = worker2
    worker2.finished_ok.connect(panel._on_visualization_ready)
    worker2.finished_err.connect(panel._on_visualization_error)
    worker2.finished.connect(lambda w=worker2: panel._on_worker_finished(w))
    worker2.finished.connect(worker2.deleteLater)
    worker2.start()
    worker2.wait(3000)
    app.sendPostedEvents(None, 0)
    app.processEvents()

    panel._cancel_active_worker()
    panel.clear_plot()
    panel.deleteLater()
    app.processEvents()

    # 2. Window level interaction test (simulating finished viz worker, clearing, and re-validating)
    window = VectorMachineWindow()
    worker_win = VisualizationWorker(
        revision_id=3,
        p_expr=p,
        q_expr=q,
        r_expr=r,
        domain=5,
        density=10,
        scale_factor=0.2,
        is_2d=False,
        parent=window.visualization_panel,
    )
    window.visualization_panel._current_worker = worker_win
    worker_win.finished_ok.connect(window.visualization_panel._on_visualization_ready)
    worker_win.finished_err.connect(window.visualization_panel._on_visualization_error)
    worker_win.finished.connect(lambda w=worker_win: window.visualization_panel._on_worker_finished(w))
    worker_win.finished.connect(worker_win.deleteLater)
    worker_win.start()
    worker_win.wait(3000)
    app.sendPostedEvents(None, 0)
    app.processEvents()

    # Now on_clear, update_state, and cancel_compute
    window.on_clear()
    app.processEvents()
    window.update_state()
    app.processEvents()

    # Compute worker cancellation/finish test
    window.input_panel.set_texts("x", "y", "z")
    window.on_compute_divergence()
    if window._compute_worker:
        window._compute_worker.wait(3000)
    app.sendPostedEvents(None, 0)
    app.processEvents()
    window.on_cancel_compute()
    window.on_clear()

    window.close()
    window.deleteLater()
    app.processEvents()
    print("worker lifecycle libshiboken safety: OK")


if __name__ == "__main__":
    test_parse_and_compute()
    test_expression_validation()
    test_evaluate_field_cache()
    test_session_round_trip()
    test_exports_accept_paths()
    test_input_invalidation()
    test_stale_compute_is_discarded()
    test_compute_worker_timeout_and_cancel()
    test_visualization_worker_async_evaluation()
    test_worker_lifecycle_libshiboken_safety()
    print("All debug tests passed.")
