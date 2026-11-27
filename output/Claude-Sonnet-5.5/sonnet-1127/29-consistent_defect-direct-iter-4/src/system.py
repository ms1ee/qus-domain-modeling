"""System initialization and management."""
import json

import globalvar


def init_system():
    """Initialize global parameters."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Manages funds, riders and running state."""

    def __init__(self):
        init_system()

    def tick(self):
        """Advance simulated time one unit and move all riders."""
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    def save(self, path="config.json"):
        """Persist system state to JSON."""
        data = {
            "funds": globalvar.get_value("funds"),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "riders": [r.to_dict() for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
