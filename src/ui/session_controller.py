"""Saving and opening sessions, without any dialogs.

Opening applies the trust rule from the bug audit: saved result strings are
never displayed.  The saved field is restored, and every result the session
had is recomputed from it.
"""

from src.core.session import load_session, save_session

RESULT_TYPES = ("divergence", "curl")


class SessionLoadError(Exception):
    pass


class SessionController:
    def __init__(self, input_panel, compute):
        self._input_panel = input_panel
        self._compute = compute

    def save(self, file_path, div_steps, curl_steps):
        """Write the current field and results.  Raises ``OSError``."""
        p, q, r = self._input_panel.get_texts()
        save_session(
            file_path, p, q, r,
            has_results=div_steps is not None or curl_steps is not None,
            divergence_steps=div_steps,
            curl_steps=curl_steps,
        )

    def open(self, file_path):
        """Restore a session and start recomputing its results.

        Returns the message to show the user.  Raises ``SessionLoadError``
        if the file can't be loaded.
        """
        data, error = load_session(file_path)
        if error:
            raise SessionLoadError(error)

        if self._compute.is_busy:
            self._compute.cancel()
        self._input_panel.set_texts(data.get("P", ""), data.get("Q", ""), data.get("R", ""))

        results = data.get("results", {})
        saved = [name for name in RESULT_TYPES if results.get(name)]
        if not saved:
            return "Session loaded successfully."
        if not self._input_panel.is_valid():
            return (
                "Session loaded, but its saved results were not restored "
                "because the vector field is invalid."
            )
        self._compute.run_sequence(saved, *self._input_panel.get_expressions())
        return "Session loaded successfully."
