from PySide6.QtCore import QThread, Signal

from src.core.computation import compute_curl, compute_divergence
from src.core.compute_process import (
    ComputeCancelled,
    ComputeTimeout,
    get_compute_process,
)

_COMPUTATIONS = {
    "divergence": compute_divergence,
    "curl": compute_curl,
}


class ComputeWorker(QThread):
    """Background worker for symbolic vector calculus with timeout and cancellation.

    The SymPy work itself runs in a child process (see ``compute_process``),
    so a timeout or cancel actually stops it instead of leaving a thread
    spinning that also delays application exit.
    """

    finished_ok = Signal(str, object)
    finished_err = Signal(str, str)

    def __init__(self, compute_type, P, Q, R, timeout_sec: float = 10.0, parent=None,
                 compute_process=None):
        super().__init__(parent)
        self.compute_type = compute_type
        self.P = P
        self.Q = Q
        self.R = R
        self.timeout_sec = timeout_sec
        self._process = compute_process or get_compute_process()
        self._cancelled = False

    def cancel(self):
        """Discard this worker's result and stop its computation if running."""
        self._cancelled = True
        self._process.cancel(self)

    def run(self):
        if self._cancelled:
            return

        func = _COMPUTATIONS.get(self.compute_type)
        if func is None:
            self.finished_err.emit(
                self.compute_type, f"Unsupported computation type: {self.compute_type}"
            )
            return

        try:
            result = self._process.run(
                func,
                (self.P, self.Q, self.R),
                self.timeout_sec,
                job=self,
                is_cancelled=lambda: self._cancelled,
            )
            if not self._cancelled:
                self.finished_ok.emit(self.compute_type, result)
        except ComputeCancelled:
            pass
        except ComputeTimeout:
            if not self._cancelled:
                self.finished_err.emit(
                    self.compute_type,
                    f"Computation timed out after {self.timeout_sec}s. "
                    "The expression may be too complex to simplify.",
                )
        except Exception as e:
            if not self._cancelled:
                self.finished_err.emit(self.compute_type, str(e))
