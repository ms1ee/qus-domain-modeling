"""System management: initialization, recruitment and ticking."""
import json

import globalvar

INITIAL_FUNDS = 10000
RIDER_COST = 100
MAX_RIDERS = 20


def init_system():
    """Initialise all global parameters."""
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("history", [])


def recruit_rider():
    """Recruit a new rider if funds allow; return it or None."""
    from rider import Rider
    funds = globalvar.get_value("funds", 0)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if funds < RIDER_COST or len(riders) >= MAX_RIDERS:
        return None
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    globalvar.set_value("funds", funds - RIDER_COST)
    r = Rider(rid)
    riders.append(r)
    return r


def tick(n=1):
    """Advance simulation by n ticks."""
    for _ in range(n):
        globalvar.set_value("tick", globalvar.get_value("tick", 0) + 1)
        for r in list(globalvar.get_value("riders", [])):
            r.move()


def save_state(path="state.json"):
    """Persist system state as JSON."""
    data = {
        "funds": globalvar.get_value("funds"),
        "tick": globalvar.get_value("tick"),
        "riders": [{"id": r.rider_id, "x": r.x, "y": r.y, "speed": r.speed,
                    "state": r.state, "log": r.log}
                   for r in globalvar.get_value("riders", [])],
        "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
