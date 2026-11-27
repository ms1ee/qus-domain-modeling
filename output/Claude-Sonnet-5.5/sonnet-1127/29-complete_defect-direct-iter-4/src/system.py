"""System manager."""
import json
import globalvar
from rider import Rider

RECRUIT_COST = 300


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", 300)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)


class SystemManager:
    """Funds, riders and ticking."""

    @staticmethod
    def add_rider():
        n = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", n)
        r = Rider(n)
        globalvar.get_value("riders").append(r)
        return r

    @staticmethod
    def auto_recruit():
        """Recruit riders while funds >= 300. Returns number added."""
        count = 0
        while globalvar.get_value("funds", 0) >= RECRUIT_COST:
            globalvar.set_value(
                "funds", globalvar.get_value("funds") - RECRUIT_COST)
            SystemManager.add_rider()
            count += 1
        return count

    @staticmethod
    def tick():
        """Advance simulated time one unit."""
        globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
        for r in globalvar.get_value("riders", []):
            r.move()

    @staticmethod
    def save(path="state.json"):
        data = {"funds": globalvar.get_value("funds"),
                "time": globalvar.get_value("time"),
                "riders": [r.to_dict() for r in globalvar.get_value("riders")],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
