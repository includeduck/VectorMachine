"""The Matplotlib view that replaces VTK when OpenGL is unavailable."""

import sys
import time
import types

import pytest
from PySide6.QtWidgets import QWidget

from src.core.computation import parse_expression
from src.ui.themes import PALETTES
from src.ui.visualization_panel import VisualizationPanel


def _install_fake_pyvistaqt(monkeypatch, fail):
    class FakeInteractor(QWidget):
        def __init__(self, parent=None):
            if fail:
                raise RuntimeError("no OpenGL context")
            super().__init__(parent)

        def set_background(self, colour):
            pass

        def add_axes(self, **kwargs):
            pass

    module = types.ModuleType("pyvistaqt")
    module.QtInteractor = FakeInteractor
    monkeypatch.setitem(sys.modules, "pyvistaqt", module)


@pytest.fixture
def fallback_panel(qapp, monkeypatch):
    _install_fake_pyvistaqt(monkeypatch, fail=True)
    panel = VisualizationPanel()
    assert panel.ensure_vtk_initialized() is False
    yield panel
    panel.stop_workers()
    panel.deleteLater()
    qapp.processEvents()


def _plot(qapp, panel, texts, is_2d):
    (panel.radio_2d if is_2d else panel.radio_3d).setChecked(True)
    panel.p_expr, panel.q_expr, panel.r_expr = (parse_expression(t)[0] for t in texts)
    panel.plot_timer.stop()
    panel._do_update_plot()
    deadline = time.monotonic() + 15
    while (panel._running_worker is not None or panel._replot_pending) and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    return panel._fallback.figure


class TestFallbackActivation:
    def test_vtk_failure_switches_to_matplotlib(self, fallback_panel):
        assert fallback_panel.is_using_fallback()
        assert fallback_panel._has_renderer()
        notice = fallback_panel._plot_placeholder.text()
        assert "Matplotlib" in notice and "no OpenGL context" in notice
        assert not fallback_panel._retry_button.isHidden()

    def test_without_matplotlib_the_error_is_shown(self, qapp, monkeypatch):
        _install_fake_pyvistaqt(monkeypatch, fail=True)
        monkeypatch.setitem(sys.modules, "src.ui.mpl_fallback", None)  # ImportError
        panel = VisualizationPanel()
        assert panel.ensure_vtk_initialized() is False
        assert not panel.is_using_fallback()
        assert "could not start" in panel._plot_placeholder.text()
        panel.deleteLater()
        qapp.processEvents()

    def test_retry_returns_to_vtk(self, fallback_panel, monkeypatch):
        _install_fake_pyvistaqt(monkeypatch, fail=False)
        assert fallback_panel.retry_vtk_initialization()
        assert not fallback_panel.is_using_fallback()
        assert fallback_panel._plot_placeholder.isHidden()


class TestFallbackDrawing:
    def test_2d_quiver(self, qapp, fallback_panel):
        figure = _plot(qapp, fallback_panel, ("-y", "x", "0"), is_2d=True)
        axes = figure.axes[0]
        quivers = [c for c in axes.collections if type(c).__name__ == "Quiver"]
        assert len(quivers) == 1
        assert len(quivers[0].get_offsets()) == 10 * 10  # default density
        assert len(figure.axes) == 2  # plot + colour bar

    def test_3d_quiver(self, qapp, fallback_panel):
        figure = _plot(qapp, fallback_panel, ("x", "y", "z"), is_2d=False)
        axes = figure.axes[0]
        assert axes.name == "3d"
        lines = [c for c in axes.collections if type(c).__name__ == "Line3DCollection"]
        assert len(lines) == 1
        # Three segments per arrow (shaft and two head lines), 10**3 arrows.
        assert len(lines[0].get_segments()) == 3 * 10 ** 3

    def test_empty_field_shows_message(self, qapp, fallback_panel):
        figure = _plot(qapp, fallback_panel, ("log(-x**2 - 1)", "0", "0"), is_2d=True)
        assert any("No finite real vectors" in t.get_text() for t in figure.texts)

    def test_png_export_saves_the_figure(self, qapp, fallback_panel, tmp_dir):
        _plot(qapp, fallback_panel, ("-y", "x", "0"), is_2d=True)
        path = tmp_dir / "fallback.png"
        assert fallback_panel.export_screenshot(str(path))
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(data) > 10_000  # a real plot, not a blank widget grab

    def test_follows_theme(self, qapp, fallback_panel):
        from matplotlib.colors import to_hex

        _plot(qapp, fallback_panel, ("-y", "x", "0"), is_2d=True)
        for theme in ("light", "dark"):
            fallback_panel.apply_palette(PALETTES[theme])
            figure = fallback_panel._fallback.figure
            assert to_hex(figure.get_facecolor()) == PALETTES[theme]["plot_background"]
            assert to_hex(figure.axes[0].get_facecolor()) == PALETTES[theme]["plot_background"]
