"""System manager."""
import json

import globalvar
from gridmap import GridMap
from order import OrderManager
from order_model import reset_counter
from pathplanner import PathPlanner
from rider import Rider

SAVE_FILE = "state.json"


def init_system():
    """Initialise globals and return a SystemManager."""
    globalvar._init()
    reset_counter()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    return SystemManager()


class SystemManager:
    """Manages funds, riders and time."""

    def __init__(self):
        self.grid = GridMap()
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    def maybe_recruit(self):
        """Recruit a rider when funds>=300 and pending > idle riders."""
        pending = len(self.order_manager.unassigned())
        idle = sum(1 for r in self.riders if r.pending_count() == 0)
        if self.funds >= 300 and pending > idle:
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.set_value("funds", self.funds - 500)
            self.riders.append(Rider(rid))
            return True
        return False

    def submit_order(self, rx, ry, cx, cy):
        """Create an order; returns (order, rider, recruited)."""
        order = self.order_manager.create_order(rx, ry, cx, cy)
        recruited = self.maybe_recruit()
        rider = self.order_manager.assign(order)
        return order, rider, recruited

    def dispatch_pending(self):
        for o in self.order_manager.unassigned():
            if not self.riders:
                self.maybe_recruit()
            self.order_manager.assign(o)

    def tick(self, n=1):
        for _ in range(n):
            globalvar.set_value("tick", globalvar.get_value("tick") + 1)
            self.dispatch_pending()
            for r in self.riders:
                r.move()

    def save(self, path=SAVE_FILE):
        data = {
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "tick": globalvar.get_value("tick"),
            "riders": [{"rider_id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "special_case": r.special_case,
                        "orders": [o.id for o in r.orders],
                        "log": r.log} for r in self.riders],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
