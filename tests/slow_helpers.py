"""Module-level helpers for compute-process tests.

They must live in an importable module (not a test function) so they pickle
by reference into the SymPy child process.
"""

import time


def slow_compute(P, Q, R):
    """Stand-in for a runaway ``sp.simplify``: far longer than any timeout."""
    time.sleep(60)
    return {}


def add(a, b):
    return a + b


def fail(message):
    raise ValueError(message)


def crash(*args):
    """Kill the child process outright, as a segfault in a C extension would."""
    import os

    os._exit(3)
