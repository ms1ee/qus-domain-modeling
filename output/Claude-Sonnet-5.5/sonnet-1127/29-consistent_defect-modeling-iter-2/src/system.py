"""System management."""

import json
import globalvar
from rider import Rider
from order import OrderManager

RECRUIT_COST = 500
RECRUIT_MIN_FUNDS = 300


def init_system():
    """Initialise global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)


class SystemManager:
    """Core manager for funds, riders and ticks."""

    def __init__(self):
        init_system()
        self.order_manager = OrderManager()

    def recruit_if_needed(self):
        """Hire a rider when conditions are met. Returns the Rider or None."""
        funds = globalvar.get_value("funds")
        riders = globalvar.get_value("riders")
        pending = len(self.order_manager.pending_orders())
        idle = sum(1 for r in riders if r.state == 0 and not r.current_order())
        if funds >= RECRUIT_MIN_FUNDS and pending > idle:
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.set_value("funds", funds - RECRUIT_COST)
            rider = Rider(rid)
            riders.append(rider)
            return rider
        return None

    def submit_order(self, rx, ry, cx, cy):
        """Create order, maybe recruit, assign. Returns (order, rider, new)."""
        order = self.order_manager.create_order(rx, ry, cx, cy)
        new = self.recruit_if_needed()
        rider = self.order_manager.assign(order)
        if rider is not None:
            rider.log.append({
                "event": "order_received", "order_id": order.id,
                "time": globalvar.get_value("tick"),
                "x": rider.x, "y": rider.y, "state": rider.state})
        return order, rider, new

    def tick(self):
        globalvar.set_value("tick", globalvar.get_value("tick") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    def save(self, path="state.json"):
        data = {
            "funds": globalvar.get_value("funds"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "state": r.state, "log": r.log}
                       for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
