# VectorMachine Implementation Plan

## Project Purpose
Build a desktop application for students to define symbolic vector fields and compute vector calculus operations such as divergence and curl, with step-by-step derivations, saving/loading sessions, example data, export options, and optional visualization.

## Scope
This plan covers the implementation of the core application flows described in `UseCase.md`, including:
- vector field input and validation
- symbolic computation (divergence and curl) with SymPy
- step-by-step solution display
- session persistence (save/load)
- example vector fields
- input clearing
- export of results
- theme settings
- 2D/3D visualization using PyVista
- responsive desktop UI with PySide6

## High-level Architecture

### Layers
- UI layer: PySide6 widgets and dialogs
- Computation layer: SymPy parsing, differentiation, simplification, and result formatting
- Persistence layer: session serialization and file storage
- Visualization layer: PyVista rendering and plot controls

### Core Components
- Input Panel
  - fields for `P(x,y,z)`, `Q(x,y,z)`, `R(x,y,z)`
  - live syntax validation and parsed preview
- Result Panel
  - divergence output
  - curl output
  - derivation steps
- Controls
  - Compute Divergence
  - Compute Curl
  - Clear
  - Load Example
  - Save Session
  - Open Session
  - Export Results
  - Theme toggles
  - Visualization options
- Visualization Pane
  - 2D quiver plot mode
  - 3D arrow glyph mode
  - rotate, zoom, pan controls
  - density/scale/domain settings

## Implementation Tasks

### 1. Project Setup
- verify Python environment using `requirements.txt`
- create application entry point and initial window
- define application constants and supported math functions
- add startup timer instrumentation to meet startup requirement

### 2. Input Handling and Validation
- implement input widgets for `P`, `Q`, `R`
- parse expressions on change using SymPy with support for `x`, `y`, `z`
- implement live syntax validation
- show inline errors with location details
- display parsed preview `F = <P, Q, R>`
- enforce non-empty input for each component

### 3. Symbolic Computation
- implement `compute_divergence()` using:
  - `diff(P, x) + diff(Q, y) + diff(R, z)`
- implement `compute_curl()` using the standard vector formula
- simplify results automatically
- provide intermediate derivative expressions
- generate step-by-step derivation text
- handle invalid expressions gracefully

### 4. Result Display
- render final simplified answer clearly
- display formula and intermediate steps for divergence
- display determinant form, intermediate derivatives, and final vector for curl
- update UI immediately after computation

### 5. Session Persistence
- define session model: `P`, `Q`, `R`, `results`, `timestamp`
- implement Save Session to file JSON or YAML
- implement Open Session to restore state
- restore UI and computed results after load
- preserve timestamp and file metadata

### 6. Example Data
- provide built-in example fields:
  - `<x, y, z>`
  - `<y*z, x^2, sin(x)>`
  - `<exp(x*y), ln(z), x*z>`
- implement `Load Example` menu / buttons to populate inputs
- clear previous results when example is loaded

### 7. Clear Input
- implement Clear action
- reset `P`, `Q`, `R` fields
- reset result panel and error messages
- reset preview and visualization state

### 8. Export Options
- implement export formats:
  - PDF
  - PNG
  - Markdown
  - Plain text
- include field definitions, formula, steps, final results, and timestamp
- choose a simple export workflow using built-in file dialogs

### 9. Visualization
- embed PyVista rendering into the PySide6 application
- support 2D quiver plots and 3D arrow glyphs
- add controls for arrow density, scale, domain
- allow camera interactions: rotate, zoom, pan
- update visualization from current vector field geometry
- provide responsive rendering on desktop platforms

### 10. Theme Settings
- implement Light/Dark/System theme modes
- persist selection across sessions
- apply theme consistently to all UI panels

### 11. Keyboard Shortcuts
- add shortcuts for key flows:
  - compute divergence
  - compute curl
  - clear input
  - save/open session
  - export
- support accessible keyboard navigation

## Milestones

### Milestone 1: Core Input + Computation
- complete input form and validation
- compute divergence and curl
- display final results and derivation steps

### Milestone 2: Persistence + Examples
- implement save/load session
- implement example vector fields
- add clear input action

### Milestone 3: Visualization + Export
- add 2D/3D visualization controls
- implement export to Markdown/PNG/PDF/plain text
- add theme settings and keyboard shortcuts

### Milestone 4: Polish + Cross-platform QA
- tune startup responsiveness
- test on Windows/Linux/macOS
- validate offline operation and accessibility
- fix UI issues and finalize error messages

## Acceptance Criteria
- `P`, `Q`, and `R` inputs accept valid math expressions without LaTeX
- divergence and curl compute correctly with SymPy
- step-by-step derivations are shown for both operations
- invalid syntax triggers clear inline errors
- session save/open works and restores state
- examples load correctly
- clear resets inputs and results
- export creates readable output files in chosen format
- visualization renders 2D/3D field views and supports user interaction
- theme selection persists across sessions
- application starts quickly and responds smoothly

## Dependencies
- Python 3.x
- PySide6
- SymPy
- PyVista
- NumPy
- Matplotlib (optional for 2D plots)

## Risks and Mitigations
- Parsing complex expressions: validate incrementally and report clear errors.
- PyVista integration with PySide6: keep visualization panel optional and fallback to text output if initialization fails.
- Cross-platform differences: use standard Qt/PySide6 APIs and avoid platform-specific paths.
- Export formatting: start with Markdown/plain text first, then add PDF/PNG once core exports work.

## Notes
- The application should work offline and preserve user data locally.
- The UI should remain responsive even during symbolic simplification by using lightweight operations and keeping computations on the main thread if they are fast; if needed, offload heavy work to a worker thread.
- The implementation should follow the use cases in `UseCase.md` closely, ensuring each UC is mapped to a clear application flow.
