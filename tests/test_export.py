"""Tests for exporting computation results to TXT, Markdown, and PDF formats."""

from pathlib import Path

import pytest

from src.core.computation import compute_curl, compute_divergence
from src.core.export import export_markdown, export_pdf, export_text


class TestExportSubsystem:
    """Test suite for export capabilities."""

    @pytest.fixture
    def field_and_results(self, rotational_field):
        p, q, r = rotational_field
        div = compute_divergence(p, q, r)
        curl = compute_curl(p, q, r)
        return "-y", "x", "0", div, curl

    def test_export_text(self, tmp_dir, field_and_results):
        p, q, r, div, curl = field_and_results
        txt_path = tmp_dir / "export_report.txt"

        export_text(txt_path, p, q, r, div, curl)
        assert txt_path.is_file()
        content = txt_path.read_text(encoding="utf-8")
        assert "VectorMachine Export" in content
        assert "Vector Field: F = < -y, x, 0 >" in content
        assert "Formula: ∂P/∂x + ∂Q/∂y + ∂R/∂z" in content
        assert "Curl:" in content

    def test_export_markdown(self, tmp_dir, field_and_results):
        p, q, r, div, curl = field_and_results
        md_path = tmp_dir / "export_report.md"

        export_markdown(md_path, p, q, r, div, curl)
        assert md_path.is_file()
        content = md_path.read_text(encoding="utf-8")
        assert "# VectorMachine Export" in content
        assert "**Vector Field:** `F = < -y, x, 0 >`" in content
        assert "## Divergence" in content
        assert "## Curl" in content

    def test_export_pdf(self, tmp_dir, qapp):
        pdf_path = tmp_dir / "export_report.pdf"
        html = "<html><body><h1>VectorMachine Report</h1><p>Test PDF content</p></body></html>"

        export_pdf(pdf_path, html)
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 0

    def test_export_accepts_string_and_path_objects(self, tmp_dir, field_and_results):
        p, q, r, div, curl = field_and_results
        str_path = str(tmp_dir / "test_str.txt")
        export_text(str_path, p, q, r, div, curl)
        assert Path(str_path).is_file()

    def test_export_creates_parent_directories_if_missing(self, tmp_dir, field_and_results):
        p, q, r, div, curl = field_and_results
        nested_path = tmp_dir / "nested" / "sub" / "report.md"
        export_markdown(nested_path, p, q, r, div, curl)
        assert nested_path.is_file()
