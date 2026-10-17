"""Tests for the symbolic and numerical computation core."""

import subprocess
import sys
from pathlib import Path

import numpy as np

from src.core.computation import (
    compute_curl,
    compute_divergence,
    evaluate_field,
    parse_expression,
)


class TestExpressionParsing:
    """Test suite for mathematical expression parsing and security validation."""

    def test_valid_basic_expressions(self):
        expr, err = parse_expression("x**2 + 2*y - z")
        assert err is None
        assert expr is not None

    def test_implicit_multiplication_and_trig(self):
        expr, err = parse_expression("2sin(x) + ln(z) + x y")
        assert err is None
        assert str(expr) == "x*y + log(z) + 2*sin(x)"

    def test_power_syntax(self):
        expr, err = parse_expression("x**3 + y**2")
        assert err is None
        assert str(expr) == "x**3 + y**2"

    def test_caret_is_exponentiation(self):
        # ``^`` used to be parsed as Python XOR: "2^3" silently became 1.
        cases = {"x^2": "x**2", "2^3": "8", "sin^2(x)": "sin(x)**2", "x^2 + y^3": "x**2 + y**3"}
        for text, expected in cases.items():
            expr, err = parse_expression(text)
            assert err is None, f"{text}: {err}"
            assert str(expr) == expected

    def test_oversized_numbers_rejected_without_hanging(self):
        # Exact bignum evaluation holds the GIL, so run in a child process
        # with a timeout: a regression must fail the test, not hang the suite.
        hostile = [
            "9**9**9", "9^9^9", "(9**9)**(9**9)", "sqrt(2)**(10**9)",
            "(1/3)**(10**9)", "(10**8)!", "10000000000!", "2**4000",
            "10**900*10**900",
        ]
        script = (
            "import sys\n"
            "from src.core.computation import parse_expression\n"
            "for text in sys.argv[1:]:\n"
            "    expr, err = parse_expression(text)\n"
            "    assert expr is None and 'too large' in err, (text, expr, err)\n"
        )
        project_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "-c", script, *hostile],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr

    def test_bounded_numbers_still_allowed(self):
        cases = {
            "2**100": str(2**100), "5!": "120", "1**(10**9)": "1",
            "(-1)**(10**9)": "1", "x**(10**9)": "x**1000000000",
        }
        for text, expected in cases.items():
            expr, err = parse_expression(text)
            assert err is None, f"{text}: {err}"
            assert str(expr) == expected

    def test_empty_and_whitespace_input(self):
        expr, err = parse_expression("   ")
        assert expr is None
        assert "empty" in err.lower()

    def test_syntax_errors(self):
        for invalid_expr in ("x +", "sin(", "x**", "++", "/"):
            expr, err = parse_expression(invalid_expr)
            assert expr is None, f"Expected None for {invalid_expr}"
            assert err is not None

    def test_security_forbidden_constructs(self):
        exploits = [
            "__import__('os').system('echo unsafe')",
            "open('/etc/passwd')",
            "eval('1+1')",
            "exec('x=1')",
            "getattr(x, '__class__')",
            "x; y",
            "import math",
        ]
        for exploit in exploits:
            expr, err = parse_expression(exploit)
            assert expr is None, f"Security violation not blocked: {exploit}"
            assert err is not None

    def test_security_unsupported_symbols(self):
        for invalid in ("foo", "bar", "a + b", "x + t"):
            expr, err = parse_expression(invalid)
            assert expr is None
            assert err is not None


class TestSymbolicCalculus:
    """Test suite for symbolic vector calculus operations."""

    def test_divergence_linear(self, radial_field):
        p, q, r = radial_field
        div = compute_divergence(p, q, r)
        assert div["dP_dx"] == "1"
        assert div["dQ_dy"] == "1"
        assert div["dR_dz"] == "1"
        assert div["final"] == "3"

    def test_divergence_rotational(self, rotational_field):
        p, q, r = rotational_field
        div = compute_divergence(p, q, r)
        assert div["final"] == "0"

    def test_curl_rotational(self, rotational_field):
        p, q, r = rotational_field
        curl = compute_curl(p, q, r)
        assert curl["final_i"] == "0"
        assert curl["final_j"] == "0"
        assert curl["final_k"] == "2"

    def test_curl_radial(self, radial_field):
        p, q, r = radial_field
        curl = compute_curl(p, q, r)
        assert curl["final_i"] == "0"
        assert curl["final_j"] == "0"
        assert curl["final_k"] == "0"

    def test_trigonometric_field(self):
        p, _ = parse_expression("sin(y)")
        q, _ = parse_expression("cos(x)")
        r, _ = parse_expression("exp(z)")
        div = compute_divergence(p, q, r)
        assert div["final"] == "exp(z)"

        curl = compute_curl(p, q, r)
        assert curl["final_i"] == "0"
        assert curl["final_j"] == "0"
        assert "-sin(x) - cos(y)" in curl["final_k"]


class TestNumericalEvaluation:
    """Test suite for numerical field evaluation and caching."""

    def test_grid_evaluation_shapes(self, rotational_field):
        p, q, r = rotational_field
        x = np.linspace(-2, 2, 5)
        y = np.linspace(-2, 2, 5)
        z = np.linspace(-2, 2, 5)
        x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing="ij")

        u, v, w = evaluate_field(p, q, r, x_grid, y_grid, z_grid)
        assert u.shape == (5, 5, 5)
        assert v.shape == (5, 5, 5)
        assert w.shape == (5, 5, 5)
        assert np.allclose(w, 0.0)

    def test_evaluation_caching(self, radial_field):
        p, q, r = radial_field
        x = np.linspace(-1, 1, 4)
        y = np.linspace(-1, 1, 4)
        z = np.array([0.0])
        x_grid, y_grid, z_grid = np.meshgrid(x, y, z, indexing="ij")

        # Run multiple times to verify deterministic cached output
        for _ in range(3):
            u, v, w = evaluate_field(p, q, r, x_grid, y_grid, z_grid)
            assert np.allclose(u, x_grid)
            assert np.allclose(v, y_grid)
            assert np.allclose(w, z_grid)

    def test_evaluation_non_finite_handling(self):
        # 1/x has singularity at x=0
        p, _ = parse_expression("1/x")
        q, _ = parse_expression("0")
        r, _ = parse_expression("0")

        x_grid = np.array([[-1.0, 0.0, 1.0]])
        y_grid = np.array([[0.0, 0.0, 0.0]])
        z_grid = np.array([[0.0, 0.0, 0.0]])

        u, v, w = evaluate_field(p, q, r, x_grid, y_grid, z_grid)
        assert np.isnan(u[0, 1]) or np.isinf(u[0, 1])
        assert not np.isnan(u[0, 0]) and not np.isnan(u[0, 2])
