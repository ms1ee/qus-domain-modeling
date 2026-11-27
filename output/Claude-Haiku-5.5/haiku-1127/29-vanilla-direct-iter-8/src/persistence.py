"""JSON persistence of system parameters, riders and order history."""

import json
import logging
import os

import globalvar
from config import SETTINGS

logger = logging.getLogger(__name__)


def build_state_snapshot():
    """Build a JSON-serializable snapshot of the whole system state.

    Returns:
        dict: Settings, funds, clock, rider list and order history.
    """
    riders = []
    for rider in globalvar.get_value("riders") or []:
        riders.append({
            "rider_id": rider.rider_id,
            "x": rider.x,
            "y": rider.y,
            "speed": rider.speed,
            "state": rider.state,
            "special_case": rider.special_case,
            "orders": [order.id for order in rider.orders],
            "log": rider.log,
        })
    orders = [order.to_dict() for order in globalvar.get_value("orders") or []]
    return {
        "settings": dict(SETTINGS),
        "funds": globalvar.get_value("funds"),
        "tick": globalvar.get_value("tick"),
        "rider_id_counter": globalvar.get_value("rider_id_counter"),
        "riders": riders,
        "orders": orders,
    }


def save_state(path=None):
    """Write the system snapshot to a JSON file atomically.

    Args:
        path: Destination file; defaults to ``SETTINGS["state_file"]``.

    Returns:
        str: The path that was written.

    Raises:
        OSError: If the file cannot be written.
    """
    path = path or SETTINGS["state_file"]
    temp_path = path + ".tmp"
    snapshot = build_state_snapshot()
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)
    os.replace(temp_path, path)
    logger.info("State saved to %s", path)
    return path
