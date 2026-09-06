"""Tests for background compute and visualization worker threads."""

from src.ui.compute_worker import ComputeWorker
from src.ui.visualization_worker import VisualizationWorker


class TestComputeWorker:
    """Test suite for the symbolic background ComputeWorker."""

    def test_divergence_worker_success(self, qapp, radial_field):
        p, q, r = radial_field
        worker = ComputeWorker("divergence", p, q, r, timeout_sec=5.0)

        results = []
        errors = []
        worker.finished_ok.connect(lambda comp_type, res: results.append((comp_type, res)))
        worker.finished_err.connect(lambda comp_type, err: errors.append((comp_type, err)))

        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert not errors
        assert len(results) == 1
        comp_type, res = results[0]
        assert comp_type == "divergence"
        assert res["final"] == "3"

    def test_curl_worker_success(self, qapp, rotational_field):
        p, q, r = rotational_field
        worker = ComputeWorker("curl", p, q, r, timeout_sec=5.0)

        results = []
        errors = []
        worker.finished_ok.connect(lambda comp_type, res: results.append((comp_type, res)))
        worker.finished_err.connect(lambda comp_type, err: errors.append((comp_type, err)))

        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert not errors
        assert len(results) == 1
        comp_type, res = results[0]
        assert comp_type == "curl"
        assert res["final_k"] == "2"

    def test_compute_worker_cancellation(self, qapp, radial_field):
        p, q, r = radial_field
        worker = ComputeWorker("divergence", p, q, r, timeout_sec=5.0)

        results = []
        worker.finished_ok.connect(lambda comp_type, res: results.append(res))

        worker.cancel()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(results) == 0


class TestVisualizationWorker:
    """Test suite for the numerical 3D meshgrid VisualizationWorker."""

    def test_visualization_worker_3d_grid(self, qapp, rotational_field):
        p, q, r = rotational_field
        worker = VisualizationWorker(
            revision_id=1,
            p_expr=p,
            q_expr=q,
            r_expr=r,
            domain=2,
            density=3,
            scale_factor=0.25,
            is_2d=False,
        )

        results = []
        errors = []
        worker.finished_ok.connect(
            lambda rev, pts, vecs, mags, is_2d, scale, elapsed: results.append(
                (rev, pts, vecs, mags, is_2d, scale, elapsed)
            )
        )
        worker.finished_err.connect(lambda rev, err: errors.append((rev, err)))

        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert not errors
        assert len(results) == 1
        rev, pts, vecs, mags, is_2d, scale, elapsed = results[0]
        assert rev == 1
        assert len(pts) == 3 * 3 * 3  # 27 points
        assert len(vecs) == 27
        assert len(mags) == 27
        assert is_2d is False
        assert scale == 0.25
        assert elapsed > 0

    def test_visualization_worker_2d_slice(self, qapp, rotational_field):
        p, q, r = rotational_field
        worker = VisualizationWorker(
            revision_id=2,
            p_expr=p,
            q_expr=q,
            r_expr=r,
            domain=4,
            density=5,
            scale_factor=0.1,
            is_2d=True,
        )

        results = []
        worker.finished_ok.connect(
            lambda rev, pts, vecs, mags, is_2d, scale, elapsed: results.append((pts, is_2d))
        )

        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(results) == 1
        pts, is_2d = results[0]
        assert is_2d is True
        assert len(pts) == 5 * 5 * 1  # 25 points on z=0 plane

    def test_visualization_worker_cancellation(self, qapp, rotational_field):
        p, q, r = rotational_field
        worker = VisualizationWorker(
            revision_id=3,
            p_expr=p,
            q_expr=q,
            r_expr=r,
            domain=3,
            density=4,
            scale_factor=0.2,
            is_2d=False,
        )

        results = []
        worker.finished_ok.connect(lambda *args: results.append(args))

        worker.cancel()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(results) == 0
