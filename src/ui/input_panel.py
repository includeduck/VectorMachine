from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QGroupBox, QFormLayout)
from PySide6.QtCore import Signal, QTimer
from src.core.computation import parse_expression

class InputPanel(QWidget):
    # Signals for when input is valid or invalid, and when fields change
    inputChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(400) # 400ms debounce
        self.validation_timer.timeout.connect(self.do_validate_inputs)
        
        self.setup_ui()
        self.connect_signals()
        self.do_validate_inputs()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.group_box = QGroupBox("Vector Field F = <P, Q, R>")
        form_layout = QFormLayout()
        
        self.p_input = QLineEdit()
        self.p_input.setPlaceholderText("e.g. x**2 * y")
        self.p_error = QLabel("")
        self.p_error.setStyleSheet("color: red;")
        
        self.q_input = QLineEdit()
        self.q_input.setPlaceholderText("e.g. sin(z)")
        self.q_error = QLabel("")
        self.q_error.setStyleSheet("color: red;")
        
        self.r_input = QLineEdit()
        self.r_input.setPlaceholderText("e.g. y * z")
        self.r_error = QLabel("")
        self.r_error.setStyleSheet("color: red;")
        
        # Add rows with input and error label
        p_layout = QVBoxLayout()
        p_layout.addWidget(self.p_input)
        p_layout.addWidget(self.p_error)
        form_layout.addRow("P(x,y,z):", p_layout)
        
        q_layout = QVBoxLayout()
        q_layout.addWidget(self.q_input)
        q_layout.addWidget(self.q_error)
        form_layout.addRow("Q(x,y,z):", q_layout)
        
        r_layout = QVBoxLayout()
        r_layout.addWidget(self.r_input)
        r_layout.addWidget(self.r_error)
        form_layout.addRow("R(x,y,z):", r_layout)
        
        self.group_box.setLayout(form_layout)
        layout.addWidget(self.group_box)
        
        self.preview_label = QLabel("Preview: F = <_, _, _>")
        self.preview_label.setStyleSheet("font-weight: bold; color: green;")
        layout.addWidget(self.preview_label)
        
    def connect_signals(self):
        self.p_input.textChanged.connect(self.validate_inputs)
        self.q_input.textChanged.connect(self.validate_inputs)
        self.r_input.textChanged.connect(self.validate_inputs)
        
    def validate_inputs(self):
        self.validation_timer.start()
        
    def do_validate_inputs(self):
        p_text = self.p_input.text()
        q_text = self.q_input.text()
        r_text = self.r_input.text()
        
        p_expr, p_err = parse_expression(p_text)
        q_expr, q_err = parse_expression(q_text)
        r_expr, r_err = parse_expression(r_text)
        
        self.p_error.setText(p_err if p_err else "")
        self.q_error.setText(q_err if q_err else "")
        self.r_error.setText(r_err if r_err else "")
        
        is_valid = not (p_err or q_err or r_err) and (p_text and q_text and r_text)
        
        if is_valid:
            self.preview_label.setText(f"Preview: F = &lt; {str(p_expr)}, {str(q_expr)}, {str(r_expr)} &gt;")
            self.preview_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.preview_label.setText("Preview: [Invalid Input]")
            self.preview_label.setStyleSheet("font-weight: bold; color: red;")
            
        self.inputChanged.emit()
        
    def get_expressions(self):
        """Returns the SymPy expressions if valid, else None."""
        p_text = self.p_input.text()
        q_text = self.q_input.text()
        r_text = self.r_input.text()
        
        p_expr, p_err = parse_expression(p_text)
        q_expr, q_err = parse_expression(q_text)
        r_expr, r_err = parse_expression(r_text)
        
        if p_err or q_err or r_err or not p_text or not q_text or not r_text:
            return None, None, None
            
        return p_expr, q_expr, r_expr
        
    def get_texts(self):
        return self.p_input.text(), self.q_input.text(), self.r_input.text()
        
    def set_texts(self, p_text, q_text, r_text):
        self.p_input.setText(p_text)
        self.q_input.setText(q_text)
        self.r_input.setText(r_text)
        self.do_validate_inputs()
        
    def is_valid(self):
        p_expr, q_expr, r_expr = self.get_expressions()
        return p_expr is not None
