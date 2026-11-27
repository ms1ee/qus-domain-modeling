"""Configuration loading and JSON persistence of system state."""

import json
import logging
import os

import globalvar

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "rider_speed": 20,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
    "state_file": "dispatch_state.json",
}

logger = logging.getLogger("dispatch.config")


def load_config(path=CONFIG_FILE):
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        Dict of configuration values.
    """
    settings = dict(DEFAULT_CONFIG)
    if not os.path.exists(path):
        return settings
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s: %s; using defaults", path, exc)
        return settings
    if not isinstance(data, dict):
        logger.warning("Config %s is not a JSON object; using defaults", path)
        return settings
    for key in DEFAULT_CONFIG:
        if key in data:
            settings[key] = data[key]
    return settings


def snapshot_state():
    """Build a JSON-serialisable snapshot of the current system state.

    Returns:
        Dict containing funds, time, riders (with logs) and order history.
    """
    riders = globalvar.get_value("riders") or []
    orders = globalvar.get_value("orders") or []
    pending = globalvar.get_value("pending_orders") or []
    return {
        "funds": globalvar.get_value("funds"),
        "time": globalvar.get_value("time"),
        "rider_id_counter": globalvar.get_value("rider_id_counter"),
        "riders": [
            {
                "rider_id": rider.rider_id,
                "x": rider.x,
                "y": rider.y,
                "speed": rider.speed,
                "state": rider.state,
                "special_case": rider.special_case,
                "order_ids": [order.id for order in rider.orders],
                "log": rider.log,
            }
            for rider in riders
        ],
        "orders": [order.to_dict() for order in orders],
        "pending_order_ids": [order.id for order in pending],
    }


def save_state(path, data=None):
    """Write the system state to a JSON file atomically.

    Args:
        path: Destination file path.
        data: Optional pre-built snapshot; built from globals when omitted.

    Raises:
        OSError: If the file cannot be written.
    """
    if data is None:
        data = snapshot_state()
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp_path, path)
    logger.info("State saved to %s", path)
