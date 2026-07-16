# Milestone 3 Plan

## Goal
Implement visualization and export capabilities so users can inspect vector fields graphically and save results in useful formats.

## Scope
- 2D and 3D vector field visualization
- Visualization controls for density, scale, and domain
- Export results to Markdown, plain text, PNG, and PDF
- Integrated UI for generating exports from computed data

## Deliverables
- Visualization panel embedded in the desktop app
- controls for rendering mode, density, and domain
- export commands for Markdown, text, image, and PDF
- export files containing expressions, formula, derivations, and results

## Tasks
1. Design the visualization panel
   - Add a dedicated pane or tab for visualization
   - Include toggle buttons or selectors for 2D and 3D render modes
   - Add controls for arrow density, scale, and domain bounds
2. Integrate PyVista with PySide6
   - Embed a PyVista render window within the Qt layout
   - Initialize the 3D renderer and add a scene camera
   - Create safe fallback if PyVista cannot initialize
3. Implement 2D visualization mode
   - Generate a 2D quiver plot for the vector field over a sample plane
   - Use NumPy to evaluate the vector field on a grid
   - Display arrows, optionally with a Matplotlib or PyVista 2D renderer
4. Implement 3D visualization mode
   - Sample the vector field on a 3D grid or set of points
   - Render arrow glyphs in PyVista
   - Enable rotate, zoom, and pan interactions
   - Update the scene when the field or visualization settings change
5. Add visualization settings
   - Implement controls for arrow density and scale
   - Allow domain selection for each axis
   - Refresh the visualization immediately when settings change
6. Implement export functionality
   - Add an export menu or actions for each supported format
   - Implement Markdown export with field definitions, formula, derivation, results, and timestamp
   - Implement plain text export with the same information
   - Implement PNG export of the result text or visualization image
   - Implement PDF export using a lightweight generator or leveraging a markdown-to-PDF flow
7. Connect export to computed state
   - Ensure exported content matches the last computed divergence/curl results and derivation steps
   - Include the vector field input values and current date/time
8. Test export and visualization
   - Verify 2D and 3D render modes work for sample fields
   - Confirm export files are generated correctly and open successfully
   - Validate image export from the visualization pane and PDF creation

## Success Criteria
- Users can switch between 2D and 3D visualizations of the vector field
- visualization updates correctly when the field or settings change
- export actions produce valid Markdown, text, PNG, and PDF files
- exported files include full field definitions and computed results
- UI remains responsive when rendering visualizations
