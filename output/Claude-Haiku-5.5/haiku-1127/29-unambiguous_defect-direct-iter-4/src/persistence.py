"""JSON persistence: configuration loading and state snapshots."""

import json
import logging
import os

import globalvar

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_STATE_PATH = os.path.join(BASE_DIR, "state.json")


def load_config(path=CONFIG_PATH):
    """Load system parameters from a JSON configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        Dictionary of parameters; empty if the file is missing or invalid.
    """
    if not os.path.exists(path):
        logger.info("No configuration file at %s; using defaults", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("Configuration %s must contain a JSON object", path)
        return {}
    return data


def build_snapshot():
    """Build a JSON-serialisable snapshot of the current simulation state."""
    riders = globalvar.get_value("riders") or []
    orders = globalvar.get_value("orders") or []
    return {
        "tick": globalvar.get_value("tick") or 0,
        "funds": globalvar.get_value("funds") or 0,
        "rider_id_counter": globalvar.get_value("rider_id_counter") or 0,
        "riders": [rider.to_dict() for rider in riders],
        "orders": [order.to_dict() for order in orders],
    }


def save_state(path=DEFAULT_STATE_PATH):
    """Write the simulation snapshot to a JSON file.

    Args:
        path: Destination file path.

    Returns:
        The path written to.

    Raises:
        OSError: If the file cannot be written.
    """
    snapshot = build_snapshot()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
    logger.info("State saved to %s", path)
    return path
