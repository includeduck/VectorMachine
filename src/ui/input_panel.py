from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QGroupBox, QFormLayout)
from PySide6.QtCore import Signal, QTimer
from src.core.computation import parse_expression
from src.core.debug_log import debug_log

class InputPanel(QWidget):
    inputChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(400)
        self.validation_timer.timeout.connect(self.do_validate_inputs)

        self._cached_p = None
        self._cached_q = None
        self._cached_r = None
        self._is_valid = False
        self._parse_count = 0
        
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
        # Cached expressions are no longer a faithful representation as soon
        # as a field changes.  Invalidating immediately prevents a shortcut
        # from computing the previous vector field during the debounce delay.
        self._cached_p = self._cached_q = self._cached_r = None
        self._is_valid = False
        self.preview_label.setText("Preview: validating input...")
        self.preview_label.setStyleSheet("font-weight: bold; color: #b36b00;")
        self.inputChanged.emit()
        self.validation_timer.start()
        
    def do_validate_inputs(self):
        p_text = self.p_input.text()
        q_text = self.q_input.text()
        r_text = self.r_input.text()
        
        self._parse_count += 1
        p_expr, p_err = parse_expression(p_text)
        q_expr, q_err = parse_expression(q_text)
        r_expr, r_err = parse_expression(r_text)

        debug_log(
            "input_panel.py:do_validate_inputs",
            "validation cycle parse",
            {"parseCount": self._parse_count, "valid": not (p_err or q_err or r_err)},
            "D",
        )
        
        self.p_error.setText(p_err if p_err else "")
        self.q_error.setText(q_err if q_err else "")
        self.r_error.setText(r_err if r_err else "")
        
        self._is_valid = not (p_err or q_err or r_err) and bool(p_text and q_text and r_text)
        if self._is_valid:
            self._cached_p, self._cached_q, self._cached_r = p_expr, q_expr, r_expr
            self.preview_label.setText(
                f"Preview: F = < {p_expr}, {q_expr}, {r_expr} >"
            )
            self.preview_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self._cached_p = self._cached_q = self._cached_r = None
            self.preview_label.setText("Preview: [Invalid Input]")
            self.preview_label.setStyleSheet("font-weight: bold; color: red;")
            
        self.inputChanged.emit()
        
    def get_expressions(self):
        debug_log(
            "input_panel.py:get_expressions",
            "get_expressions called (cache hit)",
            {"cached": self._is_valid},
            "D",
        )
        if not self._is_valid:
            return None, None, None
        return self._cached_p, self._cached_q, self._cached_r
        
    def get_texts(self):
        return self.p_input.text(), self.q_input.text(), self.r_input.text()
        
    def set_texts(self, p_text, q_text, r_text):
        self.validation_timer.stop()
        inputs = (self.p_input, self.q_input, self.r_input)
        for input_widget in inputs:
            input_widget.blockSignals(True)
        self.p_input.setText(p_text)
        self.q_input.setText(q_text)
        self.r_input.setText(r_text)
        for input_widget in inputs:
            input_widget.blockSignals(False)
        self.do_validate_inputs()
        
    def is_valid(self):
        return self._is_valid
