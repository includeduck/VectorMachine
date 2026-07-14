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

## Next Steps
With Milestones 1 and 2 completed, the core symbolic engine and user flows are fully functional. The next phase (Milestone 3) will focus on visualization (2D/3D rendering) and exporting results.
