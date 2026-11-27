"""System management."""
import json
import globalvar
from rider import Rider

RIDER_COST = 100


def init_system():
    """Initialize global state."""
    globalvar._init()


def recruit_rider():
    """Create a rider if funds allow; return it or None."""
    funds = globalvar.get_value("funds")
    if funds < RIDER_COST:
        return None
    cid = globalvar.get_value("rider_id_counter") + 1
    globalvar.set_value("rider_id_counter", cid)
    globalvar.set_value("funds", funds - RIDER_COST)
    r = Rider(cid)
    globalvar.get_value("riders").append(r)
    return r


class SystemManager:
    """Manage funds, riders and ticks."""

    def __init__(self):
        init_system()

    def tick(self):
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    def save(self, path="config.json"):
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "log": r.log} for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
