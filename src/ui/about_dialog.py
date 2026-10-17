"""Help > About: logo, version, description, link and library versions."""

import platform
from html import escape
from importlib import metadata

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.ui import branding

DESCRIPTION = (
    "Symbolic divergence and curl with worked steps, plus 2D and 3D "
    "vector-field visualization."
)
LOGO_SIZE = 168
# Distributions to report, as (label, distribution name).
_LIBRARIES = (
    ("SymPy", "sympy"),
    ("NumPy", "numpy"),
    ("PyVista", "pyvista"),
    ("VTK", "vtk"),
    ("Matplotlib", "matplotlib"),
)


def version_details():
    """Plain-text version report, also used by "Copy details"."""
    lines = [
        f"{branding.APP_NAME} {branding.APP_VERSION}",
        f"Python {platform.python_version()} ({platform.system()} {platform.release()})",
        f"PySide6 {pyside_version}, Qt {qVersion()}",
    ]
    for label, distribution in _LIBRARIES:
        try:
            lines.append(f"{label} {metadata.version(distribution)}")
        except metadata.PackageNotFoundError:
            lines.append(f"{label} (not installed)")
    return "\n".join(lines)


class AboutDialog(QDialog):
    def __init__(self, parent=None, accent="#4fc1ff"):
        super().__init__(parent)
        self.setWindowTitle(f"About {branding.APP_NAME}")
        self.setWindowIcon(branding.app_icon())

        logo = QLabel()
        pixmap = QPixmap(str(branding.logo_tile_path()))
        ratio = self.devicePixelRatioF()
        pixmap = pixmap.scaled(
            int(LOGO_SIZE * ratio), int(LOGO_SIZE * ratio),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(ratio)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignTop)
        self.logo_label = logo

        title = QLabel(
            f"<h2 style='margin:0'>{branding.APP_NAME}</h2>"
            f"<p style='margin-top:2px'>Version {escape(branding.APP_VERSION)}</p>"
        )
        description = QLabel(DESCRIPTION)
        description.setWordWrap(True)
        link = QLabel(
            f"<a href='{branding.REPO_URL}' style='color:{accent}'>"
            f"{escape(branding.REPO_URL.removeprefix('https://'))}</a>"
        )
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.link_label = link

        self.details_label = QLabel(version_details())
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details_label.setObjectName("aboutDetails")

        text = QVBoxLayout()
        for widget in (title, description, link, self.details_label):
            text.addWidget(widget)
        text.addStretch()

        top = QHBoxLayout()
        top.addWidget(logo)
        top.addSpacing(16)
        top.addLayout(text, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.copy_button = QPushButton("Copy details")
        self.copy_button.setToolTip("Copy the version details, e.g. for a bug report")
        buttons.addButton(self.copy_button, QDialogButtonBox.ActionRole)
        self.copy_button.clicked.connect(self.copy_details)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(buttons)
        self.setMinimumWidth(560)

    def copy_details(self):
        QGuiApplication.clipboard().setText(version_details())
