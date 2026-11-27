"""Command-line interface of the Beijing Subway fare calculation system."""

import argparse
import json
import re

from fare_calculator import FareCalculationError
from network import UnknownStationError
from pathfinding import (DEFAULT_MAX_TRANSFERS, MODE_SHORTEST_DISTANCE, VALID_MODES,
                         NoPathError, PathfindingError, find_route)
from report import build_json_report, build_report, build_text_report, write_text_file

# Accept ';' or ',' (ASCII and full-width forms) as the query separator.
QUERY_SEPARATOR_PATTERN = re.compile(r"[;,\uff1b\uff0c]")
EXIT_COMMANDS = ("quit", "exit", "q")
FORMAT_CHOICES = ("text", "json")
INPUT_PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryFormatError(ValueError):
    """Raised when a query line does not match the expected format."""


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="beijing-subway-fare",
        description="Beijing Subway fare calculation system (interactive CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", choices=FORMAT_CHOICES, default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=DEFAULT_MAX_TRANSFERS,
                        help="maximum number of line transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def parse_args(argv=None):
    """Parse command-line arguments."""
    return build_arg_parser().parse_args(argv)


def parse_query(text):
    """Split a query line into ``(starting_station, ending_station)``.

    Raises:
        QueryFormatError: if the line does not contain exactly two non-empty parts.
    """
    if not text or not text.strip():
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    parts = [part.strip() for part in QUERY_SEPARATOR_PATTERN.split(text)]
    if len(parts) != 2 or not all(parts):
        raise QueryFormatError(FORMAT_ERROR_MESSAGE)
    return parts[0], parts[1]


class SubwayCLI:
    """Interactive query loop supporting continuous queries and exports."""

    def __init__(self, network, args, input_func=input, output_func=print):
        self.network = network
        self.format = args.format
        self.mode = args.mode
        self.max_transfers = args.max_transfers
        self.output_file = args.output_file
        self._line_preference_arg = args.line_preference
        self._input = input_func
        self._output = output_func
        self.line_preferences = []
        self._exported = []

    def configure(self):
        """Validate command-line settings.

        Raises:
            ValueError: if a setting is invalid.
        """
        if self.max_transfers < 0:
            raise ValueError("--max_transfers must be a non-negative integer")
        self.line_preferences = []
        if self._line_preference_arg:
            for raw in self._line_preference_arg.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                official = self.network.normalize_line(raw)
                if official is None:
                    raise ValueError(f"Unknown line '{raw}' given to --line_preference")
                self.line_preferences.append(official)

    def run(self):
        """Run the continuous query loop until the user quits.

        Returns:
            int: process exit code.
        """
        try:
            self.configure()
        except ValueError as exc:
            self._output(f"Configuration error: {exc}")
            return 2

        self._output("Beijing Subway fare calculation system")
        preference = ", ".join(self.line_preferences) if self.line_preferences else "none"
        self._output(f"Mode: {self.mode} | Max transfers: {self.max_transfers} | "
                     f"Line preference: {preference}")
        self._output("Enter 'quit' to exit.")

        while True:
            try:
                raw = self._input(INPUT_PROMPT)
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
            text = raw.strip()
            if not text:
                continue
            if text.lower() in EXIT_COMMANDS:
                break
            self.handle_query(text)
        return 0

    def handle_query(self, text):
        """Process one query line.

        Returns:
            Route or None: the computed route, or None if the query failed.
        """
        try:
            origin_raw, destination_raw = parse_query(text)
        except QueryFormatError as exc:
            self._output(str(exc))
            return None

        origin = self._resolve(origin_raw, "Starting")
        if origin is None:
            return None
        destination = self._resolve(destination_raw, "Ending")
        if destination is None:
            return None
        if origin == destination:
            self._output("Starting station cannot be the same as the ending station.")
            return None

        try:
            route = find_route(
                self.network, origin, destination,
                mode=self.mode,
                max_transfers=self.max_transfers,
                line_preference=self.line_preferences,
            )
        except NoPathError as exc:
            self._output(f"No route found: {exc}")
            return None
        except FareCalculationError as exc:
            self._output(f"Fare calculation error: {exc}")
            return None
        except PathfindingError as exc:
            self._output(f"Path calculation error: {exc}")
            return None
        except (ValueError, KeyError, TypeError) as exc:
            self._output(f"Path calculation error: {exc}")
            return None

        try:
            content = build_report(route, self.format).content
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            self._output(f"Report generation error: {exc}")
            return None

        self._output(content)
        self._export(route)
        return route

    def _resolve(self, raw, label):
        """Resolve a user-entered station name; return the official name or None."""
        try:
            name, exact = self.network.resolve_station(raw)
        except UnknownStationError:
            self._output(f"{label} station '{raw}' does not exist, please check the station name.")
            return None
        if not exact:
            self._output(f"Note: {label.lower()} station '{raw}' was matched to the nearest "
                         f"station '{name}'.")
        return name

    def _export(self, route):
        """Append the route to the output file (if configured)."""
        if not self.output_file:
            return
        if self.format == "json":
            self._exported.append(build_json_report(route))
            content = json.dumps(self._exported, ensure_ascii=False, indent=2)
        else:
            self._exported.append(build_text_report(route))
            content = ("\n\n" + "-" * 60 + "\n\n").join(self._exported)
        try:
            write_text_file(self.output_file, content + "\n")
            self._output(f"Results exported to {self.output_file}")
        except OSError as exc:
            self._output(f"Failed to write output file '{self.output_file}': {exc}")
