"""SystemManager: funds, riders, simulation ticks and persistence."""

import json

import globalvar
import system


class SystemManager:
    """Core system controller."""

    def __init__(self, config_path=None):
        funds = system.INITIAL_FUNDS
        if config_path:
            try:
                with open(config_path) as f:
                    funds = int(json.load(f).get("funds", funds))
            except (OSError, ValueError):
                pass
        system.init_system(funds)

    def tick(self):
        """Advance simulation one tick."""
        globalvar.set_value("time", globalvar.get_value("time") + 1)
        for r in globalvar.get_value("riders"):
            try:
                r.move()
            except Exception as exc:  # error recovery
                print("Rider %d error: %s" % (r.rider_id, exc))

    def run_until_complete(self, order, limit=10000):
        n = 0
        while order.status != "completed" and n < limit:
            self.tick()
            n += 1
        return n

    def save(self, path="dispatch_data.json"):
        data = {
            "funds": globalvar.get_value("money"),
            "time": globalvar.get_value("time"),
            "riders": [r.to_dict() for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            print("Could not save data: %s" % exc)
