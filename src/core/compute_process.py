"""Run SymPy work in a child process that can be killed mid-computation.

A thread cannot be stopped once ``sp.simplify`` starts, so a timed-out or
cancelled computation used to keep burning a core, and interpreter exit
waited for it.  A process can simply be killed.  One child is kept warm
between requests; it is replaced after a timeout, a cancel or a crash.
"""

import multiprocessing
import threading

# Time allowed for a fresh child to import SymPy before the first request.
# Kept separate from the per-request timeout so start-up cost is not
# charged against the computation.
_STARTUP_TIMEOUT_SEC = 60.0


class ComputeTimeout(Exception):
    pass


class ComputeCancelled(Exception):
    pass


def _serve(conn):
    """Child-process loop: receive ``(func, args)``, send back the outcome."""
    import sympy  # noqa: F401  (warm the import before reporting ready)

    conn.send(("ready", None))
    while True:
        try:
            request = conn.recv()
        except EOFError:
            return
        if request is None:
            return
        func, args = request
        try:
            conn.send(("ok", func(*args)))
        except Exception as e:
            conn.send(("err", str(e)))


class ComputeProcess:
    """A single, reusable child process for one computation at a time."""

    def __init__(self):
        self._state_lock = threading.Lock()
        # Serialises requests: after a cancel, the next request waits here
        # until the killed request has unwound.
        self._run_lock = threading.Lock()
        self._process = None
        self._conn = None
        self._ready_process = None
        self._busy_job = None

    def start(self):
        """Spawn the child ahead of time so the first request starts warm."""
        with self._state_lock:
            self._ensure_started()

    def _ensure_started(self):
        if self._process is not None and self._process.is_alive():
            return
        context = multiprocessing.get_context("spawn")
        parent_conn, child_conn = context.Pipe()
        process = context.Process(
            target=_serve,
            args=(child_conn,),
            daemon=True,
            name="vectormachine-sympy",
        )
        process.start()
        child_conn.close()
        self._process = process
        self._conn = parent_conn

    def _discard(self, process):
        """Kill ``process`` if it is still the current child."""
        with self._state_lock:
            if process is not self._process:
                return
            self._process = None
            self._conn = None
        if process.is_alive():
            process.kill()
        process.join(timeout=2.0)

    def run(self, func, args, timeout, job=None, is_cancelled=None):
        """Call ``func(*args)`` in the child and return its result.

        ``func`` must be a module-level function so it pickles by reference.
        Raises ``ComputeTimeout`` or ``ComputeCancelled``; an exception raised
        by ``func`` comes back as ``RuntimeError`` with its message.
        ``is_cancelled`` is checked once the request reaches the front of the
        queue, so a request cancelled while waiting never starts.
        """
        with self._run_lock:
            with self._state_lock:
                if is_cancelled is not None and is_cancelled():
                    raise ComputeCancelled
                self._ensure_started()
                process, conn = self._process, self._conn
                self._busy_job = job
            try:
                return self._request(process, conn, func, args, timeout)
            finally:
                with self._state_lock:
                    self._busy_job = None

    def _request(self, process, conn, func, args, timeout):
        try:
            if self._ready_process is not process:
                if not conn.poll(_STARTUP_TIMEOUT_SEC):
                    self._discard(process)
                    raise RuntimeError("The computation engine failed to start.")
                conn.recv()
                self._ready_process = process
            conn.send((func, args))
            if not conn.poll(timeout):
                self._discard(process)
                raise ComputeTimeout
            status, payload = conn.recv()
        except (EOFError, OSError):
            # The child was killed by ``cancel`` (or crashed).
            self._discard(process)
            raise ComputeCancelled from None
        if status == "err":
            raise RuntimeError(payload)
        return payload

    def cancel(self, job):
        """Kill the child if it is currently running ``job``'s request."""
        with self._state_lock:
            if job is None or self._busy_job is not job:
                return
            process = self._process
        if process is not None and process.is_alive():
            process.kill()

    def shutdown(self):
        with self._state_lock:
            process, conn = self._process, self._conn
            self._process = self._conn = None
        if process is None:
            return
        if process.is_alive():
            process.kill()
        process.join(timeout=2.0)
        conn.close()


_shared = None
_shared_lock = threading.Lock()


def get_compute_process():
    """Return the application-wide compute process, creating it if needed."""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = ComputeProcess()
        return _shared
