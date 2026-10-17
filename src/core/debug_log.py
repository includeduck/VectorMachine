import json
import os
import time

_LOG_PATH = os.environ.get("VECTORMACHINE_DEBUG_LOG")
_SESSION_ID = os.environ.get("VECTORMACHINE_DEBUG_SESSION", "local")


def debug_log(location, message, data=None, hypothesis_id="", run_id="pre-fix"):
    """Write diagnostic data only when an explicit log path is configured."""
    if not _LOG_PATH:
        return
    try:
        entry = {
            "sessionId": _SESSION_ID,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
            "hypothesisId": hypothesis_id,
            "runId": run_id,
        }
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
