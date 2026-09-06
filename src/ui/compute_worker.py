from concurrent.futures import ThreadPoolExecutor, TimeoutError

from PySide6.QtCore import QThread, Signal


class ComputeWorker(QThread):
    """Background worker for symbolic vector calculus with timeout and cancellation."""

    finished_ok = Signal(str, object)
    finished_err = Signal(str, str)

    def __init__(self, compute_type, P, Q, R, timeout_sec: float = 10.0, parent=None):
        super().__init__(parent)
        self.compute_type = compute_type
        self.P = P
        self.Q = Q
        self.R = R
        self.timeout_sec = timeout_sec
        self._cancelled = False

    def cancel(self):
        """Mark this worker as cancelled so completed results are discarded."""
        self._cancelled = True

    def _execute_computation(self):
        if self.compute_type == "divergence":
            from src.core.computation import compute_divergence
            return compute_divergence(self.P, self.Q, self.R)
        elif self.compute_type == "curl":
            from src.core.computation import compute_curl
            return compute_curl(self.P, self.Q, self.R)
        else:
            raise ValueError(f"Unsupported computation type: {self.compute_type}")

    def run(self):
        if self._cancelled:
            return

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._execute_computation)
        try:
            result = future.result(timeout=self.timeout_sec)
            if not self._cancelled:
                self.finished_ok.emit(self.compute_type, result)
        except TimeoutError:
            if not self._cancelled:
                self.finished_err.emit(
                    self.compute_type,
                    f"Computation timed out after {self.timeout_sec}s. "
                    "The expression may be too complex to simplify.",
                )
        except Exception as e:
            if not self._cancelled:
                self.finished_err.emit(self.compute_type, str(e))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
