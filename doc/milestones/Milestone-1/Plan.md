# Milestone 1 Plan

## Goal
Implement the core data entry and symbolic computation flows so users can enter a vector field, validate input, compute divergence and curl, and view results with derivation steps.

## Scope
- Input widgets for `P(x,y,z)`, `Q(x,y,z)`, `R(x,y,z)`
- Live syntax validation and preview display
- Symbolic divergence computation
- Symbolic curl computation
- Results panel with final answers and step-by-step derivations
- Error handling for invalid expressions

## Deliverables
- Working desktop window with vector field input
- compute buttons for divergence and curl
- parsed field preview
- derivation display for both operations
- inline error reporting

## Tasks
1. Set up the application skeleton
   - Create the PySide6 application entry point
   - Define main window class and layout
   - Add placeholder input fields and buttons
2. Define supported math environment
   - Establish valid symbol names: `x`, `y`, `z`
   - Create alias mapping for supported functions (`sin`, `cos`, `tan`, `exp`, `log`, `ln`, etc.)
   - Prepare a centralized parsing helper
3. Build input widgets
   - Add labeled text boxes for `P`, `Q`, and `R`
   - Add a preview label that renders `F = <P, Q, R>` after successful parse
   - Connect input change events to validation logic
4. Implement live syntax validation
   - Parse expressions using SymPy on every edit or focus loss
   - Highlight invalid inputs and show the error location/token
   - Prevent computation when any field has invalid syntax
5. Implement divergence computation
   - Construct `div(F) = ∂P/∂x + ∂Q/∂y + ∂R/∂z`
   - Simplify the result using SymPy
   - Build step-by-step output with each derivative and the simplification path
6. Implement curl computation
   - Build the standard curl vector formula:
     - `(∂R/∂y - ∂Q/∂z, ∂P/∂z - ∂R/∂x, ∂Q/∂x - ∂P/∂y)`
   - Simplify each component
   - Build step-by-step output including determinant form and intermediate derivatives
7. Create the result display panel
   - Show final simplified expressions for divergence and curl
   - Show the formula used and intermediate steps
   - Allow users to copy or inspect step details
8. Validate flow
   - Enter example field values and verify correct divergence/curl output
   - Confirm errors are displayed and blocked appropriately

## Success Criteria
- Users can edit `P`, `Q`, and `R` and immediately see syntax validation
- Divergence and curl compute successfully for valid fields
- Computation results are simplified and displayed clearly
- Derivation steps are accessible and correct
- Invalid input prevents computation and shows a clear error message
