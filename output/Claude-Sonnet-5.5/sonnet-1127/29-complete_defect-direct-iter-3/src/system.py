"""System manager."""
import json

from src import globalvar
from src.rider import Rider

RIDER_COST = 300
INITIAL_FUNDS = 300
ORDER_REVENUE = 100


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("funds", INITIAL_FUNDS)


class SystemManager:
    """Manages funds, riders and the simulation clock."""

    def __init__(self):
        init_system()

    def recruit_if_possible(self):
        """Create a rider while funds >= 300. Returns number added."""
        added = 0
        while globalvar.get_value("funds") >= RIDER_COST:
            globalvar.set_value("funds", globalvar.get_value("funds")
                                - RIDER_COST)
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.get_value("riders").append(Rider(rid))
            added += 1
        return added

    def add_funds(self, amount):
        """Add funds (may be negative)."""
        globalvar.set_value("funds", globalvar.get_value("funds") + amount)

    def tick(self):
        """Advance one time unit."""
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            before = len(r.orders)
            try:
                r.move()
            except Exception:  # recover to consistent state
                r.state = 0
                r.path = []
            if len(r.orders) < before:
                self.add_funds(ORDER_REVENUE)
        self.recruit_if_possible()

    def save(self, path="state.json"):
        """Persist state as JSON."""
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "log": r.log}
                       for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
