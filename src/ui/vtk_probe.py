"""Decide, without risking the app, whether VTK can render here.

When OpenGL is unusable (remote desktops, VMs, missing drivers, or Qt's
``offscreen`` platform) VTK often fails to get a pixel format and then
*segfaults* rather than raising, so a try/except around the viewport can't
catch it and the Matplotlib fallback never engages.  This module answers
"can VTK render?" safely:

- Qt platforms without native windows are rejected outright.
- Otherwise a throwaway child process renders one tiny frame.  If it
  crashes, exits with an error or hangs, only the child dies.

The probe starts in the background at launch, so the answer is usually
ready before the Visualization tab opens.  The result is cached for the
process; ``reset()`` (used by "Retry 3D view") forces a new probe.
"""

import multiprocessing
import threading

# Qt platforms that cannot host a native OpenGL window.
_HEADLESS_PLATFORMS = frozenset({"offscreen", "minimal"})
PROBE_TIMEOUT_SEC = 15.0
# Exit code the probe child uses for "VTK started but reports no OpenGL".
_NO_OPENGL_EXIT = 42

_lock = threading.Lock()
_thread = None
_result = None  # (usable: bool, reason: str | None)


def _render_one_frame():
    """Child process: exit 0 if VTK can render with OpenGL, non-zero if not."""
    import sys

    import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (registers the OpenGL backend)
    from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow

    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(16, 16)
    window.AddRenderer(vtkRenderer())
    window.Render()
    sys.exit(0 if window.SupportsOpenGL() else _NO_OPENGL_EXIT)


def run_probe(target=_render_one_frame, args=(), timeout=PROBE_TIMEOUT_SEC):
    """Run ``target`` in a child process; return ``(usable, reason)``.

    ``target`` must be a module-level function (it is pickled by reference).
    """
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=target, args=args, daemon=True, name="vectormachine-vtk-probe")
    try:
        process.start()
    except Exception as e:
        return False, f"the OpenGL check could not start ({e})"
    process.join(timeout)
    if process.is_alive():
        process.kill()
        process.join(2.0)
        return False, f"the OpenGL check did not finish within {timeout:g} s"
    if process.exitcode == 0:
        return True, None
    if process.exitcode == _NO_OPENGL_EXIT:
        return False, "OpenGL is not supported by the graphics driver"
    return False, f"the OpenGL check crashed (exit code {process.exitcode})"


def platform_problem():
    """A reason VTK can't work on the current Qt platform, or ``None``."""
    from PySide6.QtGui import QGuiApplication

    platform = QGuiApplication.platformName()
    if platform in _HEADLESS_PLATFORMS:
        return f"the Qt '{platform}' platform has no native window for OpenGL"
    return None


def _probe_in_background():
    global _result
    outcome = run_probe()
    with _lock:
        _result = outcome


def start():
    """Begin probing in the background (no-op if started or not needed)."""
    global _thread
    if platform_problem() is not None:
        return
    with _lock:
        if _thread is None:
            _thread = threading.Thread(target=_probe_in_background, name="vtk-probe", daemon=True)
            _thread.start()


def check(timeout=PROBE_TIMEOUT_SEC + 5):
    """Return ``(usable, reason)``, waiting for the background probe if needed."""
    problem = platform_problem()
    if problem is not None:
        return False, problem
    start()
    with _lock:
        thread = _thread
    thread.join(timeout)
    with _lock:
        if _result is None:
            return False, "the OpenGL check did not finish"
        return _result


def reset():
    """Forget the cached result so the next ``check`` probes again."""
    global _thread, _result
    with _lock:
        if _thread is not None and _thread.is_alive():
            return  # a probe is already running; its result will be fresh
        _thread = None
        _result = None
