"""System management."""

import json
import globalvar
from rider import Rider

RIDER_COST = 300
ORDER_FEE = 100
INITIAL_FUNDS = 300


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Manages funds, riders and time."""

    def check_recruit(self):
        """Recruit riders while funds >= 300. Returns number added."""
        added = 0
        while globalvar.get_value("funds", 0) >= RIDER_COST:
            globalvar.set_value("funds",
                                globalvar.get_value("funds") - RIDER_COST)
            cid = globalvar.get_value("rider_id_counter", 0) + 1
            globalvar.set_value("rider_id_counter", cid)
            globalvar.get_value("riders").append(Rider(cid))
            added += 1
        return added

    def add_funds(self, amount):
        globalvar.set_value("funds", globalvar.get_value("funds", 0) + amount)

    def tick(self):
        """Advance one time unit."""
        globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
        for r in globalvar.get_value("riders", []):
            r.move()

    def busy(self):
        return any(r.orders for r in globalvar.get_value("riders", []))

    def save(self, path):
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [{"rider_id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "special_case": r.special_case,
                        "orders": [o.id for o in r.orders]}
                       for r in globalvar.get_value("riders", [])],
            "orders": [o.to_dict()
                       for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
