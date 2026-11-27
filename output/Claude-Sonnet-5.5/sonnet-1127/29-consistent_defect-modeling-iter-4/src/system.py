"""System manager and initialization."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globalvar  # noqa: E402
from rider import Rider  # noqa: E402
import order as order_mod  # noqa: E402
from order_model import Order  # noqa: E402


def init_system():
    """Initialize global state."""
    globalvar._init()


class SystemManager:
    """Manages funds, riders, orders and the clock."""

    def __init__(self):
        init_system()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def orders(self):
        return globalvar.get_value("orders")

    @property
    def tick(self):
        return globalvar.get_value("tick")

    def pending_orders(self):
        return [o for o in self.orders if o.status == "pending"]

    def idle_riders(self):
        return [r for r in self.riders if r.state == 0 and not r.pending_count()]

    def maybe_recruit(self, extra_pending=0):
        """Recruit a rider if funds>=300 and pending > idle."""
        if (self.funds >= 300 and
                len(self.pending_orders()) + extra_pending > len(self.idle_riders())):
            n = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", n)
            self.riders.append(Rider(n))
            globalvar.set_value("funds", self.funds - 500)
            return True
        return False

    def create_order(self, res_pos, cus_pos):
        """Create order, recruit if needed, assign. Returns (order, rider, hired)."""
        o = Order(res_pos, cus_pos)
        self.orders.append(o)
        hired = self.maybe_recruit()
        rider = order_mod.assign_order(o)
        return o, rider, hired

    def step(self):
        """Advance one tick."""
        globalvar.set_value("tick", self.tick + 1)
        for r in self.riders:
            r.move()
        for o in self.orders:
            if o.status == "pending":
                order_mod.assign_order(o)

    def save(self, path="state.json"):
        data = {"funds": self.funds, "tick": self.tick,
                "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                            "speed": r.speed, "state": r.state,
                            "orders": [o.id for o in r.orders]}
                           for r in self.riders],
                "orders": [o.to_dict() for o in self.orders]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
