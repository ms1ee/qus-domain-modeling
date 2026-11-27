"""System manager."""
import json

import globalvar
from display import DisplayManager
from grid_map import GridMap, convert_point
from input_manager import InputManager
from order import find_best_rider_for_order, recruit_rider
from order_model import Order
from path_planner import PathPlanner


def init_system():
    """Initialize global state."""
    globalvar._init()
    globalvar.set_value("funds", 10000)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])


class SystemManager:
    """Coordinates the simulation."""

    def __init__(self):
        init_system()
        self.grid = GridMap()
        self.planner = PathPlanner(self.grid)
        self.display = DisplayManager()
        self.input = InputManager()

    def tick(self):
        """Advance simulated time."""
        globalvar.set_value("tick", globalvar.get_value("tick") + 1)
        for r in globalvar.get_value("riders"):
            r.move()

    def submit_order(self, vals):
        """Create and assign an order; return a report string."""
        res = convert_point(vals[0], vals[1])
        cus = convert_point(vals[2], vals[3])
        order = Order(res, cus)
        before = len(globalvar.get_value("riders"))
        rider = find_best_rider_for_order(order)
        if rider is None:
            return "No rider available (insufficient funds)."
        added = len(globalvar.get_value("riders")) > before
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        globalvar.get_value("orders").append(order)
        path = self.planner.plan((rider.x, rider.y), [res, cus], rider.speed)
        return ("Order %d: restaurant=%s customer=%s\nNew rider added: %s\n"
                "Rider %d speed=%d distance=%d est. time=%d ticks\n%s" % (
                    order.id, res, cus, added, rider.rider_id, rider.speed,
                    path.total_distance, path.estimated_time,
                    self.display.map(path)))

    def save(self, filename="state.json"):
        """Persist state as JSON."""
        data = {
            "funds": globalvar.get_value("funds"),
            "tick": globalvar.get_value("tick"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state}
                       for r in globalvar.get_value("riders")],
            "orders": [{"id": o.id, "restaurant": o.res_pos,
                        "customer": o.cus_pos, "status": o.status,
                        "rider": o.rider_id}
                       for o in globalvar.get_value("orders")],
        }
        with open(filename, "w") as f:
            json.dump(data, f)

    def handle(self, line):
        """Process one command line; return output."""
        cmd, args = self.input.parse(line)
        if cmd is None:
            return ""
        if cmd == "quit":
            globalvar.set_value("running", False)
            return "Bye."
        if cmd == "start":
            if not args:
                args = input("rx ry cx cy: ").split()
            try:
                return self.submit_order(self.input.parse_coords(args))
            except ValueError as e:
                return "Error: %s" % e
        if cmd == "status":
            return self.display.status()
        if cmd == "orders":
            return self.display.orders()
        if cmd == "riders":
            return self.display.riders()
        if cmd == "help":
            return "Commands: start, status, orders, riders, quit/exit"
        return "Unknown command: %s (try help)" % cmd
