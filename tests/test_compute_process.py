"""Tests that timed-out and cancelled SymPy work is actually stopped."""

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import src.ui.compute_worker as compute_worker
from src.core.compute_process import ComputeCancelled, ComputeProcess, ComputeTimeout
from src.ui.compute_worker import ComputeWorker
from tests.slow_helpers import add, crash, fail, slow_compute

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _wait_until(predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def process():
    proc = ComputeProcess()
    yield proc
    proc.shutdown()


class TestComputeProcess:
    def test_returns_result(self, process):
        assert process.run(add, (2, 3), timeout=30) == 5

    def test_function_errors_come_back_as_runtime_error(self, process):
        with pytest.raises(RuntimeError, match="boom"):
            process.run(fail, ("boom",), timeout=30)

    def test_timeout_kills_child_and_recovers(self, process):
        process.start()
        process.run(add, (0, 0), timeout=30)  # wait until warm
        child = process._process

        started = time.monotonic()
        with pytest.raises(ComputeTimeout):
            process.run(slow_compute, (None, None, None), timeout=0.5)
        assert time.monotonic() - started < 10
        assert not child.is_alive()

        # A fresh child replaces the killed one.
        assert process.run(add, (1, 1), timeout=30) == 2

    def test_cancel_kills_running_request(self, process):
        job = object()
        outcome = []

        def run():
            try:
                process.run(slow_compute, (None, None, None), timeout=60, job=job)
            except ComputeCancelled:
                outcome.append("cancelled")

        thread = threading.Thread(target=run)
        thread.start()
        assert _wait_until(lambda: process._busy_job is job and process._ready_process is not None)
        child = process._process

        process.cancel(job)
        thread.join(10)
        assert not thread.is_alive()
        assert outcome == ["cancelled"]
        assert not child.is_alive()

    def test_crashed_child_is_an_error_not_a_cancel(self, process):
        # A crash used to surface as ComputeCancelled, so the worker emitted
        # nothing and the window stayed "computing" forever.
        with pytest.raises(RuntimeError, match="stopped unexpectedly"):
            process.run(crash, (), timeout=30)
        assert process.run(add, (2, 2), timeout=30) == 4

    def test_cancel_for_another_job_is_ignored(self, process):
        process.cancel(object())
        assert process.run(add, (4, 4), timeout=30) == 8


class TestComputeWorkerStopsWork:
    def test_cancel_stops_running_worker_promptly(self, qapp, radial_field, monkeypatch):
        monkeypatch.setitem(compute_worker._COMPUTATIONS, "divergence", slow_compute)
        proc = ComputeProcess()
        try:
            worker = ComputeWorker("divergence", *radial_field, timeout_sec=60, compute_process=proc)
            results, errors = [], []
            worker.finished_ok.connect(lambda *args: results.append(args))
            worker.finished_err.connect(lambda *args: errors.append(args))
            worker.start()
            assert _wait_until(lambda: proc._busy_job is worker and proc._ready_process is not None)

            worker.cancel()
            assert worker.wait(10000)
            qapp.processEvents()
            assert results == [] and errors == []
        finally:
            proc.shutdown()

    def test_timed_out_computation_does_not_delay_exit(self):
        # Before the child-process change, the timed-out SymPy thread kept
        # running and interpreter exit waited for it (here: 60 s).
        script = (
            "import time\n"
            "from PySide6.QtCore import QCoreApplication\n"
            "import src.ui.compute_worker as cw\n"
            "from tests.slow_helpers import slow_compute\n"
            "from src.core.computation import parse_expression\n"
            "cw._COMPUTATIONS['divergence'] = slow_compute\n"
            "app = QCoreApplication([])\n"
            "p, _ = parse_expression('x')\n"
            "worker = cw.ComputeWorker('divergence', p, p, p, timeout_sec=0.5)\n"
            "errors = []\n"
            "worker.finished_err.connect(lambda t, e: errors.append(e))\n"
            "worker.start(); worker.wait(30000); app.processEvents()\n"
            "print('timed out' if errors and 'timed out' in errors[0] else errors)\n"
        )
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
        assert "timed out" in result.stdout
        assert time.monotonic() - started < 30


class TestWindowRecoversFromEngineFailures:
    def _wait_idle(self, qapp, window, timeout=20):
        deadline = time.monotonic() + timeout
        while window._compute_in_progress and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

    def test_engine_crash_shows_error_and_unlocks(self, qapp, monkeypatch):
        import src.ui.app_window as app_window
        from src.ui.app_window import VectorMachineWindow

        monkeypatch.setitem(compute_worker._COMPUTATIONS, "divergence", crash)
        errors = []
        monkeypatch.setattr(app_window.QMessageBox, "critical", lambda *a: errors.append(a[2]))
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()
        self._wait_idle(qapp, window)

        assert not window._compute_in_progress
        assert window.btn_divergence.isEnabled()
        assert errors and "stopped unexpectedly" in errors[0]
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_worker_exiting_silently_does_not_lock_the_ui(self, qapp, monkeypatch):
        from src.ui.app_window import VectorMachineWindow

        monkeypatch.setattr(ComputeWorker, "run", lambda self: None)
        window = VectorMachineWindow()
        window.load_example("x", "y", "z")
        window.on_compute_divergence()
        self._wait_idle(qapp, window, timeout=5)

        assert not window._compute_in_progress
        assert window.btn_divergence.isEnabled()
        window.close()
        window.deleteLater()
        qapp.processEvents()
