"""Orchestrates background SymPy computations for the main window.

It owns everything that used to live as loose state on the window: the
running worker, whether a computation is in progress, the input revision
used to drop results for a field that has since been edited, and a queue
of follow-up computations (used to rebuild a loaded session's results).
"""

from PySide6.QtCore import QObject, Signal
from shiboken6 import isValid

from src.ui.compute_worker import ComputeWorker

DEFAULT_TIMEOUT_SEC = 10.0


class ComputeController(QObject):
    # Emitted whenever a computation starts or stops (including cancel).
    busyChanged = Signal(bool)
    # Only results and errors for the current input revision are emitted.
    resultReady = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, parent=None, timeout_sec=DEFAULT_TIMEOUT_SEC, worker_factory=ComputeWorker):
        super().__init__(parent)
        self.timeout_sec = timeout_sec
        self._worker_factory = worker_factory
        self._worker = None
        self._busy = False
        self._revision = 0
        self._active_revision = None
        self._queue = []

    # -- state -------------------------------------------------------------
    @property
    def is_busy(self):
        return self._busy

    @property
    def worker(self):
        return self._worker

    @property
    def revision(self):
        return self._revision

    def _set_busy(self, busy):
        if busy != self._busy:
            self._busy = busy
            self.busyChanged.emit(busy)

    def invalidate(self):
        """The input changed: results from earlier computations are stale."""
        self._revision += 1
        self._queue = []

    # -- control -----------------------------------------------------------
    def start(self, compute_type, P, Q, R):
        """Start ``compute_type`` for the field; ignored while busy."""
        if P is None or self._busy:
            return False
        self._active_revision = self._revision
        worker = self._worker_factory(
            compute_type, P, Q, R, timeout_sec=self.timeout_sec, parent=self
        )
        self._worker = worker
        # Route results through the worker identity so a cancelled worker's
        # already-queued signal cannot reset the state of its replacement.
        worker.finished_ok.connect(
            lambda kind, result, w=worker: self._on_result(w, kind, result)
        )
        worker.finished_err.connect(
            lambda kind, message, w=worker: self._on_error(w, kind, message)
        )
        worker.finished.connect(lambda w=worker: self._on_thread_finished(w))
        worker.finished.connect(worker.deleteLater)
        self._set_busy(True)
        worker.start()
        return True

    def run_sequence(self, compute_types, P, Q, R):
        """Run several computations one after another for the same field."""
        compute_types = list(compute_types)
        if not compute_types or not self.start(compute_types[0], P, Q, R):
            return False
        self._queue = [(kind, (P, Q, R)) for kind in compute_types[1:]]
        return True

    def cancel(self):
        self._queue = []
        self._cancel_worker()
        self._active_revision = None
        self._set_busy(False)

    def shutdown(self, timeout_ms=2000):
        """Cancel and wait (bounded) for the worker thread, e.g. on close."""
        worker = self._worker
        self.cancel()
        try:
            if worker is not None and isValid(worker):
                worker.wait(timeout_ms)
        except (RuntimeError, ReferenceError):
            pass

    def _cancel_worker(self):
        worker = self._worker
        self._worker = None
        if worker is not None:
            try:
                if isValid(worker) and worker.isRunning():
                    worker.cancel()
            except (RuntimeError, ReferenceError):
                pass

    # -- worker callbacks --------------------------------------------------
    def _finish(self):
        """Common bookkeeping; returns whether the result is still current."""
        is_current = self._active_revision == self._revision
        self._worker = None
        self._active_revision = None
        self._set_busy(False)
        return is_current

    def _on_result(self, worker, compute_type, result):
        if worker is not self._worker:
            return
        if not self._finish():
            return
        self.resultReady.emit(compute_type, result)
        if self._queue:
            kind, (P, Q, R) = self._queue.pop(0)
            self.start(kind, P, Q, R)

    def _on_error(self, worker, compute_type, message):
        if worker is not self._worker:
            return
        self._queue = []
        if self._finish():
            self.failed.emit(compute_type, message)

    def _on_thread_finished(self, worker):
        if self._worker is worker:
            # Still current, so it exited without reporting a result or an
            # error (those callbacks clear it).  Never leave the UI stuck in
            # "computing".
            self._worker = None
            self._queue = []
            self._active_revision = None
            self._set_busy(False)
