"""System manager."""
import json

import globalvar
from grid_map import GridMap
from order import OrderManager
from rider import Rider

RIDER_COST = 300


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
    """Manages funds, riders, orders and time."""

    def __init__(self):
        init_system()
        self.grid = GridMap()
        self.order_manager = OrderManager()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def tick(self):
        return globalvar.get_value("tick")

    @property
    def running(self):
        return globalvar.get_value("running")

    def idle_riders(self):
        return [r for r in self.riders if r.state == 0 and not r.orders]

    def recruit_if_needed(self):
        """Hire a rider if funds and demand allow. Returns the new rider."""
        if (self.funds >= RIDER_COST and
                self.order_manager.unstarted_count() > len(self.idle_riders())):
            cnt = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", cnt)
            globalvar.set_value("funds", self.funds - RIDER_COST)
            rider = Rider(cnt)
            self.riders.append(rider)
            return rider
        return None

    def submit_order(self, coords):
        """Create order, recruit if needed, assign. Returns (order, rider, new)."""
        order = self.order_manager.create(coords)
        new_rider = self.recruit_if_needed()
        rider = self.order_manager.assign(order)
        return order, rider, new_rider

    def step(self, n=1):
        for _ in range(n):
            globalvar.set_value("tick", self.tick + 1)
            for r in self.riders:
                r.move()

    def stop(self):
        globalvar.set_value("running", False)

    def save(self, path="config.json"):
        data = {"funds": self.funds, "tick": self.tick,
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "riders": [dict(r.to_dict(), log=r.log) for r in self.riders],
                "orders": [o.to_dict() for o in self.order_manager.orders]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
