# Use Cases – Curl & Divergence Calculator

## Project Overview
A desktop application built with Python, PySide6, SymPy, and PyVista that allows students to define a vector field and compute symbolic vector calculus operations with optional visualization.

## Actors
- Student (Primary)
- Instructor
- Teaching Assistant

---

# UC-01 Launch Application
**Goal:** Open the application.

Preconditions:
- Application is installed.

Main Flow:
1. User launches the app.
2. Home window opens.
3. Previous preferences are restored.

Success:
- Application is ready.

---

# UC-02 Enter Vector Field
**Goal:** Enter P(x,y,z), Q(x,y,z), and R(x,y,z).

Main Flow:
1. User types expressions into P, Q, and R.
2. Live syntax validation runs.
3. Parsed preview displays:
   F = <P,Q,R>

Extensions:
- Empty field -> highlight missing component.
- Invalid syntax -> show error with location.

---

# UC-03 Compute Divergence
Formula:
div(F) = ∂P/∂x + ∂Q/∂y + ∂R/∂z

Flow:
1. Click "Compute Divergence".
2. Parse expressions.
3. Symbolically differentiate.
4. Simplify result.
5. Display step-by-step derivation.
6. Display final simplified answer.

---

# UC-04 Compute Curl
Formula:
curl(F)=(
∂R/∂y-∂Q/∂z,
∂P/∂z-∂R/∂x,
∂Q/∂x-∂P/∂y)

Flow:
1. Click "Compute Curl".
2. Differentiate components.
3. Simplify.
4. Display determinant form.
5. Display intermediate derivatives.
6. Display final vector.

---

# UC-05 Clear Input
Goal:
Reset all fields.

Flow:
1. Click Clear.
2. Remove expressions.
3. Remove results.

---

# UC-06 Load Example
Goal:
Populate a sample vector field.

Examples:
- <x,y,z>
- <yz,x²,sin(x)>
- <e^(xy), ln(z), xz>

---

# UC-07 Save Session
Goal:
Save work.

Saved:
- P,Q,R
- Results
- Timestamp

---

# UC-08 Open Session
Goal:
Restore a saved session.

---

# UC-09 View Step-by-Step Solution
Displays:
- Original field
- Formula
- Partial derivatives
- Simplification
- Final answer

---

# UC-10 Visualize Vector Field

2D:
- Quiver plot

3D:
- Arrow glyphs
- Rotate
- Zoom
- Pan

Options:
- Arrow density
- Scale
- Domain

---

# UC-11 Export Results

Formats:
- PDF
- PNG
- Markdown
- Plain text

---

# UC-12 Theme Settings

Options:
- Light
- Dark
- System

---

# Functional Requirements

FR-1 Accept mathematical expressions without LaTeX.
FR-2 Support x, y, z variables.
FR-3 Support standard functions:
- sin
- cos
- tan
- asin
- acos
- atan
- sinh
- cosh
- exp
- sqrt
- log
- ln

FR-4 Perform symbolic differentiation using SymPy.
FR-5 Automatically simplify expressions.
FR-6 Display friendly error messages.
FR-7 Support keyboard shortcuts.
FR-8 Save and load sessions.
FR-9 Interactive visualization.

# Non-functional Requirements

- Startup <2 seconds
- Responsive UI
- Cross-platform (Windows/Linux/macOS)
- Offline operation
- Accessible fonts and keyboard navigation

# Suggested UI

Input Panel
- P(x,y,z)
- Q(x,y,z)
- R(x,y,z)

Buttons
- Compute Curl
- Compute Divergence
- Visualize
- Clear
- Save
- Load

Tabs
- Results
- Steps
- Visualization
- History
- Settings

# Technology Stack

GUI: PySide6
Math Engine: SymPy
Visualization: PyVista + Matplotlib
Packaging: PyInstaller
Testing: pytest

# Future Features

- Gradient calculator
- Line integrals
- Surface integrals
- Jacobian
- Hessian
- Directional derivative
- Cylindrical & spherical coordinates
- Copy as LaTeX
- Interactive tutorial
