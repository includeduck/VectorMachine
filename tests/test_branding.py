"""Logo, icon, About dialog and the branded PDF header."""

import sys
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QGuiApplication

from src.ui import branding
from src.ui.about_dialog import AboutDialog, version_details
from src.version import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAssets:
    def test_every_icon_size_exists_and_loads(self, qapp):
        icon = branding.app_icon()
        assert not icon.isNull()
        available = {size.width() for size in icon.availableSizes()}
        assert available == set(branding.ICON_SIZES)
        for size in branding.ICON_SIZES:
            assert not icon.pixmap(QSize(size, size)).isNull()

    def test_ico_carries_every_size_for_packaging(self):
        with Image.open(branding.asset("app.ico")) as ico:
            sizes = {width for width, _ in ico.info["sizes"]}
        assert sizes == set(branding.ICON_SIZES)

    def test_readme_images_exist(self):
        for name in ("readme-logo-dark.png", "readme-logo-light.png", "social-preview.png"):
            assert (PROJECT_ROOT / "assets" / name).is_file(), name
        with Image.open(PROJECT_ROOT / "assets" / "social-preview.png") as card:
            assert card.size == (1280, 640)
        with Image.open(PROJECT_ROOT / "assets" / "readme-logo-dark.png") as logo:
            assert "A" in logo.convert("RGBA").getbands()
            assert logo.convert("RGBA").getpixel((2, 2))[3] == 0  # transparent corner

    def test_build_script_finds_the_emblem_above_the_wordmark(self):
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        try:
            import build_brand_assets as build
        finally:
            sys.path.pop(0)
        master = Image.open(build.MASTER).convert("RGB")
        emblem, wordmark = build.find_parts(master, master.getpixel((8, 8)))
        assert emblem[3] < wordmark[1]  # emblem bottom above wordmark top
        assert wordmark[2] - wordmark[0] > emblem[2] - emblem[0]  # the wordmark is wider


class TestWindowBranding:
    def test_window_icon_and_about_menu(self, qapp):
        from src.ui.app_window import VectorMachineWindow

        window = VectorMachineWindow()
        assert not window.windowIcon().isNull()
        actions = {
            action.text(): action
            for menu in window.menuBar().findChildren(type(window.menuBar().addMenu("x")))
            for action in menu.actions()
        }
        about = actions["About VectorMachine"]
        assert about.menuRole() == QAction.AboutRole
        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_set_windows_app_id_never_raises(self):
        branding.set_windows_app_id()


class TestAboutDialog:
    def test_contents(self, qapp):
        dialog = AboutDialog(accent="#123456")
        assert not dialog.logo_label.pixmap().isNull()
        assert branding.REPO_URL in dialog.link_label.text()
        assert "#123456" in dialog.link_label.text()  # theme accent, not Qt's default blue
        details = dialog.details_label.text()
        assert f"VectorMachine {__version__}" in details
        for name in ("Python", "PySide6", "Qt", "SymPy", "NumPy", "PyVista", "VTK", "Matplotlib"):
            assert name in details
        dialog.deleteLater()

    def test_copy_details(self, qapp):
        dialog = AboutDialog()
        dialog.copy_button.click()
        assert QGuiApplication.clipboard().text() == version_details()
        dialog.deleteLater()

    def test_missing_library_is_reported_not_fatal(self, monkeypatch):
        import src.ui.about_dialog as about

        def missing(name):
            raise about.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(about.metadata, "version", missing)
        assert "SymPy (not installed)" in version_details()


class TestPdfHeader:
    def test_header_has_logo_field_and_date(self):
        from datetime import datetime

        from src.ui.pdf_export import report_header_html

        html = report_header_html(("x", "y", "sin(z)"), generated=datetime(2026, 1, 2, 3, 4))
        assert "VectorMachine report" in html
        assert "F = &lt; x, y, sin(z) &gt;" in html
        assert "Generated 2026-01-02 03:04" in html
        assert "<img src='vectormachine://logo'" in html

    def test_pdf_embeds_the_logo(self, qapp, tmp_dir):
        from src.ui.pdf_export import export_pdf

        path = tmp_dir / "report.pdf"
        export_pdf(path, "<p>results</p>", field=("x", "y", "z"))
        assert b"/Subtype /Image" in path.read_bytes()

    def test_field_is_optional(self, qapp, tmp_dir):
        from src.ui.pdf_export import export_pdf

        path = tmp_dir / "plain.pdf"
        export_pdf(path, "<p>results</p>")
        assert path.stat().st_size > 0


@pytest.mark.parametrize("module", ["src.ui.branding", "src.version"])
def test_version_is_defined_once(module):
    import importlib

    assert importlib.import_module(module).__dict__.get("APP_VERSION", __version__) == __version__
