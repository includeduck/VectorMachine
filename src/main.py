import os
import sys
import time

# Add the project root to sys.path so 'src' module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def main():
    # Imported here, not at module level: the SymPy child process re-imports
    # this module on spawn, and must not pull in Qt and the whole UI.
    from PySide6.QtWidgets import QApplication

    from src.core.debug_log import debug_log
    from src.ui import branding
    from src.ui.app_window import VectorMachineWindow

    start_time = time.perf_counter()

    # Before any window exists, so the taskbar picks up the app's identity.
    branding.set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(branding.APP_NAME)
    app.setApplicationVersion(branding.APP_VERSION)
    app.setWindowIcon(branding.app_icon())
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
