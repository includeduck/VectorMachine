"""PDF export.  It renders HTML with Qt, so it lives in the UI layer and
``src/core`` stays free of Qt."""

import os

from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument


def export_pdf(filepath, html_content):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    doc = QTextDocument()
    doc.setHtml(html_content)
    writer = QPdfWriter(str(filepath))
    writer.setPageSize(QPageSize(QPageSize.A4))
    doc.print_(writer)
