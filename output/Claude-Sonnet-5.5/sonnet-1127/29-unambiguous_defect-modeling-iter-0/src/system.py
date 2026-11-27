"""System management: funds, riders, persistence."""
import json
import globalvar
from rider import Rider

INITIAL_FUNDS = 10000
RECRUIT_COST = 500
MAX_RIDERS = 20


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("recruit_cost", RECRUIT_COST)


def recruit_rider():
    """Recruit a rider if funds allow; return Rider or None."""
    funds = globalvar.get_value("funds", 0)
    riders = globalvar.get_value("riders")
    if funds < RECRUIT_COST or len(riders) >= MAX_RIDERS:
        return None
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    globalvar.set_value("funds", funds - RECRUIT_COST)
    r = Rider(rid)
    riders.append(r)
    return r


def tick():
    """Advance simulated time by one tick."""
    globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def save(path="config.json"):
    """Persist system data as JSON."""
    data = {"funds": globalvar.get_value("funds"),
            "tick": globalvar.get_value("tick"),
            "riders": [r.to_dict() for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
