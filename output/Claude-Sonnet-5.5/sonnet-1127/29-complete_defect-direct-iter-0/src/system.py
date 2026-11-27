"""System manager."""
import json

from . import globalvar
from .rider import Rider

RIDER_COST = 300


class SystemManager:
    """Manages funds, riders and state."""

    def __init__(self):
        init_system()

    @staticmethod
    def recruit():
        """Create riders while funds suffice. Returns list of new riders."""
        new = []
        while globalvar.get_value("funds") >= RIDER_COST:
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            r = Rider(rid)
            globalvar.get_value("riders").append(r)
            globalvar.set_value("funds",
                                globalvar.get_value("funds") - RIDER_COST)
            new.append(r)
            break
        return new

    @staticmethod
    def tick():
        """Advance simulation one tick."""
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    @staticmethod
    def save(path="state.json"):
        """Persist state to JSON."""
        data = {"funds": globalvar.get_value("funds"),
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "time": globalvar.get_value("time"),
                "riders": [r.to_dict() for r in globalvar.get_value("riders")],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", 300)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
