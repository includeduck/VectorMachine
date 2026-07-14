# Milestone 2 Plan

## Goal
Add session persistence, example field loading, and reset behavior so users can save and restore work, populate sample problems, and clear application inputs safely.

## Scope
- Save current session to disk
- Open a saved session and restore state
- Load predefined example vector fields
- Clear all inputs, results, and preview state
- Persist theme setting selection across sessions

## Deliverables
- Save Session button/workflow
- Open Session button/workflow
- Example field menu or quick actions
- Clear button that resets the application state
- Session restore updates UI and results correctly

## Tasks
1. Define session data model
   - Create a session schema with `P`, `Q`, `R`, `results`, `timestamp`, and optional `theme`
   - Select serialization format: JSON for ease of readability and cross-platform compatibility
2. Implement Save Session
   - Add Save Session control to UI
   - Serialize the current field expressions and computed results
   - Include a timestamp and metadata in the saved file
   - Use a file save dialog for user-selected storage location
3. Implement Open Session
   - Add Open Session control to UI
   - Read saved session files and validate the contents
   - Restore `P`, `Q`, and `R`, plus previously computed results
   - Update preview, results panel, and theme state as needed
4. Implement Load Example actions
   - Add at least three built-in example vector fields:
     - `<x, y, z>`
     - `<y*z, x^2, sin(x)>`
     - `<exp(x*y), ln(z), x*z>`
   - Add a selection menu or button group for examples
   - Load example values and run validation immediately
   - Clear old computation results when a new example is selected
5. Implement Clear Input
   - Add a Clear action button or menu item
   - Reset all input fields and validation messages
   - Clear result displays, derivation panels, and previews
   - Confirm that no stale data remains in the UI
6. Persist theme selection
   - Store theme preference alongside session data or via a separate local config file
   - Restore theme when application starts
   - Ensure theme persistence works after Save/Open operations
7. Test session flows
   - Save a session with expressions and results, then reopen it and verify all data restores
   - Load each example and confirm validation and preview updates
   - Clear the UI and verify all fields and result panels are reset

## Success Criteria
- Saved sessions can be opened to restore the full working state
- Example vector fields populate the inputs and show correct previews
- Clear resets every input and result without leaving stale state
- Theme settings persist and restore across launches
- Session file format is reusable and readable
