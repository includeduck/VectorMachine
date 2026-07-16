<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/4/41/Nabla_symbol.svg" alt="VectorMachine Logo" width="120" height="120">
  <h1>VectorMachine</h1>
  <p><strong>A Desktop Application for Symbolic Vector Calculus and 3D Field Visualization</strong></p>
  <br/>
</div>

## 🌌 Overview

**VectorMachine** is a powerful educational and mathematical tool designed to help students, engineers, and researchers explore vector fields. Built with a sleek, modern PySide6 interface, it seamlessly bridges symbolic mathematics with interactive 3D visualizations.

Whether you're calculating divergence, evaluating curl, or trying to visualize how a field behaves in three-dimensional space, VectorMachine does the heavy lifting for you—showing all its work step-by-step.

---

## ✨ Features

- **Symbolic Calculus**: Leverages [SymPy](https://www.sympy.org/) to compute exact partial derivatives for Divergence and Curl.
- **Step-by-Step Derivations**: Don't just get the final answer. VectorMachine shows the exact formulas and unsimplified steps used to arrive at the solution.
- **Interactive Visualization**: Powered by [PyVista](https://docs.pyvista.org/) and VTK, providing buttery-smooth 2D quiver plots and 3D arrow glyphs that update dynamically.
- **Export Anywhere**: Save your work natively to `.json` sessions, or export beautifully formatted `.md` (Markdown), `.txt`, `.pdf`, or `.png` reports.
- **Keyboard Navigation**: Highly accessible with built-in shortcuts to keep your hands on the keyboard.

---

## 🚀 Quickstart

### Prerequisites
Make sure you have Python 3.9+ installed.

### Installation
Clone the repository and install the requirements:

```bash
git clone https://github.com/yourusername/VectorMachine.git
cd VectorMachine
python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Running the App
```bash
python src/main.py
```

---

## ⌨️ Shortcuts & Controls

- `Ctrl + Return`: Compute Divergence
- `Ctrl + Shift + Return`: Compute Curl
- `Ctrl + Del`: Clear Inputs
- `Ctrl + S`: Save Session
- `Ctrl + O`: Open Session

### 3D Navigation
- **Left Click & Drag**: Rotate camera
- **Right Click & Drag**: Zoom in/out
- **Middle Click & Drag**: Pan camera

---

## 🏗️ Architecture

VectorMachine is designed around three core layers:
1. **Core Computation (`src/core/`)**: Handles all parsing, SymPy evaluations, Numpy vectorization, and data serialization.
2. **User Interface (`src/ui/`)**: A modular PySide6 application structured with standalone components for inputs, results, and visualization.
3. **Documentation (`doc/`)**: Detailed internal specs, milestone plans, and progress tracking.

---

<div align="center">
  <sub>Built for exploration. Enjoy the math!</sub>
</div>
