import json
import os
from datetime import datetime

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
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def load_session(filepath):
    """
    Loads a session state from a JSON file.
    Returns (data_dict, None) on success, or (None, error_msg) on failure.
    """
    if not os.path.exists(filepath):
        return None, "File does not exist."
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        return None, f"Failed to load session: {str(e)}"
