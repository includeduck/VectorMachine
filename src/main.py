import sys
import os
import time

# Add the project root to sys.path so 'src' module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication
from src.ui.app_window import VectorMachineWindow

def main():
    start_time = time.time()
    
    app = QApplication(sys.argv)
    
    window = VectorMachineWindow()
    window.show()
    
    print(f"Application started in {time.time() - start_time:.2f} seconds")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
