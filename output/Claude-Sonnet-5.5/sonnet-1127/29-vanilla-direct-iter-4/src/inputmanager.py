"""Command parsing."""
import json
import globalvar
from order import OrderManager
from system import SystemManager
from display import DisplayManager

try:
    import readline  # noqa: F401
except ImportError:
    pass

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "exit": "quit", "t": "tick"}


def parse_coords(text):
    """Parse four ints in 0-800. Raises ValueError."""
    cleaned = text.replace("[", " ").replace("]", " ").replace(",", " ")
    parts = cleaned.split()
    if len(parts) != 4:
        raise ValueError("Need exactly four integers.")
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise ValueError("Coordinates must be integers.")
    for v in vals:
        if not 0 <= v <= 800:
            raise ValueError("Coordinates must be within 0-800.")
    return vals


class InputManager:
    """Handle commands."""

    def handle(self, line):
        """Process a line; return output string."""
        parts = line.strip().split(None, 1)
        if not parts:
            return ""
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        arg = parts[1] if len(parts) > 1 else ""
        try:
            if cmd == "quit":
                globalvar.set_value("running", False)
                return "Bye."
            if cmd == "status":
                return DisplayManager.status() + "\n" + DisplayManager.map()
            if cmd == "orders":
                return DisplayManager.orders()
            if cmd == "riders":
                return DisplayManager.riders_log()
            if cmd == "help":
                return ("Commands: start x1 y1 x2 y2, status, orders, "
                        "riders, tick [n], save [file], quit")
            if cmd == "tick":
                n = int(arg) if arg.strip() else 1
                for _ in range(max(0, n)):
                    SystemManager.tick()
                return DisplayManager.status()
            if cmd == "save":
                return self.save(arg.strip() or "state.json")
            if cmd == "start":
                if not arg:
                    arg = input("Enter res_x res_y cus_x cus_y: ")
                return self.start(parse_coords(arg))
            return "Unknown command. Type help."
        except ValueError as e:
            return "Error: %s" % e
        except Exception as e:  # recovery
            return "Unexpected error: %s" % e

    def start(self, coords):
        order = OrderManager.create(coords)
        rider, recruited = OrderManager.dispatch(order)
        out = ["Restaurant grid: %s, Customer grid: %s" % (
            (order.res_pos[0] // 100, order.res_pos[1] // 100),
            (order.cus_pos[0] // 100, order.cus_pos[1] // 100)),
            "New rider added: %s" % recruited]
        if rider is None:
            out.append("No rider available; order pending.")
        else:
            pts = DisplayManager.route_for(rider, order)
            out.append("Order %d assigned to rider %d, speed %d, "
                       "estimated time %d ticks" % (
                           order.id, rider.rider_id, rider.speed,
                           len(pts) - 1))
            out.append(DisplayManager.map(pts))
        SystemManager.tick()
        return "\n".join(out)

    def save(self, path):
        data = {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "riders": [{"id": r.rider_id, "x": r.x, "y": r.y,
                        "speed": r.speed, "state": r.state,
                        "orders": [o.id for o in r.orders],
                        "special_case": r.special_case}
                       for r in globalvar.get_value("riders")],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return "Saved to %s" % path
