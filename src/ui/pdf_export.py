"""PDF export.  It renders HTML with Qt, so it lives in the UI layer and
``src/core`` stays free of Qt."""

import os
from datetime import datetime
from html import escape

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QPageSize, QPdfWriter, QTextDocument

from src.ui import branding

# Registered on the document as an in-memory resource, so the header image
# doesn't depend on file paths or data-URL support in the HTML renderer.
_LOGO_URL = QUrl("vectormachine://logo")
_LOGO_SIZE = 56


def report_header_html(field=None, generated=None):
    """Logo, title, the vector field and the generation time."""
    generated = generated or datetime.now()
    lines = [f"<span style='font-size:16pt; font-weight:bold'>{branding.APP_NAME} report</span>"]
    if field is not None:
        p, q, r = (escape(text) for text in field)
        lines.append(f"Vector field: F = &lt; {p}, {q}, {r} &gt;")
    lines.append(f"<span style='color:#5c5c5c'>Generated {generated:%Y-%m-%d %H:%M}</span>")
    return (
        "<table cellspacing='0' cellpadding='0'><tr>"
        f"<td valign='middle'><img src='{_LOGO_URL.toString()}' "
        f"width='{_LOGO_SIZE}' height='{_LOGO_SIZE}'></td>"
        "<td width='14'></td>"
        f"<td valign='middle'>{'<br/>'.join(lines)}</td>"
        "</tr></table><hr>"
    )


def export_pdf(filepath, html_content, field=None):
    """Write ``html_content`` as an A4 PDF, under a branded header."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    doc = QTextDocument()
    logo = QImage(str(branding.logo_tile_path()))
    if not logo.isNull():
        doc.addResource(QTextDocument.ImageResource, _LOGO_URL, logo)
    doc.setHtml(report_header_html(field) + html_content)
    writer = QPdfWriter(str(filepath))
    writer.setPageSize(QPageSize(QPageSize.A4))
    doc.print_(writer)
