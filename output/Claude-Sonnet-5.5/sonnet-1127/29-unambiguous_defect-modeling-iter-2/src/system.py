"""System management."""
import json

import globalvar
from rider import Rider

INITIAL_FUNDS = 10000
RIDER_COST = 500


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)


def recruit_rider():
    """Recruit a rider if funds allow; return it or None."""
    funds = globalvar.get_value("funds")
    if funds < RIDER_COST:
        return None
    cid = globalvar.get_value("rider_id_counter") + 1
    globalvar.set_value("rider_id_counter", cid)
    globalvar.set_value("funds", funds - RIDER_COST)
    r = Rider(cid)
    globalvar.get_value("riders").append(r)
    return r


def tick():
    """Advance simulation by one tick."""
    globalvar.set_value("tick", globalvar.get_value("tick") + 1)
    for r in globalvar.get_value("riders"):
        r.move()


def save_state(path):
    """Persist state as JSON."""
    data = {
        "funds": globalvar.get_value("funds"),
        "tick": globalvar.get_value("tick"),
        "riders": [{"id": r.rider_id, "x": r.x, "y": r.y, "speed": r.speed,
                    "state": r.state, "log": r.log}
                   for r in globalvar.get_value("riders")],
        "orders": [{"id": o.id, "res": o.res_pos, "cus": o.cus_pos,
                    "start": o.start_time, "end": o.completion_time,
                    "distance": o.distance, "status": o.status,
                    "rider": o.rider_id}
                   for o in globalvar.get_value("orders")],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
