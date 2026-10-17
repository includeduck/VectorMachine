# Technical Weakness Analysis & Architectural Critique: VectorMachine

**Document Version:** 1.1  
**Date:** September 2026 (status updated October 2026)  
**Subject:** Codebase Architecture, Computational Engine, and System Vulnerabilities  

---

## Status (October 2026)

Since this critique was written, the bug audit (`bugreport.md`, PRs #1 to #4) and the fallback-renderer PR have addressed most of it. The original analysis is kept below, and each heading now carries its status.

| § | Finding | Status | How it was addressed / what remains |
| :--- | :--- | :--- | :--- |
| 1 | Synchronous 3D evaluation | **Resolved** | `VisualizationWorker` evaluates off the GUI thread, and at most one evaluation runs at a time. |
| 1 | Irrecoverable VTK initialisation | **Resolved** | The failure is shown with its reason and a **Retry 3D view** button, and a Matplotlib renderer (`src/ui/mpl_fallback.py`) takes over. |
| 1 | Blank PNG export | **Resolved** | Native `plotter.screenshot()`, or the fallback figure's `savefig`. |
| 2.1 | God Object (`VectorMachineWindow`) | **Resolved** | Compute orchestration, sessions, export and theming moved into `ComputeController`, `SessionController`, `ExportController` and `ThemeManager`. The window (446 → 264 lines) keeps the layout, menus, dialogs and wiring. |
| 2.2 | Qt in `src/core/export.py` | **Resolved** | PDF rendering moved to `src/ui/pdf_export.py` and `QSettings` preferences to `src/ui/settings.py`. A test asserts that importing and using `src/core` loads no PySide6. |
| 2.3 | Repository debris | **Resolved** | Removed `src/test_pv.py`, `.gitignore.txt`, `desktop.ini` and the tracked `.pyc` files, and retired `test_debug.py`. |
| 3.1 | SymPy denial of service | **Resolved** | SymPy runs in a killable child process, and numbers over 1000 digits are rejected before evaluation. |
| 3.2 | Uncancellable threads | **Resolved** | Timeout and Cancel kill the child process; crashes surface as errors. |
| 3.3 | Singularities and arrow scaling | **Partly resolved** | Arrows are scaled to the grid against a robust (95th-percentile) maximum. There is still no warning near poles and no adaptive sampling. |
| 3.4 | "Step-by-step" claims | **Open** | The README wording is corrected, but differentiation rules are still not shown. |
| 3.5 | Cartesian coordinates only | **Open** | |
| 4.1 | Unversioned session schema | **Resolved** | Sessions carry `"version": 1`; newer or malformed versions are rejected. |
| 4.2 | Derived results trusted on load | **Resolved** | Loaded sessions recompute their results from the saved inputs. |
| 4.3 | ASCII math formatting | **Open** | Colours are now theme-aware and WCAG AA, but there is no LaTeX/MathML typesetting. |
| 5 | Testing and QA gaps | **Mostly resolved** | See the update under §5. Fuzzing is still missing. |

---

## Executive Summary

VectorMachine is a desktop application designed to assist students and instructors with symbolic vector calculus (divergence, curl, step derivations) and 2D/3D vector field visualization using PySide6, SymPy, NumPy, and PyVista.

While recent maintenance passes introduced sandboxed parsing, atomic session persistence, and debounced input invalidation, rigorous static analysis, graph topological inspection, and code audits reveal substantial systemic vulnerabilities. Most notably, the project suffers from a severe **architectural God Object**, **main-thread blocking during 3D visualization**, **unbounded symbolic simplification complexity**, and **tight cross-layer coupling**.

This document outlines the key weaknesses, identifies the project's critical **Achilles Heel**, and provides an actionable remediation roadmap.

---

## 1. The Achilles Heel: Synchronous 3D Field Evaluation & PyVista/OpenGL Fragility `[RESOLVED]`

If there is a single point of failure capable of catastrophically destabilizing the application or ruining the user experience, it is **the visualization pipeline's main-thread execution and unisolated C++/OpenGL bindings**.

### Why This Is the Achilles Heel

1. **Main GUI Thread Blocking on Numerical Grid Evaluation:**
   - In `src/ui/visualization_panel.py`, the method `_do_update_plot()` runs directly on Qt's main thread via a `QTimer` single-shot timeout (300ms).
   - Inside `_do_update_plot()`, `evaluate_field(...)` evaluates the vector field over an $N \times N \times N$ 3D grid ($N=15 \implies 3,375$ points per component; in 2D mode, up to $50 \times 50 = 2,500$ points).
   - Although divergence and curl are delegated to a background `ComputeWorker(QThread)`, **3D visualization numerical evaluation, PolyData generation, and glyph filtering happen entirely on the UI thread**.
   - If a student enters expressions with heavy transcendental operations, power towers, or slow lambdified functions, the Qt event loop completely freezes during field evaluation and actor meshing, triggering OS "Application Not Responding" (ANR) warnings.

2. **Irrecoverable VTK Initialization Failures:**
   - In `ensure_vtk_initialized()` (`visualization_panel.py`), if `from pyvistaqt import QtInteractor` or OpenGL context creation fails (common on remote desktops, headless environments, missing graphics drivers, or virtual machines):
     ```python
     self._plot_placeholder.setText(f"PyVista failed to initialize: {e}")
     self.plotter = None
     self._vtk_initialization_failed = True
     ```
   - The flag `_vtk_initialization_failed` permanently locks out the visualization tab for the entire lifetime of the process. There is no retry mechanism, no diagnostics for driver misconfiguration, and no graceful fallback to a software 2D renderer (such as Matplotlib).

3. **Defective PNG Export for 3D Visualizations (`QWidget.grab()` on OpenGL Surfaces):**
   - In `src/ui/app_window.py` (`on_export("png")`):
     ```python
     if self.tab_widget.currentWidget() is self.visualization_panel:
         pixmap = self.visualization_panel.grab()
     ```
   - On Windows and X11/Wayland Linux, calling `QWidget.grab()` on native child OpenGL/VTK viewports frequently captures an empty black rectangle or corrupted frame buffer because VTK renders directly to its own hardware swapchain outside the Qt software raster engine.
   - PyVista provides a native `plotter.screenshot(file_path)` API that reads the OpenGL backbuffer directly, but VectorMachine bypasses this in favor of `QWidget.grab()`.

---

## 2. Architectural Weaknesses (Topological & Graph Analysis)

Topological analysis of the codebase knowledge graph revealed critical structural anomalies:

### 2.1. The Monolithic God Object (`VectorMachineWindow`) `[RESOLVED]`
- **Topological Metric:** Betweenness Centrality of **0.149**, degree **28** (highest in the codebase by far).
- `VectorMachineWindow` acts as a central bottleneck bridging almost every independent subsystem:
  - Layout & Widget Management (`InputPanel`, `ResultsPanel`, `VisualizationPanel`)
  - Menu Actions & File Dialogs (`QFileDialog`, `QMenuBar`)
  - Asynchronous Task Orchestration (`ComputeWorker`, signal-slot multiplexing)
  - State Invalidation & Revision Tracking (`_input_revision`, `_active_compute_revision`)
  - Persistence Layer (`save_session`, `load_session`)
  - Export Subsystem (`export_text`, `export_markdown`, `export_pdf`, `export_png`)
  - Theme Management (`get_theme`, `set_theme`, `stylesheet_for`)
- **Impact:** Any modification to business logic, export formats, or compute pipelines requires editing `app_window.py`. It violates the Single Responsibility Principle (SRP) and creates high merge collision risks.

```
       ┌────────────────────────┐
       │   VectorMachineWindow  │ (God Node: 28 edges, BC: 0.149)
       └───────────┬────────────┘
     ┌─────────────┼─────────────┬─────────────┬─────────────┐
     ▼             ▼             ▼             ▼             ▼
[UI Panels]  [Persistence]   [Worker]    [Export Sys]   [Themes]
(Input, Res, (save/load_     (Compute-   (txt, md,      (QSettings,
 VizPanel)    session)        Worker)     pdf, png)      qss)
```

### 2.2. Architectural Layer Boundary Leaks (`src/core/export.py`) `[RESOLVED]`
- The project documentation (`ImplementationPlan.md`) claims a clean four-layer architecture:
  1. UI Layer (`src/ui/`)
  2. Computation Layer (`src/core/computation.py`)
  3. Persistence Layer (`src/core/session.py`)
  4. Visualization Layer (`src/ui/visualization_panel.py`)
- **The Violation:** `src/core/export.py` directly imports GUI primitives:
  ```python
  from PySide6.QtGui import QTextDocument
  from PySide6.QtPrintSupport import QPrinter
  ```
- Because `export.py` resides under `src/core/`, core services should be 100% headless. Relying on `PySide6.QtPrintSupport` means PDF generation cannot run in headless CI environments or CLI utilities without spinning up an offscreen Qt platform plugin.

### 2.3. Residual Spikes and Workspace Debris `[RESOLVED]`
- `src/test_pv.py`: An obsolete, throwaway debugging spike experimenting with `QVTKRenderWindowInteractor` was committed directly into the production `src/` directory.
- `desktop.ini` and duplicate `.gitignore.txt`: Artifact files committed across subdirectories clutter the repository.
- `test_debug.py` resides in the project root rather than a standard `tests/` hierarchy.

---

## 3. Computational & Mathematical Vulnerabilities

### 3.1. SymPy Denial of Service (Algorithmic Complexity & Hangs) `[RESOLVED]`
- In `src/core/computation.py`:
  ```python
  div_expr = sp.simplify(unsimplified)
  i_comp = sp.simplify(i_comp_unsimplified)
  ```
- SymPy’s `simplify()` is a heuristic driver that attempts dozens of algebraic, trigonometric, and rational transformations. On nested trigonometric functions, rational polynomials, or expressions with non-trivial cancellations, `simplify()` can run with exponential complexity ($O(2^n)$ or worse).
- **No Timeout:** There is no execution timeout on differentiation or simplification. If a student inputs a pathological expression, the worker thread hangs permanently.

### 3.2. Uncancellable Background Threads `[RESOLVED]`
- `ComputeWorker` subclasses `QThread` and executes `run()`.
- While `VectorMachineWindow` properly discards results from stale revisions (`_input_revision`), the underlying thread **cannot be interrupted or killed**.
- If a computation enters an infinite or hyper-complex loop inside SymPy, that thread consumes 100% of a CPU core indefinitely. Because `_compute_in_progress` is set until completion, the user is locked out from running any new divergence or curl calculations until restarting the app.

### 3.3. Numerical Singularities, Poles, and Grid Sampling `[PARTLY RESOLVED]`
- In `evaluate_field()`:
  ```python
  with np.errstate(all="ignore"):
      u, v, w = field_func(x_grid, y_grid, z_grid)
  ```
- While `np.errstate(all="ignore")` prevents console spam, singularities (e.g., $F = \langle \frac{1}{x}, \frac{1}{y}, \frac{1}{z} \rangle$, $\ln(x)$, or $\tan(x)$) produce `inf` and `NaN`.
- In `visualization_panel.py`, points with non-finite coordinates are discarded via `valid_mask &= np.all(np.isfinite(vectors), axis=1)`. However:
  - If a singularity occurs, large adjacent values can distort the color scalar map and arrow glyph normalization, causing arrows to blow up across the screen or collapse to near-zero size elsewhere.
  - The application lacks adaptive sampling near poles or visual warnings informing students why field lines disappear around $x=0$.

### 3.4. Pedagogical Limitation: "Step-by-Step" Derivation is an Illusion `[OPEN]`
- The application claims in `README.md` and `UseCase.md` (UC-09) to provide "Step-by-Step Derivations".
- In reality, `compute_divergence()` and `compute_curl()` only produce:
  1. The general formula definition
  2. The raw partial derivatives
  3. The unsimplified sum
  4. The fully simplified answer
- **What is missing:** It does not show *how* the derivative was obtained (e.g., Product Rule, Chain Rule, Quotient Rule), nor does it show intermediate factoring or common denominator steps. For educational software, it acts as a symbolic calculator rather than an instructional tutor.

### 3.5. Rigid Coordinate System (Cartesian Only) `[OPEN]`
- The vector calculus domain is strictly constrained to Cartesian coordinates $\langle x, y, z \rangle$.
- In undergraduate physics and vector calculus, over 50% of real-world problems (Gauss's Law, Ampere's Law, vortex dynamics, fluid flow around cylinders) require **Cylindrical** $(r, \theta, z)$ or **Spherical** $(\rho, \theta, \phi)$ coordinates. VectorMachine cannot handle these systems.

---

## 4. Reliability, State & Persistence Weaknesses

### 4.1. Unversioned Session Schema `[RESOLVED]`
- In `src/core/session.py`:
  - Sessions serialize raw text, pre-rendered string dictionaries, and timestamps to JSON.
  - There is **no schema version field** (e.g., `"version": "1.0"`).
  - Validation requires exact key sets (`_DIVERGENCE_KEYS`, `_CURL_KEYS`). If future versions alter step representations (e.g., adding LaTeX syntax or rule metadata), all existing user session files will fail validation and be rejected as corrupted.

### 4.2. Serialization of Derivative Results Instead of Pure State `[RESOLVED]`
- The session saves intermediate string computations (`results.divergence` and `results.curl`).
- Saving derived results rather than pure inputs ($P, Q, R$) violates normalization principles. If a session file is manually edited with bogus mathematical results, loading it displays those fraudulent results directly in the UI without verification.

### 4.3. Raw ASCII / HTML Math Formatting `[OPEN]`
- `ResultsPanel` renders equations using basic HTML and Monospace Courier fonts (e.g., `&part;P/&part;x = 2*x*y`).
- SymPy natively supports rich MathML and LaTeX generation (`sp.latex()`).
- Displaying raw ASCII polynomials without proper mathematical typography makes complex vector formulas difficult to parse for students.

---

## 5. Testing & Quality Assurance Gaps `[MOSTLY RESOLVED]`

| Area | Current Status | Vulnerability / Gap |
| :--- | :--- | :--- |
| **Test Framework** | Ad-hoc `test_debug.py` script | No `pytest` runner, no fixtures, no test discovery, no coverage metrics. |
| **CI/CD** | None | No GitHub Actions or automated test runs on pull requests. |
| **UI Integration** | 2 simulated headless events | No systematic automated UI interaction testing (QTest for sliders, menus, shortcuts). |
| **3D Rendering** | Untested in automated test suite | `VisualizationPanel` and PyVista rendering are skipped in headless tests (`QT_QPA_PLATFORM=offscreen`). |
| **Extreme Math Inputs** | Minimal | No fuzz testing with deeply nested expressions, large exponents ($x^{1000}$), or complex branch cuts. |

**Update (October 2026):**

- There is a pytest suite (`tests/`, 97 tests) with shared fixtures.
- GitHub Actions runs ruff and the suite on Ubuntu 24.04 and Windows 2025 with Python 3.12 and 3.14.
- UI tests drive widgets with QTest, covering the sliders and the keyboard.
- Plot calls are checked against an autospec'd `pv.Plotter`.
- The Matplotlib fallback is rendered and exported in tests.
- Hostile inputs (`9**9**9`, `(10**8)!`) run in a subprocess with a timeout, so a regression fails instead of hanging.
- Still missing: systematic fuzzing.

---

## 6. Prioritized Remediation Roadmap

To transition VectorMachine from a student prototype to a resilient, production-ready educational application, the following improvements should be prioritized:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REMEDIATION ROADMAP                             │
├───────────────────┬────────────────────────────────────────────────────┤
│ Priority 1 (High) │ • Decouple 3D field evaluation to a QThread worker │
│                   │ • Fix PNG export to use PyVista native screenshot  │
│                   │ • Add SymPy compute timeout and worker abort       │
├───────────────────┼────────────────────────────────────────────────────┤
│ Priority 2 (Med)  │ • Refactor VectorMachineWindow into controllers    │
│                   │ • Remove Qt dependency from src/core/export.py     │
│                   │ • Add version tag to session JSON schema           │
├───────────────────┼────────────────────────────────────────────────────┤
│ Priority 3 (Low)  │ • Integrate MathJax/KaTeX for rich LaTeX rendering │
│                   │ • Support Cylindrical & Spherical coordinate bases │
│                   │ • Convert test suite to pytest with CI automation  │
└───────────────────┴────────────────────────────────────────────────────┘
```

### Phase 1: High Priority (Stability & Crash Prevention) [COMPLETED]
1. **Asynchronous 3D Grid Evaluation:** `[RESOLVED]`
   - Implemented `VisualizationWorker` (`src/ui/visualization_worker.py`) to execute `evaluate_field()` and mesh points in background `QThread`. UI event loop remains responsive with real-time cancellation on state revision.
2. **Native OpenGL Screenshot Capture:** `[RESOLVED]`
   - Implemented `export_screenshot()` on `VisualizationPanel` via PyVista's native `plotter.screenshot(file_path)` to eliminate blank/corrupted PNG captures.
3. **Computation Timeout & Cancellation:** `[RESOLVED]`
   - Added 10-second timeout guard to `ComputeWorker` via `ThreadPoolExecutor` and user-facing "Cancel Computation" button in `VectorMachineWindow`.
   - *Superseded:* the thread-based timeout couldn't stop SymPy, and exit waited for it. The work now runs in a killable child process (`src/core/compute_process.py`).

### Phase 2: Architectural Decoupling & Cleanliness
1. **Break Down the God Object:** `[RESOLVED]`
   - Extracted `SessionController` (session save/load logic), `ExportController` (file export dispatching) and `ThemeManager`, plus a `ComputeController` for the worker, revision and queue state that also lived on the window. Each has unit tests; the compute controller is tested with a fake worker, so stale-result and queue handling are tested deterministically.
2. **Make `src/core/export.py` Headless:** `[RESOLVED]`
   - Qt-dependent PDF printing moved to `src/ui/pdf_export.py`, and the `QSettings` wrapper to `src/ui/settings.py`.
3. **Purge Repository Debris:** `[RESOLVED]`
   - Removed `src/test_pv.py` and the duplicate `.gitignore.txt`. `test_debug.py` was retired: its checks were already covered by `tests/`, and the one unique assertion (a stale compute leaves the UI unlocked and VTK uninitialised) moved into `tests/test_ui.py`.

### Phase 3: Educational Value & Math Enhancements
1. **True Pedagogical Derivations:**
   - Enhance derivative computation to identify and display the specific calculus differentiation rule used (Sum Rule, Power Rule, Product Rule, Chain Rule).
2. **LaTeX Typography:**
   - Render mathematical outputs in `ResultsPanel` using KaTeX or MathJax inside a `QTextBrowser` or lightweight WebEngine for textbook-grade typesetting.
3. **Coordinate System Expansion:**
   - Add support for Cylindrical $(r, \theta, z)$ and Spherical $(\rho, \theta, \phi)$ divergence and curl equations.
