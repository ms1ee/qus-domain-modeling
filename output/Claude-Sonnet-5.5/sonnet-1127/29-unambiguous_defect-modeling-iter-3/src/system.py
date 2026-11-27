"""System management."""
import json
import globalvar
from rider import Rider

RIDER_COST = 500
CONFIG_FILE = "state.json"


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 10000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


def recruit_rider():
    """Create a rider if funds allow; return it or None."""
    funds = globalvar.get_value("funds", 0)
    if funds < RIDER_COST:
        return None
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    globalvar.set_value("funds", funds - RIDER_COST)
    r = Rider(rid)
    globalvar.get_value("riders").append(r)
    return r


def tick():
    """Advance simulated time by one tick."""
    globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def save_state(path=CONFIG_FILE):
    """Persist state as JSON."""
    data = {
        "funds": globalvar.get_value("funds"),
        "tick": globalvar.get_value("tick"),
        "riders": [{"rider_id": r.rider_id, "x": r.x, "y": r.y,
                    "speed": r.speed, "state": r.state,
                    "special_case": r.special_case,
                    "orders": [o.id for o in r.orders]}
                   for r in globalvar.get_value("riders")],
        "orders": [o.to_dict() for o in globalvar.get_value("orders")],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
