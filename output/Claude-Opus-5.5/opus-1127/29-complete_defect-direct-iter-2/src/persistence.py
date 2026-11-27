"""JSON persistence of system parameters, riders and order history."""

import json

import config
import globalvar
from order_model import Order
from rider import Rider


def save_state(path=None):
    """Save the full system state to a JSON file; returns the path."""
    path = path or config.STATE_FILE
    data = {
        "system": {
            "funds": globalvar.get_value("funds", 0),
            "tick": globalvar.get_value("tick", 0),
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "rider_cost": config.RIDER_COST,
            "order_fee": config.ORDER_FEE,
            "rider_speed": config.RIDER_SPEED,
        },
        "orders": [o.to_dict() for o in globalvar.get_value("orders") or []],
        "riders": [r.to_dict() for r in globalvar.get_value("riders") or []],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return path


def load_state(path=None):
    """Load system state from a JSON file previously written by save."""
    path = path or config.STATE_FILE
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    sysd = data.get("system", {})
    Order.reset_counter()
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    globalvar.set_value("funds", int(sysd.get("funds", 0)))
    globalvar.set_value("tick", int(sysd.get("tick", 0)))
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    counter = int(sysd.get("rider_id_counter", 0))
    if riders:
        counter = max(counter, max(r.rider_id for r in riders))
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
    globalvar.set_value("running", True)
    return path
