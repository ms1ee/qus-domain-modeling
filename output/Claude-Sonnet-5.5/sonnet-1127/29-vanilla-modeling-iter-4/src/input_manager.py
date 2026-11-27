"""Command parsing and validation."""
from display import DisplayManager


class InputManager:
    """Parses commands and runs them against the system."""

    def __init__(self, system):
        self.system = system
        self.display = DisplayManager(system)
        self.history = []
        self.aliases = {"s": "status", "o": "orders", "r": "riders",
                        "q": "quit", "exit": "quit"}

    def parse_coords(self, text):
        parts = text.replace(",", " ").replace("[", " ").replace("]", " ").split()
        if len(parts) != 4:
            raise ValueError("Enter exactly four integers: rx ry cx cy")
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Coordinates must be integers")
        for v in vals:
            if not 0 <= v <= 800:
                raise ValueError("Coordinates must be within 0-800")
        return vals

    def handle(self, line, prompt=input):
        """Process one command; returns output text."""
        cmd = line.strip().lower()
        if not cmd:
            return ""
        self.history.append(cmd)
        cmd = self.aliases.get(cmd, cmd)
        if cmd == "quit":
            self.system.stop()
            return "Bye."
        if cmd == "status":
            return self.display.status_text()
        if cmd == "orders":
            return self.display.orders_text()
        if cmd == "riders":
            return self.display.riders_text()
        if cmd == "history":
            return "\n".join(self.history)
        if cmd == "start":
            try:
                coords = self.parse_coords(prompt("Enter rx ry cx cy: "))
            except ValueError as e:
                return "Error: %s" % e
            order, rider, new = self.system.submit_order(coords)
            out = ["Restaurant cell: %s  Customer cell: %s" % (
                order.res_pos, order.cus_pos)]
            out.append("New rider added: %s" % ("yes (#%d)" % new.rider_id
                                                 if new else "no"))
            if rider is None:
                out.append("No rider available; order pending.")
            else:
                out.append("Assigned to rider %d" % rider.rider_id)
                out.append(self.display.route_text(rider, order))
            return "\n".join(out)
        return "Unknown command. Use start/status/orders/riders/quit."
