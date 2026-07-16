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
