"""System manager and initialisation."""
import json

import globalvar
from rider import Rider
from order import OrderManager
from gridmap import GRID

RIDER_COST = 300
ORDER_FEE = 100
INITIAL_FUNDS = 300


class SystemManager:
    """Manages funds, riders and the simulation clock."""

    def __init__(self):
        self.grid = GRID
        self.order_manager = OrderManager()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @funds.setter
    def funds(self, v):
        globalvar.set_value("funds", v)

    @property
    def running(self):
        return globalvar.get_value("running")

    @running.setter
    def running(self, v):
        globalvar.set_value("running", v)

    @property
    def tick_count(self):
        return globalvar.get_value("tick")

    def recruit(self):
        """Create riders while funds >= 300. Returns number added."""
        added = 0
        while self.funds >= RIDER_COST:
            self.funds -= RIDER_COST
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.get_value("riders").append(Rider(rid))
            added += 1
        return added

    def submit_order(self, coords):
        """Create an order; returns (order, rider, riders_added)."""
        order = self.order_manager.create_order(coords)
        self.funds += ORDER_FEE
        added = self.recruit()
        rider = self.order_manager.assign(order)
        return order, rider, added

    def tick(self):
        """Advance simulation by one tick."""
        globalvar.set_value("tick", self.tick_count + 1)
        self.order_manager.assign_pending()
        for r in globalvar.get_value("riders"):
            r.move()

    def save(self, path="state.json"):
        data = {"funds": self.funds, "tick": self.tick_count,
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "riders": [r.to_dict() for r in globalvar.get_value("riders")],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def init_system():
    """Initialise global state and return a SystemManager."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", INITIAL_FUNDS)
    globalvar.set_value("tick", 0)
    return SystemManager()
