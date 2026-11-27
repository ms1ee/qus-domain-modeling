"""JSON persistence of system state."""

import json
import logging

import globalvar
from config import get_config

logger = logging.getLogger(__name__)


def build_state():
    """Build a serialisable snapshot of the system."""
    return {
        "config": get_config(),
        "time": globalvar.get_value("time", 0),
        "funds": globalvar.get_value("funds", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "riders": [r.to_dict() for r in (globalvar.get_value("riders") or [])],
        "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
    }


def save_state(path=None):
    """Save state to JSON. Returns the path written, or None on failure."""
    path = path or get_config().get("state_file", "dispatch_state.json")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(build_state(), fh, indent=2)
        return path
    except OSError as exc:
        logger.error("Failed to save state to %s: %s", path, exc)
        return None
