"""System initialisation and management."""
import json

import globalvar

RECRUIT_COST = 300


def init_system():
    """Initialise all global parameters."""
    globalvar._init()
    return True


def recruit_rider():
    """Create a new rider, deducting cost. Returns Rider or None."""
    from rider import Rider
    funds = globalvar.get_value("funds")
    if funds < RECRUIT_COST:
        return None
    rid = globalvar.get_value("rider_id_counter")
    globalvar.set_value("rider_id_counter", rid + 1)
    globalvar.set_value("funds", funds - RECRUIT_COST)
    r = Rider(rid)
    globalvar.get_value("riders").append(r)
    return r


def tick():
    """Advance the simulation by one tick."""
    globalvar.set_value("time", globalvar.get_value("time") + 1)
    for r in list(globalvar.get_value("riders")):
        try:
            r.move()
        except Exception as exc:  # error recovery
            r.state = 0
            r.orders = []
            print("Recovered rider %s: %s" % (r.rider_id, exc))


def save_state(path="state.json"):
    """Persist state to a JSON file."""
    data = {
        "funds": globalvar.get_value("funds"),
        "time": globalvar.get_value("time"),
        "riders": [r.to_dict() for r in globalvar.get_value("riders")],
        "orders": [o.to_dict() for o in globalvar.get_value("orders")],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
