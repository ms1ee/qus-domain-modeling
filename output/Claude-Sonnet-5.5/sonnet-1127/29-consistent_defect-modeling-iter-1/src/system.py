"""System manager."""
import json

import globalvar
from grid_map import GridMap
from order import OrderManager
from path_planner import PathPlanner
from display import DisplayManager
from input_manager import InputManager


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 1000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Coordinates all modules."""

    def __init__(self):
        init_system()
        self.grid = GridMap()
        self.orders = OrderManager()
        self.planner = PathPlanner()
        self.display = DisplayManager()
        self.input = InputManager()

    def tick(self):
        globalvar.set_value("tick", globalvar.get_value("tick") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    def busy(self):
        return any(o.status != "completed"
                   for o in globalvar.get_value("orders"))

    def start_order(self, coords):
        order, added = self.orders.create_order(coords)
        rider = next((r for r in globalvar.get_value("riders")
                      if r.rider_id == order.rider_id), None)
        out = ["Restaurant: %s  Customer: %s" % (order.res_pos, order.cus_pos),
               "New rider added: %s" % ("yes" if added else "no")]
        if rider is None:
            out.append("No rider available; order pending.")
            return "\n".join(out)
        route = self.planner.plan((rider.x, rider.y),
                                  [order.res_pos, order.cus_pos], rider.speed)
        out.append("Rider %d speed %d units/tick, estimated time %d ticks"
                   % (rider.rider_id, rider.speed, len(route) - 1))
        out.append(self.display.render_map(route, order))
        return "\n".join(out)

    def save(self, path="state.json"):
        data = {
            "funds": globalvar.get_value("funds"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "state": r.state, "history": r.history}
                       for r in globalvar.get_value("riders")],
            "orders": [{"id": o.id, "res": o.res_pos, "cus": o.cus_pos,
                        "status": o.status, "rider": o.rider_id,
                        "start": o.start_time, "time": o.time_taken}
                       for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
