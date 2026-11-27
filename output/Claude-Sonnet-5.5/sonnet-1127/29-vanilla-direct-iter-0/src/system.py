"""System manager."""

import json

import globalvar
from rider import Rider

RIDER_COST = 300


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


def recruit_rider():
    """Create a rider, paying the cost."""
    n = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", n)
    globalvar.set_value("funds", globalvar.get_value("funds") - RIDER_COST)
    rider = Rider(n)
    globalvar.get_value("riders").append(rider)
    return rider


def maybe_recruit(pending):
    """Recruit when funds >= 300 and pending > idle riders."""
    riders = globalvar.get_value("riders")
    idle = sum(1 for r in riders if r.state == 0 and not r.orders)
    if globalvar.get_value("funds") >= RIDER_COST and pending > idle:
        return recruit_rider()
    return None


def tick():
    """Advance simulated time one unit."""
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def save(path="state.json"):
    """Persist state to JSON."""
    data = {"funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "riders": [r.to_dict() for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
