"""Command parsing and loop."""
import globalvar
from display import DisplayManager
from order import OrderManager
from path_planner import PathPlanner
from system import SystemManager

try:
    import readline  # noqa: F401  (command history)
except ImportError:
    pass

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "n": "start", "h": "help"}


def parse_coords(text):
    """Parse four integers in 0-800; raises ValueError."""
    parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
    if len(parts) != 4:
        raise ValueError("Enter exactly four integers.")
    vals = [int(p) for p in parts]
    if any(v < 0 or v > 800 for v in vals):
        raise ValueError("Coordinates must be within 0-800.")
    return vals


class InputManager:
    """Interactive command loop."""

    def __init__(self):
        self.sm = SystemManager()
        self.disp = DisplayManager()
        self.om = OrderManager()

    def handle(self, cmd):
        cmd = ALIASES.get(cmd, cmd)
        if cmd in ("quit", "exit"):
            globalvar.set_value("running", False)
        elif cmd == "status":
            print(self.disp.status())
            print(self.disp.map())
        elif cmd == "orders":
            print(self.disp.orders())
        elif cmd == "riders":
            print(self.disp.riders_log())
        elif cmd == "start":
            try:
                coords = parse_coords(input("Enter rx ry cx cy: "))
            except ValueError as e:
                print("Invalid input: %s" % e)
                return
            order, rider, added = self.om.create_order(coords)
            if rider is None:
                print("No rider available.")
                return
            print("Restaurant grid pos: %s, customer grid pos: %s" % (
                order.res_pos, order.cus_pos))
            print("New rider added: %s" % added)
            route = PathPlanner.route(rider.pos, order.res_pos, order.cus_pos)
            dist = sum(PathPlanner.distance(a, b)
                       for a, b in zip(route, route[1:]))
            print("Rider %d speed %d, estimated time %d ticks" % (
                rider.rider_id, rider.speed, -(-dist // rider.speed)))
            print(self.disp.map(route))
        elif cmd == "help":
            print("start(n) status(s) orders(o) riders(r) quit(q)")
        elif cmd:
            print("Unknown command '%s'. Type help." % cmd)

    def run(self):
        print("Food Delivery Dispatch. Type help.")
        while globalvar.get_value("running"):
            try:
                cmd = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            try:
                self.handle(cmd)
                self.sm.tick()
            except Exception as e:  # recover gracefully
                print("Error: %s" % e)
        self.sm.save()
