"""System manager and initialization."""
import json

import globalvar

RIDER_COST = 300
MAX_RIDERS = 20


def init_system():
    """Initialise global state."""
    globalvar._init()


def recruit_rider():
    """Create a new rider if funds allow. Returns the Rider or None."""
    from rider import Rider
    funds = globalvar.get_value("funds", 0)
    riders = globalvar.get_value("riders")
    if funds < RIDER_COST or len(riders) >= MAX_RIDERS:
        return None
    rid = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    globalvar.set_value("funds", funds - RIDER_COST)
    r = Rider(rid)
    riders.append(r)
    return r


def tick():
    """Advance simulated time by one tick."""
    globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
    for r in globalvar.get_value("riders"):
        r.move()


class SystemManager:
    """Facade over system-level operations."""

    def __init__(self):
        init_system()

    recruit = staticmethod(recruit_rider)
    tick = staticmethod(tick)

    @staticmethod
    def save(path="config.json"):
        """Persist state as JSON."""
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [r.to_dict() for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
