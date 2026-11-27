"""Input manager: command parsing and validation."""
import globalvar
from display import DisplayManager

try:
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    pass

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "t": "tick", "h": "history"}


class InputManager:
    """Reads and executes commands."""

    def __init__(self, system):
        self.system = system
        self.display = DisplayManager()
        self.command_history = []

    def parse_coords(self, text):
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Need exactly 4 integers: rx ry cx cy")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        for v in vals:
            if not 0 <= v <= 800:
                raise ValueError("Coordinates must be within 0-800")
        return vals

    def execute(self, line):
        """Execute one command line; returns output text."""
        line = line.strip()
        if not line:
            return ""
        self.command_history.append(line)
        cmd, _, rest = line.partition(" ")
        cmd = ALIASES.get(cmd.lower(), cmd.lower())
        if cmd in ("quit", "exit"):
            globalvar.set_value("running", False)
            return "Bye."
        if cmd == "start":
            if not rest.strip():
                rest = input("Enter rx ry cx cy: ")
            vals = self.parse_coords(rest)
            o, rider, recruited, route = self.system.submit_order(*vals)
            out = ["Order %d: restaurant cell center %s, customer cell center %s"
                   % (o.id, o.res_pos, o.cus_pos),
                   "New rider added: %s" % ("yes" if recruited else "no")]
            if rider is None:
                out.append("No rider available; order pending.")
            else:
                out.append("Assigned rider %d, speed %d, est. time %d ticks"
                           % (rider.rider_id, rider.speed, route.estimated_time))
                out.append(self.display.render_map(route))
            return "\n".join(out)
        if cmd == "status":
            return self.display.status() + "\n" + self.display.render_map()
        if cmd == "orders":
            return self.display.orders()
        if cmd == "riders":
            return self.display.riders_history()
        if cmd == "history":
            return "\n".join(self.command_history)
        if cmd == "tick":
            n = int(rest) if rest.strip().isdigit() else 1
            self.system.tick(n)
            return "Advanced %d tick(s)." % n
        if cmd == "save":
            self.system.save(rest.strip() or "config.json")
            return "Saved."
        return "Unknown command. Use start, status, orders, riders, tick, save, quit."
