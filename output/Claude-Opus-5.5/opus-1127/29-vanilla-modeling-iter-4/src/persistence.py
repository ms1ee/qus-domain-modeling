"""JSON persistence of system parameters, riders and order history."""

import json

import globalvar
from order_model import Order
from rider import Rider


def save_state(path):
    """Write the full system state to ``path`` as JSON."""
    data = {
        "config": globalvar.get_value("config") or {},
        "funds": globalvar.get_value("funds", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "order_id_counter": globalvar.get_value("order_id_counter", 0),
        "tick": globalvar.get_value("tick", 0),
        "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
        "riders": [r.to_dict() for r in (globalvar.get_value("riders") or [])],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return path


def load_state(path):
    """Load system state from ``path`` into the global store."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("config"):
        globalvar.set_value("config", data["config"])
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
    globalvar.set_value("funds", int(data.get("funds", 0)))
    globalvar.set_value("rider_id_counter", int(data.get("rider_id_counter", 0)))
    globalvar.set_value("order_id_counter",
                        max([int(data.get("order_id_counter", 0))] + [o.id for o in orders]))
    globalvar.set_value("tick", int(data.get("tick", 0)))
    globalvar.set_value("running", True)
    return len(riders), len(orders)
