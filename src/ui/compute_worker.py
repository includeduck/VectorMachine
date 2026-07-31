from PySide6.QtCore import QThread, Signal


class ComputeWorker(QThread):
    finished_ok = Signal(str, object)
    finished_err = Signal(str, str)

    def __init__(self, compute_type, P, Q, R, parent=None):
        super().__init__(parent)
        self.compute_type = compute_type
        self.P = P
        self.Q = Q
        self.R = R

    def run(self):
        try:
            if self.compute_type == "divergence":
                from src.core.computation import compute_divergence
                result = compute_divergence(self.P, self.Q, self.R)
            elif self.compute_type == "curl":
                from src.core.computation import compute_curl
                result = compute_curl(self.P, self.Q, self.R)
            else:
                raise ValueError(f"Unsupported computation type: {self.compute_type}")
            self.finished_ok.emit(self.compute_type, result)
        except Exception as e:
            self.finished_err.emit(self.compute_type, str(e))
