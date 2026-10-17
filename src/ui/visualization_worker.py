import time

import numpy as np
from PySide6.QtCore import QThread, Signal

from src.core.computation import evaluate_field


class VisualizationWorker(QThread):
    """Background worker that computes field vector numerical grids off the Qt GUI thread."""

    finished_ok = Signal(int, object, object, object, bool, float, float)
    finished_err = Signal(int, str)

    def __init__(
        self,
        revision_id: int,
        p_expr,
        q_expr,
        r_expr,
        domain: int,
        density: int,
        scale_factor: float,
        is_2d: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.revision_id = revision_id
        self.p_expr = p_expr
        self.q_expr = q_expr
        self.r_expr = r_expr
        self.domain = domain
        self.density = density
        self.scale_factor = scale_factor
        self.is_2d = is_2d
        self._cancelled = False

    def cancel(self):
        """Mark this worker as cancelled so completed results are not emitted."""
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return

        t0 = time.perf_counter()
        try:
            x = np.linspace(-self.domain, self.domain, self.density)
            y = np.linspace(-self.domain, self.domain, self.density)
            if self.is_2d:
                z = np.array([0.0])
            else:
                z = np.linspace(-self.domain, self.domain, self.density)

            x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing="ij")

            if self._cancelled:
                return

            u, v, w = evaluate_field(
                self.p_expr, self.q_expr, self.r_expr, x_grid, y_grid, z_grid
            )

            if self._cancelled:
                return

            points = np.c_[x_grid.ravel(), y_grid.ravel(), z_grid.ravel()]
            vectors = np.c_[u.ravel(), v.ravel(), w.ravel()]

            if np.iscomplexobj(vectors):
                real_vectors = np.real(vectors)
                valid_vectors = np.isclose(np.imag(vectors), 0.0, equal_nan=False)
                valid_mask = np.all(valid_vectors, axis=1)
                vectors = real_vectors
            else:
                valid_mask = np.ones(len(vectors), dtype=bool)
            valid_mask &= np.all(np.isfinite(vectors), axis=1)

            if not np.any(valid_mask):
                points = np.empty((0, 3), dtype=np.float64)
                vectors = np.empty((0, 3), dtype=np.float64)
                magnitudes = np.empty((0,), dtype=np.float64)
            else:
                points = points[valid_mask]
                vectors = vectors[valid_mask]
                magnitudes = np.linalg.norm(vectors, axis=1)

            elapsed_ms = (time.perf_counter() - t0) * 1000

            if not self._cancelled:
                self.finished_ok.emit(
                    self.revision_id,
                    points,
                    vectors,
                    magnitudes,
                    self.is_2d,
                    self.scale_factor,
                    elapsed_ms,
                )
        except Exception as e:
            if not self._cancelled:
                self.finished_err.emit(self.revision_id, str(e))
