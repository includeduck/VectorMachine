from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit
from PySide6.QtGui import QFont

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
        html = f"""
        <h3>Divergence: div(F) = &nabla; &middot; F</h3>
        <p><b>Formula:</b> {steps['formula']}</p>
        <p><b>Partial Derivatives:</b><br/>
           &part;P/&part;x = {steps['dP_dx']}<br/>
           &part;Q/&part;y = {steps['dQ_dy']}<br/>
           &part;R/&part;z = {steps['dR_dz']}
        </p>
        <p><b>Unsimplified:</b> {steps['unsimplified']}</p>
        <p><b>Final Simplified:</b> <span style="color:blue;">{steps['final']}</span></p>
        <hr>
        """
        self.results_text.setHtml(html)
        
    def display_curl(self, steps):
        html = f"""
        <h3>Curl: curl(F) = &nabla; &times; F</h3>
        <p><b>Determinant components:</b><br/>
           i: (&part;R/&part;y - &part;Q/&part;z) = {steps['dR_dy']} - ({steps['dQ_dz']}) = {steps['i_comp_unsimplified']}<br/>
           j: (&part;P/&part;z - &part;R/&part;x) = {steps['dP_dz']} - ({steps['dR_dx']}) = {steps['j_comp_unsimplified']}<br/>
           k: (&part;Q/&part;x - &part;P/&part;y) = {steps['dQ_dx']} - ({steps['dP_dy']}) = {steps['k_comp_unsimplified']}
        </p>
        <p><b>Final Vector:</b> <br/>
           <span style="color:blue;">&lt; {steps['final_i']}, {steps['final_j']}, {steps['final_k']} &gt;</span>
        </p>
        <hr>
        """
        self.results_text.setHtml(html)
        
    def clear_results(self):
        self.results_text.clear()
