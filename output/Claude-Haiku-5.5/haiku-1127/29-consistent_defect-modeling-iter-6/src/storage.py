"""JSON persistence: configuration loading and state saving."""

import json
import logging
import os
from typing import Any, Dict

import globalvar

logger = logging.getLogger(__name__)

CONFIG_KEYS = ("recruit_cost", "min_recruit_funds")


def load_config(path: str) -> bool:
    """Load system parameters from a JSON configuration file.

    Recognised keys: ``initial_funds`` (sets current funds), ``recruit_cost``
    and ``min_recruit_funds``. Unknown keys are ignored.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        True if the file was read successfully, False otherwise.
    """
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("could not read config %s: %s", path, exc)
        return False
    if not isinstance(data, dict):
        logger.warning("config %s must contain a JSON object", path)
        return False

    for key in CONFIG_KEYS:
        if key in data:
            value = data[key]
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                globalvar.set_value(key, value)
            else:
                logger.warning("ignoring invalid config value %s=%r", key, value)
    if "initial_funds" in data and isinstance(data["initial_funds"], int):
        globalvar.set_value("funds", data["initial_funds"])
    logger.info("loaded configuration from %s", path)
    return True


def build_snapshot() -> Dict[str, Any]:
    """Build a JSON-serialisable snapshot of parameters, riders and orders."""
    riders = globalvar.get_value("riders") or []
    orders = globalvar.get_value("orders") or []
    return {
        "parameters": {
            "recruit_cost": globalvar.get_value("recruit_cost", 500),
            "min_recruit_funds": globalvar.get_value("min_recruit_funds", 300),
        },
        "funds": globalvar.get_value("funds", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "current_time": globalvar.get_value("current_time", 0),
        "riders": [r.to_dict() for r in riders],
        "orders": [o.to_dict() for o in orders],
    }


def save_state(path: str) -> None:
    """Write the current system state to a JSON file.

    Args:
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    snapshot = build_snapshot()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
    logger.info("saved state to %s", path)
