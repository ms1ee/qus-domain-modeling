"""System manager."""
import json
import globalvar
from rider import Rider
import order as order_mod
from pathplanner import PathPlanner

RIDER_COST = 300


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


def recruit_rider():
    """Create a new rider, deducting cost."""
    cnt = globalvar.get_value("rider_id_counter", 0)
    rider = Rider(cnt)
    globalvar.set_value("rider_id_counter", cnt + 1)
    globalvar.set_value("funds", globalvar.get_value("funds") - RIDER_COST)
    globalvar.get_value("riders").append(rider)
    return rider


class SystemManager:
    """Facade over the global state."""

    def __init__(self):
        init_system()
        self.planner = PathPlanner()

    def tick(self, n=1):
        for _ in range(n):
            globalvar.set_value("tick", globalvar.get_value("tick") + 1)
            for r in globalvar.get_value("riders"):
                r.move()

    def submit_order(self, rx, ry, cx, cy):
        """Returns (order, rider, recruited, route)."""
        o = order_mod.create_order(rx, ry, cx, cy)
        riders = globalvar.get_value("riders")
        pending = sum(1 for x in globalvar.get_value("orders")
                      if x.status == "pending")
        idle = sum(1 for r in riders if r.state == 0 and not r.orders)
        recruited = False
        if globalvar.get_value("funds") >= RIDER_COST and pending > idle:
            recruit_rider()
            recruited = True
        rider = order_mod.assign_order(o)
        route = None
        if rider is not None:
            route = self.planner.plan((rider.x, rider.y),
                                      [o.res_pos, o.cus_pos], rider.speed)
        return o, rider, recruited, route

    def save(self, path="config.json"):
        data = {"funds": globalvar.get_value("funds"),
                "tick": globalvar.get_value("tick"),
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "riders": [r.to_dict() for r in globalvar.get_value("riders")],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
