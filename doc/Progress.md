# VectorMachine Progress

## Milestones Completed

### Milestone 1: Core Input + Computation
- **Project Structure**: Established the application skeleton using PySide6 (`src/main.py`, `src/ui/app_window.py`).
- **Input Widgets**: Implemented text input fields for `P(x,y,z)`, `Q(x,y,z)`, and `R(x,y,z)`.
- **Live Syntax Validation**: Integrated SymPy for real-time parsing of mathematical expressions, complete with inline error reporting and a live valid preview.
- **Symbolic Computation**: Implemented symbolic differentiation for vector calculus:
  - **Divergence**: Computes `div(F) = ∂P/∂x + ∂Q/∂y + ∂R/∂z` symbolically.
  - **Curl**: Computes `curl(F)` using the standard determinant vector formula.
- **Results Display**: Built a `ResultsPanel` that renders the formulas, intermediate partial derivatives, unsimplified expressions, and final simplified answers cleanly.

### Milestone 2: Persistence + Examples
- **Session Management**: Built `session.py` to handle serializing user inputs to JSON.
- **Save / Open State**: Wired up the `File > Save Session` and `File > Open Session` menus so users can save and resume their work seamlessly.
- **Example Data**: Added three built-in example vector fields via the `Examples` menu:
  - `<x, y, z>`
  - `<y*z, x**2, sin(x)>`
  - `<exp(x*y), ln(z), x*z>`
- **Clear Flow**: Implemented a `Clear` button that safely resets the inputs, computation results, and validation state.
- **Cross-platform Compatibility**: Ensured the application structure uses relative imports and proper `sys.path` injection so it launches reliably via standard Python virtual environments.

### Milestone 3: Visualization + Export
- **Visualization Panel**: Embedded a PyVista 3D render window directly into the PySide6 UI, allowing interactive 3D and 2D viewing of vector fields.
- **Controls**: Added sliders and spinboxes for domain range, rendering density, and arrow scale.
- **Export Formats**: Implemented robust exporting for `.txt`, `.md`, `.pdf`, and `.png` image captures.
- **Tabs Layout**: Upgraded the UI to use a `QTabWidget` separating raw results from the graphical visualization.

## Next Steps
With Milestones 1, 2, and 3 completed, the application now supports input, calculation, persistence, visualization, and exporting. The final phase (Milestone 4) focuses on cross-platform QA, accessibility, and polishing the final user interface.

## Maintenance Pass: Reliability and Performance

- Secured expression parsing by limiting input to supported mathematical syntax, functions, and variables (`x`, `y`, and `z`), preventing arbitrary Python evaluation.
- Fixed the validation/compute race: edits invalidate cached expressions immediately, and results from computations started before an edit are discarded.
- Improved visualization responsiveness by keeping VTK/PyVista initialization lazy, debouncing redraws, capping 3D density, and ignoring non-finite or complex field samples safely.
- Reduced repeated field-evaluation overhead with a bounded LRU cache that compiles all three vector components together.
- Made diagnostic disk logging opt-in via `VECTORMACHINE_DEBUG_LOG`, avoiding routine I/O during normal use.
- Hardened session persistence with UTF-8, atomic writes, schema validation, and user-facing save failure handling.
- Added headless regression checks for secure parsing, cache-backed evaluation, session validation, all export formats, immediate input invalidation, and stale-computation suppression.

## Phase 1 Recovery: Concurrency, Robust Visualization & Computation Guards

- **Asynchronous 3D Visualization Pipeline**: Created `VisualizationWorker` (`src/ui/visualization_worker.py`) to execute numerical meshgrid generation and `evaluate_field()` calculations in a dedicated background `QThread`. The Qt GUI thread no longer blocks when rendering vector fields.
- **Native OpenGL Screenshot Capture**: Added `export_screenshot()` to `VisualizationPanel` using PyVista's native `plotter.screenshot()`, resolving blank and corrupted image captures caused by `QWidget.grab()` on hardware OpenGL viewports.
- **Computation Timeout & Cancellation**: Enhanced `ComputeWorker` with a 10-second `ThreadPoolExecutor` timeout to prevent runaway SymPy simplifications, and added a user-facing "Cancel Computation" button (`btn_cancel`) in `VectorMachineWindow` to safely abort pending calculations and prevent UI lockouts.
- **Worker Thread Lifecycle & Shiboken Safety**: Fixed `RuntimeError: libshiboken: Internal C++ object already deleted` by clearing thread references on finish, disconnecting stale wrappers, and guarding worker checks (`isRunning()`, `cancel()`) with `shiboken6.isValid()`.
- **Repository Hygiene**: Cleaned up the repository by removing the redundant `.gitignore.txt` and updating `.gitignore` with comprehensive rules for temporary, log, and analysis artifacts.

## Milestone 4: Cross-Platform CI Pipeline & Dedicated Testing Framework

- **Modular Pytest Architecture (`tests/`)**:
  - Organized test suites into dedicated modules: `test_computation.py`, `test_session.py`, `test_export.py`, `test_workers.py`, and `test_ui.py`.
  - Added `tests/conftest.py` providing session-scoped headless `QApplication` fixtures with `QT_QPA_PLATFORM=offscreen` to run Qt and VTK tests safely in headless and CI runners.
  - Implemented 47 automated tests with 72%+ test coverage across the core computation, persistence, export, worker concurrency, and UI layers.
- **Robust PDF Export (`src/core/export.py`)**:
  - Transitioned from `QPrinter` to native Qt `QPdfWriter`, eliminating Windows COM print spooler errors (`code 0x80040155`) and guaranteeing automated directory creation.
- **GitHub Actions CI Automation (`.github/workflows/ci.yml`)**:
  - Configured multi-platform matrix CI running on `ubuntu-latest` (with Xvfb and Mesa/OpenGL libraries) and `windows-latest`.
  - Python matrix coverage for Python 3.11 and 3.12.
  - Incorporated automated linting (`ruff`), Python bytecode compilation verification (`compileall`), test execution (`pytest`), and coverage artifact generation.
- **Developer Experience**:
  - Added `requirements-dev.txt`, `pytest.ini`, and `ruff.toml` for standardized testing, linting, and quality enforcement.

