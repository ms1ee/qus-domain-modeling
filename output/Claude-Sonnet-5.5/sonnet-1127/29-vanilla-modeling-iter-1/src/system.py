"""System manager and initialisation."""

import json

import globalvar
from rider import Rider
from order import OrderManager

RECRUIT_COST = 300


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Manages funds, riders and the simulation clock."""

    def __init__(self):
        init_system()
        self.order_manager = OrderManager()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def tick_count(self):
        return globalvar.get_value("tick")

    def idle_riders(self):
        return sum(1 for r in self.riders if r.state == 0 and not r.orders)

    def maybe_recruit(self):
        """Recruit a rider if funds allow and pending > idle."""
        if (self.funds >= RECRUIT_COST and
                self.order_manager.pending_count() > self.idle_riders()):
            cnt = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", cnt)
            globalvar.set_value("funds", self.funds - RECRUIT_COST)
            rider = Rider(cnt)
            self.riders.append(rider)
            return rider
        return None

    def submit_order(self, rx, ry, cx, cy):
        """Create order, recruit if needed, assign. Returns (order, new_rider, rider)."""
        order = self.order_manager.create_order(rx, ry, cx, cy)
        new_rider = self.maybe_recruit()
        rider = self.order_manager.assign(order)
        return order, new_rider, rider

    def tick(self, n=1):
        for _ in range(n):
            globalvar.set_value("tick", self.tick_count + 1)
            for r in self.riders:
                r.move()

    def save(self, path="state.json"):
        data = {"funds": self.funds, "tick": self.tick_count,
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "riders": [r.to_dict() for r in self.riders],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
