"""Command parsing and validation."""

try:
    import readline  # noqa: F401  (command history / line editing)
except ImportError:  # pragma: no cover
    pass

ALIASES = {"s": "status", "o": "orders", "r": "riders", "q": "quit",
           "exit": "quit", "t": "tick", "st": "start"}


class InputManager:
    """Parses and executes user commands."""

    def __init__(self, system, display):
        self.system = system
        self.display = display
        self.command_history = []

    def parse_coords(self, parts):
        if len(parts) != 4:
            raise ValueError("Enter exactly four integers: rx ry cx cy")
        vals = []
        for p in parts:
            p = p.strip("[],")
            try:
                v = int(p)
            except ValueError:
                raise ValueError("Coordinates must be integers: %r" % p)
            if not 0 <= v <= 800:
                raise ValueError("Coordinate out of range 0-800: %d" % v)
            vals.append(v)
        return vals

    def handle(self, line):
        """Execute a command line; return output text."""
        line = line.strip()
        if not line:
            return ""
        self.command_history.append(line)
        parts = line.replace(",", " ").split()
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        args = parts[1:]
        try:
            if cmd == "start":
                if not args:
                    args = input("Enter rx ry cx cy: ").replace(
                        ",", " ").split()
                rx, ry, cx, cy = self.parse_coords(args)
                order, new_rider, rider = self.system.submit_order(
                    rx, ry, cx, cy)
                out = ["Order %d: restaurant grid %s, customer grid %s"
                       % (order.id, order.res_pos, order.cus_pos),
                       "New rider added: %s" % (
                           "yes (id %d)" % new_rider.rider_id
                           if new_rider else "no")]
                if rider is None:
                    out.append("No rider available; order pending.")
                else:
                    out.append("Assigned to rider %d" % rider.rider_id)
                    out.append(self.display.route_report(rider, order))
                return "\n".join(out)
            if cmd == "status":
                return self.display.status()
            if cmd == "orders":
                return self.display.orders()
            if cmd == "riders":
                return self.display.rider_logs()
            if cmd == "tick":
                n = int(args[0]) if args else 1
                if n < 0 or n > 100000:
                    raise ValueError("tick count out of range")
                self.system.tick(n)
                return "Advanced to tick %d" % self.system.tick_count
            if cmd == "save":
                self.system.save(args[0] if args else "state.json")
                return "Saved."
            if cmd == "history":
                return "\n".join(self.command_history)
            if cmd == "quit":
                import globalvar
                globalvar.set_value("running", False)
                return "Bye."
            if cmd == "help":
                return ("Commands: start rx ry cx cy | status | orders | "
                        "riders | tick [n] | save [file] | history | quit")
            return "Unknown command. Type 'help'."
        except ValueError as e:
            return "Error: %s" % e
        except Exception as e:  # recovery
            return "Unexpected error: %s" % e
