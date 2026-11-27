"""Command parsing, shortcuts, history and input validation."""

import re

from path_planner import MAP_SIZE

try:  # optional line editing / arrow-key history
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None


class Command:
    """A command with its shortcut and description."""

    def __init__(self, name, shortcut, description):
        self.name = name
        self.shortcut = shortcut
        self.description = description


COMMANDS = [
    Command("start", "s", "Input an order: rx ry cx cy (0-800)"),
    Command("status", "st", "Show funds, riders and map"),
    Command("orders", "o", "Show all orders"),
    Command("riders", "r", "Show rider status change logs"),
    Command("map", "m", "Show the 8x8 map"),
    Command("tick", "t", "Advance simulation: tick [n]"),
    Command("history", "hi", "Show command history (!! repeat, !n run n)"),
    Command("save", "sv", "Save state to JSON"),
    Command("help", "h", "Show this help"),
    Command("quit", "q", "Exit the program"),
    Command("exit", "x", "Exit the program"),
]


class InputManager:
    """Parses commands and validates user input."""

    def __init__(self):
        self.command_history = []
        self._lookup = {}
        for cmd in COMMANDS:
            self._lookup[cmd.name] = cmd.name
            self._lookup[cmd.shortcut] = cmd.name
        self._lookup["?"] = "help"

    def help_text(self):
        lines = ["Commands:"]
        for cmd in COMMANDS:
            lines.append("  {:<8} ({:<2})  {}".format(cmd.name, cmd.shortcut,
                                                    cmd.description))
        return "\n".join(lines)

    def resolve_history(self, line):
        """Expand ``!!`` and ``!n`` references. Raises ValueError."""
        line = line.strip()
        if line == "!!":
            if not self.command_history:
                raise ValueError("no command history")
            return self.command_history[-1]
        if line.startswith("!") and line[1:].isdigit():
            idx = int(line[1:])
            if idx < 1 or idx > len(self.command_history):
                raise ValueError("history index out of range")
            return self.command_history[idx - 1]
        return line

    def parse(self, line):
        """Parse a line into (command_name, args).

        Unknown commands return (None, [word]).
        """
        line = self.resolve_history(line or "")
        if not line:
            return "", []
        self.command_history.append(line)
        if len(self.command_history) > 1000:
            del self.command_history[:-1000]
        parts = line.split(None, 1)
        word = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        name = self._lookup.get(word)
        args = [a for a in re.split(r"[\s,\[\]()]+", rest) if a]
        if name is None:
            return None, [word]
        return name, args

    @staticmethod
    def validate_coordinates(args):
        """Validate four integer coordinates in range 0-800."""
        if isinstance(args, str):
            args = [a for a in re.split(r"[\s,\[\]()]+", args) if a]
        if len(args) != 4:
            raise ValueError("expected 4 integers: restaurant_x restaurant_y "
                             "customer_x customer_y, got {}".format(len(args)))
        values = []
        for a in args:
            try:
                v = int(str(a).strip())
            except ValueError:
                raise ValueError("'{}' is not an integer".format(a))
            if v < 0 or v > MAP_SIZE:
                raise ValueError("coordinate {} out of range 0-{}".format(
                    v, MAP_SIZE))
            values.append(v)
        return values

    @staticmethod
    def read_line(prompt):
        """Read a line, converting EOF/interrupt to 'quit'."""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"
