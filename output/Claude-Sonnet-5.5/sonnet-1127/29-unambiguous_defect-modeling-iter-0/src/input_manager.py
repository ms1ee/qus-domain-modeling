"""Command parsing and main loop."""
import globalvar
import system
from display import DisplayManager
from order import OrderManager
from path_planner import PathPlanner

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "st": "start", "h": "history"}


class InputManager:
    """Parses and executes commands."""

    def __init__(self):
        self.command_history = []
        self.display = DisplayManager()
        self.orders = OrderManager()

    def parse_coords(self, parts):
        if len(parts) != 4:
            raise ValueError("Need 4 integers: rx ry cx cy")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        if any(v < 0 or v > 800 for v in vals):
            raise ValueError("Coordinates must be within 0-800")
        return vals

    def start(self, parts):
        vals = self.parse_coords(parts)
        order, rider, added = self.orders.create_order(vals)
        if rider is None:
            return "No rider available (insufficient funds)."
        planner = PathPlanner()
        path = planner.plan_multi(
            [(rider.x, rider.y), tuple(order.res_pos), tuple(order.cus_pos)],
            rider.speed)
        return ("Restaurant: %s Customer: %s\nNew rider added: %s\n"
                "Rider %d speed=%d distance=%d time=%d ticks\n%s" % (
                    order.res_pos, order.cus_pos, added, rider.rider_id,
                    rider.speed, path.total_distance, path.estimated_time,
                    self.display.map(path, order)))

    def execute(self, line):
        parts = line.split()
        if not parts:
            return ""
        self.command_history.append(line)
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        if cmd in ("quit", "exit"):
            globalvar.set_value("running", False)
            return "Bye."
        if cmd == "start":
            out = self.start(parts[1:])
        elif cmd == "status":
            out = self.display.status() + "\n" + self.display.map()
        elif cmd == "orders":
            out = self.display.orders()
        elif cmd == "riders":
            out = self.display.riders_log()
        elif cmd == "history":
            out = "\n".join(self.command_history)
        else:
            raise ValueError("Unknown command: %s" % cmd)
        system.tick()
        return out

    def loop(self):
        while globalvar.get_value("running"):
            try:
                line = input("> ")
            except EOFError:
                break
            try:
                print(self.execute(line))
            except ValueError as e:
                print("Error:", e)
            except Exception as e:  # recover gracefully
                print("Unexpected error:", e)
