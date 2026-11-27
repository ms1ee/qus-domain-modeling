"""JSON persistence for system state."""

import json

import globalvar
from order_model import Order
from rider import Rider


def save_state(path):
    """Save funds, config, riders and orders to a JSON file."""
    data = {
        "funds": globalvar.get_value("funds"),
        "config": globalvar.get_value("config"),
        "rider_id_counter": globalvar.get_value("rider_id_counter"),
        "order_id_counter": globalvar.get_value("order_id_counter"),
        "current_tick": globalvar.get_value("current_tick"),
        "orders": [o.to_dict() for o in globalvar.get_value("orders") or []],
        "riders": [r.to_dict() for r in globalvar.get_value("riders") or []],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_state(path):
    """Load state saved by :func:`save_state`."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    globalvar.set_value("funds", data.get("funds", 1000))
    if data.get("config"):
        globalvar.set_value("config", data["config"])
    globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
    globalvar.set_value("order_id_counter", data.get("order_id_counter", 0))
    globalvar.set_value("current_tick", data.get("current_tick", 0))
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
    globalvar.set_value("running", True)
