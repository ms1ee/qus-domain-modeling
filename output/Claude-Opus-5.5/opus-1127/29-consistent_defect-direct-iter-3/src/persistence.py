"""JSON persistence of configuration and system state."""

import json
import os

import globalvar
from order_model import Order
from rider import Rider

CONFIG_KEYS = ("funds", "rider_speed", "recruit_cost", "recruit_threshold",
               "rider_start")


def load_config(path):
    """Apply system parameters from a JSON config file if it exists."""
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key in CONFIG_KEYS:
        if key in data:
            value = data[key]
            if key == "rider_start":
                value = tuple(int(v) for v in value)
            globalvar.set_value(key, value)
    return True


def save_state(path):
    """Write funds, riders and order history to a JSON file."""
    data = {
        "funds": globalvar.get_value("funds"),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "current_time": globalvar.get_value("current_time", 0),
        "riders": [r.to_dict() for r in globalvar.get_value("riders") or []],
        "orders": [o.to_dict() for o in globalvar.get_value("orders") or []],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_state(path):
    """Restore state written by :func:`save_state`."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    orders = [Order.from_dict(o) for o in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = []
    for rd in data.get("riders", []):
        rider = Rider(rd["rider_id"], rd["x"], rd["y"], rd.get("speed"))
        rider.state = rd.get("state", 0)
        rider.special_case = rd.get("special_case", False)
        rider.total_distance = rd.get("total_distance", 0)
        rider.orders = [by_id[i] for i in rd.get("orders", []) if i in by_id]
        cur = rd.get("current_order")
        rider.current_order = by_id.get(cur) if cur is not None else None
        rider.log = rd.get("log", rider.log)
        riders.append(rider)
    globalvar.set_value("funds", data.get("funds", 1000))
    globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
    globalvar.set_value("current_time", data.get("current_time", 0))
    globalvar.set_value("riders", riders)
    globalvar.set_value("orders", orders)
