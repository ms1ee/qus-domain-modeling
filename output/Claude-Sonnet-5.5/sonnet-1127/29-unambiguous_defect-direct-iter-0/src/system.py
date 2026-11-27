"""System management."""
import json
import globalvar
from rider import Rider

RIDER_COST = 500
INITIAL_FUNDS = 10000
MAX_RIDERS = 12


def init_system():
    """Initialize global state."""
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Manages funds, riders and persistence."""

    @staticmethod
    def recruit_rider():
        """Recruit a rider if funds allow; return it or None."""
        riders = globalvar.get_value("riders")
        funds = globalvar.get_value("funds")
        if riders is None or funds is None:
            init_system()
            riders = globalvar.get_value("riders")
            funds = globalvar.get_value("funds")
        if funds < RIDER_COST or len(riders) >= MAX_RIDERS:
            return None
        rid = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rid)
        globalvar.set_value("funds", funds - RIDER_COST)
        r = Rider(rid)
        riders.append(r)
        return r

    @staticmethod
    def tick():
        """Advance simulated time and move riders."""
        globalvar.set_value("time", (globalvar.get_value("time", 0) or 0) + 1)
        for r in globalvar.get_value("riders", []):
            r.move()

    @staticmethod
    def save(path="state.json"):
        """Persist state to JSON."""
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "log": r.log} for r in globalvar.get_value("riders", [])],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
