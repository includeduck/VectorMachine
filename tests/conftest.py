"""Pytest configuration and shared fixtures for VectorMachine tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure offscreen Qt execution in CI and headless environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from src.core.computation import clear_lambdify_cache, parse_expression


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped fixture providing the QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def tmp_dir():
    """Temporary directory fixture for isolated file operations."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture(autouse=True)
def reset_computation_cache():
    """Clear lambdify LRU cache before and after each test."""
    clear_lambdify_cache()
    yield
    clear_lambdify_cache()


@pytest.fixture
def rotational_field():
    """Return parsed expressions for a 2D rotational vector field <-y, x, 0>."""
    p, _ = parse_expression("-y")
    q, _ = parse_expression("x")
    r, _ = parse_expression("0")
    return p, q, r


@pytest.fixture
def radial_field():
    """Return parsed expressions for a 3D radial vector field <x, y, z>."""
    p, _ = parse_expression("x")
    q, _ = parse_expression("y")
    r, _ = parse_expression("z")
    return p, q, r


@pytest.fixture(autouse=True)
def vtk_probe_passes(request, monkeypatch):
    """Report VTK as usable unless a test opts into the real check.

    The suite runs on Qt's ``offscreen`` platform, which the real probe
    rejects (VTK can't render there), so tests that drive the VTK path with a
    fake ``pyvistaqt`` would otherwise never reach it.  Mark a test with
    ``@pytest.mark.real_vtk_check`` to exercise the real probe.
    """
    if request.node.get_closest_marker("real_vtk_check") is None:
        from src.ui import vtk_probe

        monkeypatch.setattr(vtk_probe, "check", lambda *args, **kwargs: (True, None))
