"""JSON persistence for system parameters, riders and order history."""

import json
import logging
import os
import tempfile
from typing import Any, Dict

import globalvar

LOGGER = logging.getLogger("dispatch.persistence")

CONFIG_KEYS = ("initial_funds", "recruit_cost", "recruit_threshold")


def load_config(path: str) -> Dict[str, int]:
    """Load system parameter overrides from a JSON file.

    Missing or malformed files produce a warning and an empty configuration
    so that the system falls back to its defaults.

    Args:
        path: Path to the JSON configuration file (may be None).

    Returns:
        Dictionary of recognised integer parameters.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Could not read config %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        LOGGER.warning("Config %s must contain a JSON object", path)
        return {}

    config: Dict[str, int] = {}
    for key in CONFIG_KEYS:
        if key in data:
            try:
                config[key] = int(data[key])
            except (TypeError, ValueError):
                LOGGER.warning("Ignoring non-integer config value for %s",
                               key)
    return config


def build_snapshot() -> Dict[str, Any]:
    """Build a JSON-serialisable snapshot of the current system state."""
    riders = globalvar.get_value("riders", []) or []
    orders = globalvar.get_value("orders", []) or []
    pending = globalvar.get_value("pending_orders", []) or []
    return {
        "funds": globalvar.get_value("funds", 0),
        "simulated_time": globalvar.get_value("simulated_time", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "riders": [rider.to_dict() for rider in riders],
        "orders": [order.to_dict() for order in orders],
        "pending_order_ids": [order.id for order in pending],
    }


def save_state(path: str) -> None:
    """Write the system snapshot to ``path`` atomically.

    Args:
        path: Destination JSON file.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    snapshot = build_snapshot()
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
        os.replace(tmp_path, path)
    except OSError:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    LOGGER.info("State saved to %s", path)
