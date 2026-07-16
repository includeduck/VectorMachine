import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyvista as pv
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.frame = QWidget()
        self.layout = QVBoxLayout()
        
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.layout.addWidget(self.vtkWidget)
        self.frame.setLayout(self.layout)
        self.setCentralWidget(self.frame)
        
        # Initialize the Plotter with the render window
        self.plotter = pv.Plotter(window_size=[800, 600]) # create default
        # Actually in pyvista >= 0.40, one can pass render_window maybe? Let's see:
        try:
            print("Creating Plotter")
            # In older pyvista, it's not possible to easily pass render_window. 
            # We can do:
            self.vtkWidget.SetRenderWindow(self.plotter.render_window)
            self.vtkWidget.Initialize()
            
            # Add something
            sphere = pv.Sphere()
            self.plotter.add_mesh(sphere)
            
            print("Render successful")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    # Don't show to avoid blocking the test script, we just want to see if it errors out
    window.show()
    print("Test finished without crashing")
    # sys.exit(app.exec())
