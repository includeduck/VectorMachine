from html import escape

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGroupBox, QTextEdit, QVBoxLayout, QWidget


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.group_box = QGroupBox("Computation Results")
        group_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        # Monospace font
        font = self.results_text.font()
        font.setFamily("Courier")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.results_text.setFont(font)
        
        group_layout.addWidget(self.results_text)
        self.group_box.setLayout(group_layout)
        layout.addWidget(self.group_box)
        
    def display_divergence(self, steps):
        self.results_text.setHtml(self._divergence_html(steps))

    def display_curl(self, steps):
        self.results_text.setHtml(self._curl_html(steps))

    def display_results(self, div_steps=None, curl_steps=None):
        parts = []
        if div_steps:
            parts.append(self._divergence_html(div_steps))
        if curl_steps:
            parts.append(self._curl_html(curl_steps))
        self.results_text.setHtml("".join(parts) if parts else "")

    def _divergence_html(self, steps):
        values = {key: escape(str(value)) for key, value in steps.items()}
        return f"""
        <h3>Divergence: div(F) = &nabla; &middot; F</h3>
        <p><b>Formula:</b> {values['formula']}</p>
        <p><b>Partial Derivatives:</b><br/>
           &part;P/&part;x = {values['dP_dx']}<br/>
           &part;Q/&part;y = {values['dQ_dy']}<br/>
           &part;R/&part;z = {values['dR_dz']}
        </p>
        <p><b>Unsimplified:</b> {values['unsimplified']}</p>
        <p><b>Final Simplified:</b> <span style="color:blue;">{values['final']}</span></p>
        <hr>
        """

    def _curl_html(self, steps):
        values = {key: escape(str(value)) for key, value in steps.items()}
        return f"""
        <h3>Curl: curl(F) = &nabla; &times; F</h3>
        <p><b>Determinant components:</b><br/>
           i: (&part;R/&part;y - &part;Q/&part;z) = {values['dR_dy']} - ({values['dQ_dz']}) = {values['i_comp_unsimplified']}<br/>
           j: (&part;P/&part;z - &part;R/&part;x) = {values['dP_dz']} - ({values['dR_dx']}) = {values['j_comp_unsimplified']}<br/>
           k: (&part;Q/&part;x - &part;P/&part;y) = {values['dQ_dx']} - ({values['dP_dy']}) = {values['k_comp_unsimplified']}
        </p>
        <p><b>Final Vector:</b> <br/>
           <span style="color:blue;">&lt; {values['final_i']}, {values['final_j']}, {values['final_k']} &gt;</span>
        </p>
        <hr>
        """
        
    def clear_results(self):
        self.results_text.clear()
