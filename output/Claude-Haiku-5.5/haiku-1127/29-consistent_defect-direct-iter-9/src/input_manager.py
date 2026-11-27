"""Command parsing, coordinate validation, and input history."""

from path_planner import MAP_SIZE

COMMAND_ALIASES = {
    "start": "start", "s": "start",
    "status": "status", "st": "status",
    "orders": "orders", "o": "orders",
    "riders": "riders", "r": "riders",
    "map": "map", "m": "map",
    "tick": "tick", "t": "tick",
    "save": "save", "w": "save",
    "history": "history", "hist": "history",
    "help": "help", "h": "help", "?": "help",
    "quit": "quit", "exit": "quit", "q": "quit",
}

try:  # Enables arrow-key history on platforms that provide readline.
    import readline  # noqa: F401
except ImportError:
    readline = None


class InputManager:
    """Reads, parses and validates user commands."""

    def __init__(self):
        """Create an input manager with an empty command history."""
        self.history = []

    def read_line(self, prompt):
        """Read one line from the user and record it in the history.

        Args:
            prompt: Prompt text to display.

        Returns:
            The raw input line.

        Raises:
            EOFError: When input is closed.
        """
        line = input(prompt)
        if line.strip():
            self.history.append(line.strip())
        return line

    def parse(self, line):
        """Split a command line into a canonical command and arguments.

        Args:
            line: Raw input line.

        Returns:
            Tuple ``(command, args)``. ``command`` is None for blank input.

        Raises:
            ValueError: If the command is unknown.
        """
        tokens = line.strip().split()
        if not tokens:
            return None, []
        name = tokens[0].lower()
        command = COMMAND_ALIASES.get(name)
        if command is None:
            raise ValueError(f"Unknown command '{name}'. Type 'help' for the command list.")
        return command, tokens[1:]

    @staticmethod
    def parse_coordinates(tokens):
        """Validate four integer coordinates in the range 0-800.

        Args:
            tokens: List of four string tokens.

        Returns:
            List of four integers ``[rx, ry, cx, cy]``.

        Raises:
            ValueError: If the count, type or range is wrong.
        """
        if len(tokens) != 4:
            raise ValueError("expected 4 integers: restaurant_x restaurant_y customer_x customer_y")
        values = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError:
                raise ValueError(f"'{token}' is not an integer")
            if not 0 <= value <= MAP_SIZE:
                raise ValueError(f"coordinate {value} is out of range 0-{MAP_SIZE}")
            values.append(value)
        return values

    def prompt_order(self):
        """Interactively ask for order coordinates until valid or cancelled.

        Returns:
            List of four integers, or None if the user cancelled with a blank line.
        """
        print("Enter restaurant_x restaurant_y customer_x customer_y "
              f"(0-{MAP_SIZE}). Leave blank to cancel.")
        while True:
            line = self.read_line("order> ")
            if not line.strip():
                return None
            try:
                return self.parse_coordinates(line.split())
            except ValueError as exc:
                print(f"Invalid input: {exc}. Please try again.")
