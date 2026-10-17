"""Unit tests for the pieces extracted from VectorMachineWindow."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMenu, QWidget

from src.core.computation import compute_divergence, parse_expression
from src.ui.compute_controller import ComputeController
from src.ui.export_controller import ExportController
from src.ui.input_panel import InputPanel
from src.ui.results_panel import ResultsPanel
from src.ui.session_controller import SessionController, SessionLoadError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# ComputeController, driven by a fake worker (no threads, fully deterministic)
# --------------------------------------------------------------------------
class FakeWorker(QObject):
    finished_ok = Signal(str, object)
    finished_err = Signal(str, str)
    finished = Signal()
    created = []

    def __init__(self, compute_type, P, Q, R, timeout_sec=10.0, parent=None):
        super().__init__(parent)
        self.compute_type = compute_type
        self.args = (P, Q, R)
        self.running = False
        self.cancelled = False
        FakeWorker.created.append(self)

    def start(self):
        self.running = True

    def isRunning(self):
        return self.running

    def cancel(self):
        self.cancelled = True

    def wait(self, timeout_ms=0):
        return True

    # Helpers that play the part of the background thread.
    def succeed(self, result="ok"):
        self.finished_ok.emit(self.compute_type, result)
        self.exit()

    def fail(self, message="boom"):
        self.finished_err.emit(self.compute_type, message)
        self.exit()

    def exit(self):
        self.running = False
        self.finished.emit()


@pytest.fixture
def controller(qapp):
    FakeWorker.created = []
    ctrl = ComputeController(worker_factory=FakeWorker)
    events = {"busy": [], "results": [], "errors": []}
    ctrl.busyChanged.connect(events["busy"].append)
    ctrl.resultReady.connect(lambda kind, result: events["results"].append((kind, result)))
    ctrl.failed.connect(lambda kind, message: events["errors"].append((kind, message)))
    ctrl.events = events
    return ctrl


FIELD = ("P", "Q", "R")  # the fake worker never evaluates them


class TestComputeController:
    def test_result_for_current_field_is_delivered(self, controller):
        assert controller.start("divergence", *FIELD)
        assert controller.is_busy
        controller.worker.succeed("3")
        assert controller.events["results"] == [("divergence", "3")]
        assert controller.events["busy"] == [True, False]
        assert controller.worker is None

    def test_ignored_while_busy_or_without_a_field(self, controller):
        assert not controller.start("divergence", None, None, None)
        controller.start("divergence", *FIELD)
        assert not controller.start("curl", *FIELD)
        assert len(FakeWorker.created) == 1

    def test_result_for_an_edited_field_is_dropped(self, controller):
        controller.start("divergence", *FIELD)
        worker = controller.worker
        controller.invalidate()  # user edited the field meanwhile
        worker.succeed("stale")
        assert controller.events["results"] == []
        assert not controller.is_busy

    def test_cancelled_workers_late_signal_is_ignored(self, controller):
        controller.start("divergence", *FIELD)
        stale = controller.worker
        controller.cancel()
        assert stale.cancelled
        controller.start("curl", *FIELD)
        active = controller.worker

        stale.succeed("late")
        assert controller.is_busy and controller.worker is active
        assert controller.events["results"] == []

        active.succeed("curl result")
        assert controller.events["results"] == [("curl", "curl result")]

    def test_sequence_runs_in_order(self, controller):
        assert controller.run_sequence(["divergence", "curl"], *FIELD)
        controller.worker.succeed("div")
        assert controller.worker.compute_type == "curl"
        assert controller.worker.args == FIELD
        controller.worker.succeed("curl")
        assert [kind for kind, _ in controller.events["results"]] == ["divergence", "curl"]
        assert not controller.is_busy

    def test_error_reports_and_drops_the_queue(self, controller):
        controller.run_sequence(["divergence", "curl"], *FIELD)
        controller.worker.fail("timed out")
        assert controller.events["errors"] == [("divergence", "timed out")]
        assert controller.worker is None and not controller.is_busy
        assert len(FakeWorker.created) == 1

    def test_invalidate_drops_the_queue(self, controller):
        controller.run_sequence(["divergence", "curl"], *FIELD)
        controller.invalidate()
        controller.worker.succeed("stale")
        assert len(FakeWorker.created) == 1

    def test_silent_worker_exit_unlocks(self, controller):
        controller.start("divergence", *FIELD)
        controller.worker.exit()  # finished without a result or an error
        assert not controller.is_busy and controller.worker is None

    def test_shutdown_cancels_the_running_worker(self, controller):
        controller.start("divergence", *FIELD)
        worker = controller.worker
        controller.shutdown()
        assert worker.cancelled and not controller.is_busy


# --------------------------------------------------------------------------
# SessionController
# --------------------------------------------------------------------------
class RecordingCompute:
    def __init__(self, busy=False):
        self.is_busy = busy
        self.cancelled = False
        self.sequences = []

    def cancel(self):
        self.cancelled = True
        self.is_busy = False

    def run_sequence(self, kinds, P, Q, R):
        self.sequences.append((list(kinds), (P, Q, R)))
        return True


def _session_file(tmp_dir, p_text="x", results=("divergence", "curl")):
    p, _ = parse_expression("x")
    div = compute_divergence(p, p, p)
    curl_keys = (
        "dR_dy", "dQ_dz", "dP_dz", "dR_dx", "dQ_dx", "dP_dy",
        "i_comp_unsimplified", "j_comp_unsimplified", "k_comp_unsimplified",
        "i_comp", "j_comp", "k_comp", "final_i", "final_j", "final_k",
    )
    saved = {
        "divergence": div if "divergence" in results else None,
        "curl": {key: "0" for key in curl_keys} if "curl" in results else None,
    }
    path = tmp_dir / "session.json"
    path.write_text(
        json.dumps({"P": p_text, "Q": "y", "R": "z", "results": saved}), encoding="utf-8"
    )
    return path


class TestSessionController:
    def test_open_recomputes_saved_results(self, qapp, tmp_dir):
        panel, compute = InputPanel(), RecordingCompute()
        message = SessionController(panel, compute).open(_session_file(tmp_dir))
        assert message == "Session loaded successfully."
        assert panel.get_texts() == ("x", "y", "z")
        kinds, field = compute.sequences[0]
        assert kinds == ["divergence", "curl"]
        assert [str(e) for e in field] == ["x", "y", "z"]

    def test_open_without_results_computes_nothing(self, qapp, tmp_dir):
        compute = RecordingCompute()
        SessionController(InputPanel(), compute).open(_session_file(tmp_dir, results=()))
        assert compute.sequences == []

    def test_invalid_field_drops_results(self, qapp, tmp_dir):
        compute = RecordingCompute()
        message = SessionController(InputPanel(), compute).open(_session_file(tmp_dir, p_text="x +"))
        assert "not restored" in message
        assert compute.sequences == []

    def test_open_cancels_a_running_computation(self, qapp, tmp_dir):
        compute = RecordingCompute(busy=True)
        SessionController(InputPanel(), compute).open(_session_file(tmp_dir))
        assert compute.cancelled

    def test_unloadable_file_raises(self, qapp, tmp_dir):
        with pytest.raises(SessionLoadError, match="does not exist"):
            SessionController(InputPanel(), RecordingCompute()).open(tmp_dir / "missing.json")

    def test_save_writes_current_field(self, qapp, tmp_dir):
        panel = InputPanel()
        panel.set_texts("x", "y", "z")
        path = tmp_dir / "saved.json"
        SessionController(panel, RecordingCompute()).save(path, None, None)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert (data["P"], data["Q"], data["R"], data["has_results"]) == ("x", "y", "z", False)


# --------------------------------------------------------------------------
# ExportController
# --------------------------------------------------------------------------
class TestExportController:
    def _controller(self, panel_texts=("x", "y", "z"), viz_active=False, screenshot_ok=True):
        panel = InputPanel()
        panel.set_texts(*panel_texts)
        results = ResultsPanel()
        viz = QWidget()
        viz.shots = []
        viz.export_screenshot = lambda path: viz.shots.append(path) or screenshot_ok
        return ExportController(panel, results, viz, lambda: viz_active), viz

    def test_incomplete_field(self, qapp):
        assert self._controller(("x", "", "z"))[0].incomplete_field()
        assert not self._controller()[0].incomplete_field()

    @pytest.mark.parametrize("format_type", ["txt", "md", "pdf", "png"])
    def test_each_format_writes_a_file(self, qapp, tmp_dir, format_type):
        controller, _ = self._controller()
        path = tmp_dir / f"out.{format_type}"
        controller.export(format_type, str(path), None, None)
        assert path.is_file() and path.stat().st_size > 0

    def test_png_from_visualization_tab_uses_the_plot(self, qapp, tmp_dir):
        controller, viz = self._controller(viz_active=True)
        controller.export("png", str(tmp_dir / "plot.png"), None, None)
        assert viz.shots == [str(tmp_dir / "plot.png")]

    def test_failed_plot_capture_raises(self, qapp, tmp_dir):
        controller, _ = self._controller(viz_active=True, screenshot_ok=False)
        with pytest.raises(OSError):
            controller.export("png", str(tmp_dir / "plot.png"), None, None)

    def test_unknown_format_raises(self, qapp, tmp_dir):
        with pytest.raises(ValueError):
            self._controller()[0].export("docx", str(tmp_dir / "x.docx"), None, None)


# --------------------------------------------------------------------------
# ThemeManager
# --------------------------------------------------------------------------
class TestThemeManager:
    def test_menu_selection_persists_and_applies(self, qapp, monkeypatch):
        import src.ui.theme_manager as theme_manager
        from src.ui.visualization_panel import VisualizationPanel

        saved = []
        monkeypatch.setattr(theme_manager, "set_theme", saved.append)
        window = QWidget()
        manager = theme_manager.ThemeManager(window, ResultsPanel(), VisualizationPanel())
        menu = QMenu()
        manager.build_menu(menu)
        actions = {action.text(): action for action in menu.actions()}
        assert set(actions) == {"Light", "Dark", "System"}

        actions["Light"].trigger()
        assert saved == ["light"]
        assert manager.current == "light"
        assert actions["Light"].isChecked() and not actions["Dark"].isChecked()
        assert window.styleSheet() != ""


# --------------------------------------------------------------------------
# Layering
# --------------------------------------------------------------------------
def test_core_package_does_not_import_qt():
    script = (
        "import sys\n"
        "import src.core.computation, src.core.compute_process, src.core.debug_log\n"
        "import src.core.export, src.core.session\n"
        "from src.core.computation import parse_expression, compute_divergence\n"
        "e, _ = parse_expression('x*y')\n"
        "compute_divergence(e, e, e)\n"
        "qt = sorted(m for m in sys.modules if m.split('.')[0] in ('PySide6', 'shiboken6'))\n"
        "assert not qt, qt\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
