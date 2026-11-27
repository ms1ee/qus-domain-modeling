"""System parameters and JSON persistence helpers.

Parameters can be overridden by a JSON configuration file. Unknown keys are
ignored with a warning. The current state (funds, riders, orders) can be
written to a JSON state file on exit.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "rider_cost": 300,
    "order_revenue": 100,
    "rider_speed": 50,
    "max_orders_per_rider": 3,
    "load_penalty": 150,
    "late_threshold_ticks": 60,
    "late_penalty": 20,
    "max_wait_ticks": 3,
    "state_file": "dispatch_state.json",
    "log_file": "dispatch.log",
}

# Active configuration; modules read values from here at use time.
CONFIG: Dict[str, Any] = dict(DEFAULT_CONFIG)

_POSITIVE_KEYS = ("rider_speed", "max_orders_per_rider")


def load_config(path: str) -> bool:
    """Load parameter overrides from a JSON configuration file.

    The file may either be a flat JSON object or contain the overrides under
    a ``"parameters"`` key.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        True if the file existed and was applied, False if it was absent.

    Raises:
        ValueError: If the JSON is malformed or a value has an invalid type.
        OSError: If the file cannot be read.
    """
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration file must contain a JSON object")
    params = data.get("parameters", data)
    if not isinstance(params, dict):
        raise ValueError("'parameters' must be a JSON object")

    for key, value in params.items():
        if key not in DEFAULT_CONFIG:
            logger.warning("Ignoring unknown configuration key '%s'", key)
            continue
        default = DEFAULT_CONFIG[key]
        if isinstance(default, int):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"'{key}' must be an integer")
            if value < 0 or (key in _POSITIVE_KEYS and value < 1):
                raise ValueError(f"'{key}' is out of the allowed range")
        elif isinstance(default, str) and not isinstance(value, str):
            raise ValueError(f"'{key}' must be a string")
        CONFIG[key] = value
    logger.info("Configuration loaded from %s", path)
    return True


def save_state(path: str, state: Dict[str, Any]) -> None:
    """Write the system state to a JSON file atomically.

    Args:
        path: Destination file path.
        state: JSON-serialisable dictionary describing the system state.

    Raises:
        OSError: If the file cannot be written.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp_path, path)
    logger.info("State saved to %s", path)
