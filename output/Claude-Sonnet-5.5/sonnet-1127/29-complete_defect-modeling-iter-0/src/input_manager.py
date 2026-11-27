"""Command parsing and input validation."""
import globalvar
import system
from display import DisplayManager
from order import assign_order
from order_model import Order
from pathplanner import PathPlanner

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "t": "tick"}


class InputManager:
    """Handles commands."""

    def __init__(self):
        self.commandHistory = []
        self.display = DisplayManager()
        self.planner = PathPlanner()

    @staticmethod
    def parse_coords(text):
        """Parse four ints in 0-800; raises ValueError."""
        parts = text.replace(",", " ").replace("[", " ").replace(
            "]", " ").split()
        if len(parts) != 4:
            raise ValueError("Need exactly four integers.")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers.")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be in 0-800.")
        return vals

    def start_order(self, vals):
        order = Order((vals[0], vals[1]), (vals[2], vals[3]))
        globalvar.set_value("funds", globalvar.get_value("funds") + 300)
        globalvar.get_value("orders").append(order)
        added = False
        riders = globalvar.get_value("riders")
        if not any(r.state == 0 and not r.orders for r in riders):
            added = system.recruit_rider() is not None
        rider = assign_order(order)
        if rider is None:
            return "No rider available."
        route = self.planner.plan(rider.pos, order.res_pos)
        route += self.planner.plan(order.res_pos, order.cus_pos)[1:]
        total = sum(PathPlanner.distance(a, b)
                    for a, b in zip(route, route[1:]))
        eta = -(-total // rider.speed)
        return "\n".join([
            "Restaurant grid: (%d,%d)  Customer grid: (%d,%d)" % (
                order.res_pos[0] // 100, order.res_pos[1] // 100,
                order.cus_pos[0] // 100, order.cus_pos[1] // 100),
            "New rider added: %s" % added,
            "Order %d -> rider %d, speed %d, distance %d, est. time %d ticks"
            % (order.id, rider.rider_id, rider.speed, total, eta),
            DisplayManager.map_text([rider], [order], route)])

    def handle(self, line):
        """Process a command line; return output text."""
        line = line.strip()
        if not line:
            return ""
        self.commandHistory.append(line)
        parts = line.split(None, 1)
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        arg = parts[1] if len(parts) > 1 else ""
        try:
            if cmd == "start":
                return self.start_order(self.parse_coords(arg))
            if cmd == "status":
                return self.display.status()
            if cmd == "orders":
                return self.display.orders()
            if cmd == "riders":
                return self.display.riders()
            if cmd == "tick":
                n = int(arg) if arg else 1
                for _ in range(max(0, n)):
                    system.tick()
                return "Advanced to tick %d" % globalvar.get_value("tick")
            if cmd == "history":
                return "\n".join(self.commandHistory)
            if cmd in ("quit", "exit"):
                globalvar.set_value("running", False)
                return "Bye."
            return "Unknown command: %s" % cmd
        except ValueError as e:
            return "Error: %s" % e
