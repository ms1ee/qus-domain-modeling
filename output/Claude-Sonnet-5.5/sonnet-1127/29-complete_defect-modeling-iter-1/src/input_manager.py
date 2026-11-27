"""Command parsing."""
from display import DisplayManager

ALIASES = {"s": "start", "st": "status", "o": "orders", "r": "riders",
           "q": "quit", "exit": "quit", "h": "help", "t": "tick"}


class InputManager:
    """Parses commands and dispatches them."""

    def __init__(self, system, input_fn=input):
        self.system = system
        self.display = DisplayManager(system)
        self.command_history = []
        self.input_fn = input_fn

    def handle(self, line):
        """Process a command line; returns output text."""
        line = line.strip()
        if not line:
            return ""
        self.command_history.append(line)
        parts = line.split()
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        args = parts[1:]
        try:
            if cmd == "start":
                return self._start(args)
            if cmd == "status":
                return self.display.status()
            if cmd == "orders":
                return self.display.orders()
            if cmd == "riders":
                return self.display.riders_log()
            if cmd == "tick":
                n = int(args[0]) if args else 1
                for _ in range(max(0, n)):
                    self.system.tick()
                return "Advanced %d tick(s)." % n
            if cmd == "history":
                return "\n".join(self.command_history)
            if cmd == "save":
                self.system.save()
                return "Saved."
            if cmd == "quit":
                self.system.running = False
                return "Bye."
            if cmd == "help":
                return ("Commands: start [rx ry cx cy], status, orders, "
                        "riders, tick [n], history, save, quit/exit")
            return "Unknown command '%s'. Type help." % parts[0]
        except ValueError as e:
            return "Error: %s" % e
        except Exception as e:  # recovery
            return "Unexpected error: %s" % e

    def _start(self, args):
        if not args:
            args = self.input_fn("Enter rx ry cx cy: ").split()
        try:
            coords = [int(a) for a in args]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        order, rider, added = self.system.submit_order(coords)
        from gridmap import GRID
        out = ["Order %d: restaurant cell (%d,%d), customer cell (%d,%d)" % (
            order.id, GRID.cell_index(order.res_pos[0]),
            GRID.cell_index(order.res_pos[1]),
            GRID.cell_index(order.cus_pos[0]),
            GRID.cell_index(order.cus_pos[1])),
            "New rider added: %s" % ("yes" if added else "no")]
        if rider:
            out.append(self.display.route_info(rider, order))
        else:
            out.append("No rider available; order pending.")
        return "\n".join(out)
