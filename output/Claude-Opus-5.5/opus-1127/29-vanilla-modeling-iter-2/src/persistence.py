"""JSON persistence of system parameters, riders and order history."""

import json

import globalvar
from order_model import Order
from rider import Rider


def save_state(path):
    """Save the full system state to ``path``."""
    data = {
        "funds": globalvar.get_value("funds", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "order_id_counter": globalvar.get_value("order_id_counter", 0),
        "current_tick": globalvar.get_value("current_tick", 0),
        "config": globalvar.get_value("config", {}),
        "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
        "riders": [r.to_dict() for r in (globalvar.get_value("riders") or [])],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_state(path):
    """Load system state from ``path`` (system must be initialised)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    globalvar.set_value("funds", int(data.get("funds", 0)))
    globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter", 0)))
    globalvar.set_value("order_id_counter", int(data.get("order_id_counter", 0)))
    globalvar.set_value("current_tick", int(data.get("current_tick", 0)))
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
