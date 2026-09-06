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
    from src.ui.compute_worker import ComputeWorker
    from src.ui.app_window import VectorMachineWindow

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
    from src.ui.visualization_worker import VisualizationWorker
    from src.ui.visualization_panel import VisualizationPanel

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
    print("All debug tests passed.")
