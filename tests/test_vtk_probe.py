"""The crash-isolated check that decides whether VTK may start."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.ui import vtk_probe
from tests.slow_helpers import crash, slow_compute

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestRunProbe:
    def test_crashing_child_is_reported_not_fatal(self):
        usable, reason = vtk_probe.run_probe(target=crash)
        assert usable is False
        assert "crashed (exit code 3)" in reason

    def test_hanging_child_is_killed(self):
        started = time.monotonic()
        usable, reason = vtk_probe.run_probe(target=slow_compute, args=(1, 2, 3), timeout=1)
        assert usable is False and "did not finish" in reason
        assert time.monotonic() - started < 6

    def test_real_probe_answers_without_taking_the_caller_down(self):
        # Whether this machine has OpenGL varies (CI runners may not); what
        # matters is a well-formed answer from a separate process.
        usable, reason = vtk_probe.run_probe()
        assert isinstance(usable, bool)
        assert (reason is None) == usable


class TestCheck:
    @pytest.fixture
    def counted_probe(self, monkeypatch):
        calls = []

        def fake_probe():
            calls.append(1)
            return True, None

        monkeypatch.setattr(vtk_probe, "platform_problem", lambda: None)
        monkeypatch.setattr(vtk_probe, "run_probe", fake_probe)
        monkeypatch.setattr(vtk_probe, "_thread", None)
        monkeypatch.setattr(vtk_probe, "_result", None)
        return calls

    @pytest.mark.real_vtk_check
    def test_result_is_cached_until_reset(self, counted_probe):
        assert vtk_probe.check() == (True, None)
        assert vtk_probe.check() == (True, None)
        assert len(counted_probe) == 1
        vtk_probe.reset()
        vtk_probe.check()
        assert len(counted_probe) == 2

    @pytest.mark.real_vtk_check
    def test_headless_qt_platform_is_rejected_without_probing(self, qapp, monkeypatch):
        monkeypatch.setattr(vtk_probe, "run_probe", lambda: pytest.fail("must not probe"))
        usable, reason = vtk_probe.check()
        assert usable is False
        assert "offscreen" in reason


class TestPanelUsesTheProbe:
    @pytest.mark.real_vtk_check
    def test_offscreen_visualization_tab_falls_back_instead_of_crashing(self):
        # The original bug: under Qt's offscreen platform VTK failed to get a
        # pixel format and segfaulted the whole process (exit code 139).
        script = (
            "import os, time\n"
            "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
            "from PySide6.QtWidgets import QApplication\n"
            "app = QApplication([])\n"
            "from src.ui.app_window import VectorMachineWindow\n"
            "w = VectorMachineWindow(); w.show(); w.load_example('-y', 'x', '0')\n"
            "w.tab_widget.setCurrentWidget(w.visualization_panel)\n"
            "end = time.time() + 3\n"
            "while time.time() < end:\n"
            "    app.processEvents(); time.sleep(0.02)\n"
            "p = w.visualization_panel\n"
            "print('vtk', p._vtk_initialized, 'fallback', p.is_using_fallback())\n"
            "print(p._plot_placeholder.text())\n"
            "w.close()\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stderr[-2000:]
        assert "vtk False fallback True" in result.stdout
        assert "offscreen" in result.stdout

    def test_retry_probes_again(self, qapp, monkeypatch):
        from src.ui.visualization_panel import VisualizationPanel

        resets = []
        monkeypatch.setattr(vtk_probe, "check", lambda *a, **k: (False, "no OpenGL here"))
        monkeypatch.setattr(vtk_probe, "reset", lambda: resets.append(1))
        panel = VisualizationPanel()
        assert panel.ensure_vtk_initialized() is False
        assert "no OpenGL here" in panel._plot_placeholder.text()
        assert panel.is_using_fallback()

        panel.retry_vtk_initialization()
        assert resets == [1]
        panel.deleteLater()
        qapp.processEvents()
