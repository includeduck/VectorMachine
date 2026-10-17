"""Writes exports in each supported format, without any dialogs."""

from src.core.export import export_markdown, export_text
from src.ui.pdf_export import export_pdf

FILE_FILTERS = {
    "md": "Markdown Files (*.md)",
    "txt": "Text Files (*.txt)",
    "pdf": "PDF Files (*.pdf)",
    "png": "PNG Images (*.png)",
}


class ExportController:
    def __init__(self, input_panel, results_panel, visualization_panel, is_visualization_active):
        self._input_panel = input_panel
        self._results_panel = results_panel
        self._visualization_panel = visualization_panel
        # Callable: PNG export captures the plot only when that tab is shown.
        self._is_visualization_active = is_visualization_active

    def incomplete_field(self):
        """True if any component is empty, in which case export is refused."""
        return not all(self._input_panel.get_texts())

    def export(self, format_type, file_path, div_steps, curl_steps):
        """Write ``file_path`` in ``format_type``.  Raises on failure."""
        p, q, r = self._input_panel.get_texts()
        if format_type == "txt":
            export_text(file_path, p, q, r, div_steps, curl_steps)
        elif format_type == "md":
            export_markdown(file_path, p, q, r, div_steps, curl_steps)
        elif format_type == "pdf":
            export_pdf(file_path, self._results_panel.export_html())
        elif format_type == "png":
            if self._is_visualization_active():
                if not self._visualization_panel.export_screenshot(file_path):
                    raise OSError("Could not capture 3D visualization screenshot.")
            elif not self._results_panel.grab().save(file_path, "PNG"):
                raise OSError("Qt could not write the PNG file.")
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
