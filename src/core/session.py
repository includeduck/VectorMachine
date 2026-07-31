import json
import os
import tempfile
from datetime import datetime


_DIVERGENCE_KEYS = frozenset({
    "dP_dx", "dQ_dy", "dR_dz", "formula", "unsimplified", "final",
})
_CURL_KEYS = frozenset({
    "dR_dy", "dQ_dz", "dP_dz", "dR_dx", "dQ_dx", "dP_dy",
    "i_comp_unsimplified", "j_comp_unsimplified", "k_comp_unsimplified",
    "i_comp", "j_comp", "k_comp", "final_i", "final_j", "final_k",
})


def _validate_steps(steps, required_keys, name):
    if steps is None:
        return None
    if not isinstance(steps, dict):
        return f"Saved {name} results are malformed."
    if not required_keys <= steps.keys() or not all(
        isinstance(steps[key], str) for key in required_keys
    ):
        return f"Saved {name} results are incomplete."
    return None


def _validate_session_data(data):
    if not isinstance(data, dict):
        return "Session file must contain a JSON object."
    if not all(isinstance(data.get(key, ""), str) for key in ("P", "Q", "R")):
        return "Session field expressions must be text."

    results = data.get("results", {})
    if not isinstance(results, dict):
        return "Session results are malformed."
    return (
        _validate_steps(results.get("divergence"), _DIVERGENCE_KEYS, "divergence")
        or _validate_steps(results.get("curl"), _CURL_KEYS, "curl")
    )


def save_session(filepath, p_str, q_str, r_str, has_results=False, divergence_steps=None, curl_steps=None):
    """
    Saves the current session state to a JSON file.
    """
    data = {
        "timestamp": datetime.now().isoformat(),
        "P": p_str,
        "Q": q_str,
        "R": r_str,
        "has_results": has_results,
        "results": {
            "divergence": divergence_steps,
            "curl": curl_steps
        }
    }
    directory = os.path.dirname(os.path.abspath(filepath))
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".vectormachine-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(data, temporary_file, indent=4, ensure_ascii=False)
            temporary_file.write("\n")
        os.replace(temporary_path, filepath)
    except Exception:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise

def load_session(filepath):
    """
    Loads a session state from a JSON file.
    Returns (data_dict, None) on success, or (None, error_msg) on failure.
    """
    if not os.path.exists(filepath):
        return None, "File does not exist."
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        error = _validate_session_data(data)
        if error:
            return None, error
        return data, None
    except Exception as e:
        return None, f"Failed to load session: {str(e)}"
