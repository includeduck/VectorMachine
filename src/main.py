import sys
import os
import time

# Add the project root to sys.path so 'src' module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication
from src.ui.app_window import VectorMachineWindow
from src.core.debug_log import debug_log

def main():
    start_time = time.perf_counter()
    
    app = QApplication(sys.argv)
    app_created_ms = (time.perf_counter() - start_time) * 1000

    window_start = time.perf_counter()
    window = VectorMachineWindow()
    window_created_ms = (time.perf_counter() - window_start) * 1000

    window.show()
    total_ms = (time.perf_counter() - start_time) * 1000

    debug_log(
        "main.py:main",
        "startup complete",
        {
            "appCreatedMs": round(app_created_ms, 2),
            "windowCreatedMs": round(window_created_ms, 2),
            "totalMs": round(total_ms, 2),
        },
        "F",
    )
    
    print(f"Application started in {total_ms / 1000:.2f} seconds")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
