"""Tests for session persistence, serialization, and validation."""

import json

from src.core.computation import compute_curl, compute_divergence, parse_expression
from src.core.session import load_session, save_session


class TestSessionPersistence:
    """Test suite for session save and load functionality."""

    def test_save_and_load_round_trip(self, tmp_dir):
        p, _ = parse_expression("x**2")
        q, _ = parse_expression("y")
        r, _ = parse_expression("sin(z)")
        div = compute_divergence(p, q, r)
        curl = compute_curl(p, q, r)

        session_path = tmp_dir / "test_session.json"
        save_err = save_session(session_path, "x**2", "y", "sin(z)", True, div, curl)
        assert save_err is None
        assert session_path.is_file()

        data, load_err = load_session(session_path)
        assert load_err is None
        assert data is not None
        assert data["P"] == "x**2"
        assert data["Q"] == "y"
        assert data["R"] == "sin(z)"
        assert data["has_results"] is True
        assert data["results"]["divergence"] == div
        assert data["results"]["curl"] == curl

    def test_load_non_existent_file(self, tmp_dir):
        missing_path = tmp_dir / "does_not_exist.json"
        data, err = load_session(missing_path)
        assert data is None
        assert err is not None
        assert "does not exist" in err.lower()

    def test_load_corrupted_json(self, tmp_dir):
        corrupt_path = tmp_dir / "corrupted.json"
        corrupt_path.write_text("{ this is not valid json }", encoding="utf-8")

        data, err = load_session(corrupt_path)
        assert data is None
        assert err is not None
        assert "failed to load" in err.lower()

    def test_load_malformed_results(self, tmp_dir):
        incomplete_path = tmp_dir / "malformed.json"
        incomplete_path.write_text('{"P": "x", "Q": "y", "R": "z", "results": "not a dict"}', encoding="utf-8")

        data, err = load_session(incomplete_path)
        assert data is None
        assert err is not None
        assert "malformed" in err.lower()

    def test_load_invalid_expression_types(self, tmp_dir):
        invalid_type_path = tmp_dir / "invalid_type.json"
        invalid_type_path.write_text(
            json.dumps({
                "P": 123,
                "Q": "y",
                "R": "z",
                "has_results": False,
                "results": {"divergence": None, "curl": None}
            }),
            encoding="utf-8",
        )

        data, err = load_session(invalid_type_path)
        assert data is None
        assert err is not None
        assert "text" in err.lower()

    def test_atomic_write_preserves_utf8(self, tmp_dir):
        unicode_path = tmp_dir / "unicode_session.json"
        save_err = save_session(
            unicode_path,
            "α + x",
            "β + y",
            "γ + z",
            False,
            None,
            None,
        )
        assert save_err is None

        content = unicode_path.read_text(encoding="utf-8")
        assert "α + x" in content
