"""JSON persistence for system parameters, riders and order history."""

import json
import logging
import os

import config
import globalvar
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)

SAVE_VERSION = 1


def save_state(path=None):
    """Save settings, funds, clock, riders and orders to a JSON file.

    Args:
        path: Target file path; defaults to SETTINGS['save_file'].

    Returns:
        The path that was written.

    Raises:
        OSError: If the file cannot be written.
    """
    path = path or config.SETTINGS["save_file"]
    riders = globalvar.get_value("riders") or []
    orders = globalvar.get_value("orders") or []
    data = {
        "version": SAVE_VERSION,
        "settings": dict(config.SETTINGS),
        "funds": int(globalvar.get_value("funds") or 0),
        "current_tick": int(globalvar.get_value("current_tick") or 0),
        "rider_id_counter": int(globalvar.get_value("rider_id_counter") or 0),
        "order_id_counter": int(globalvar.get_value("order_id_counter") or 0),
        "riders": [
            {
                "rider_id": r.rider_id,
                "x": r.x,
                "y": r.y,
                "speed": r.speed,
                "state": r.state,
                "special_case": r.special_case,
                "order_ids": [o.order_id for o in r.orders],
            }
            for r in riders
        ],
        "orders": [o.to_dict() for o in orders],
    }
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp_path, path)
    logger.info("State saved to %s", path)
    return path


def load_state(path=None):
    """Load a saved state, replacing the current in-memory state.

    The new state is fully built before any global is replaced, so a corrupt
    file leaves the current state untouched.

    Args:
        path: Source file path; defaults to SETTINGS['save_file'].

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file content is invalid.
    """
    path = path or config.SETTINGS["save_file"]
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid save file: {exc}") from exc
    try:
        orders = [Order.from_dict(od) for od in data.get("orders", [])]
        orders_by_id = {o.order_id: o for o in orders}
        riders = []
        for rd in data.get("riders", []):
            rider = Rider(int(rd["rider_id"]))
            rider.x = int(rd["x"])
            rider.y = int(rd["y"])
            rider.speed = int(rd["speed"])
            rider.state = int(rd["state"])
            rider.special_case = bool(rd.get("special_case", False))
            rider.orders = [orders_by_id[oid] for oid in rd.get("order_ids", [])
                            if oid in orders_by_id]
            riders.append(rider)
        funds = int(data["funds"])
        tick = int(data["current_tick"])
        rider_counter = int(data["rider_id_counter"])
        order_counter = int(data["order_id_counter"])
        settings = data.get("settings", {})
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Corrupt save file: {exc}") from exc

    for key in config.SETTINGS:
        if key in settings and isinstance(settings[key], type(config.SETTINGS[key])):
            config.SETTINGS[key] = settings[key]
    globalvar.set_value("funds", funds)
    globalvar.set_value("current_tick", tick)
    globalvar.set_value("rider_id_counter", rider_counter)
    globalvar.set_value("order_id_counter", order_counter)
    globalvar.set_value("riders", riders)
    globalvar.set_value("orders", orders)
    logger.info("State loaded from %s", path)
