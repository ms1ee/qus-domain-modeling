"""
Command-line interface of the Beijing Subway fare calculation system.

Usage::

    python main.py [--format text|json] [--output_file PATH]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1,Line 4"]
                   [--check_data]

Enter queries as ``Starting Station; Ending Station``; type ``quit`` to exit.
With ``--output_file`` text results are appended for the session, while JSON
output contains the latest query result.
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Optional

from data_loader import DATA_FILE_PATH
from integrity import DataIntegrityCheck
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathCalculationError, PathfindingConfig
from planner import RoutePlanner
from report import render_report

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SAME_STATION_ERROR = "Starting station cannot be the same as the ending station"
QUIT_COMMANDS = {"quit", "exit", "q"}


class InputValidationError(ValueError):
    """Raised for invalid user query input."""


@dataclass
class QueryConfiguration:
    output_file: Optional[str] = None
    format: str = "text"
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: List[str] = field(default_factory=list)
    check_data: bool = False


@dataclass
class RouteQuery:
    start_station_name: str
    end_station_name: str
    raw_input: str


def parse_query(raw):
    """Split ``"Start; End"`` into a :class:`RouteQuery` (format check only)."""
    if raw is None:
        raise InputValidationError(FORMAT_ERROR)
    text = str(raw).strip().replace("；", ";")
    if text.count(";") != 1:
        raise InputValidationError(FORMAT_ERROR)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputValidationError(FORMAT_ERROR)
    return RouteQuery(start, end, raw)


def validate_query(network, query):
    """Check existence and logic; return canonical ``(start, end)`` names."""
    start = network.resolve_station(query.start_station_name)
    if start is None:
        msg = f"Starting station '{query.start_station_name}' does not exist, please check the station name"
        hints = network.suggest_stations(query.start_station_name)
        if hints:
            msg += f" (did you mean: {', '.join(hints)}?)"
        raise InputValidationError(msg)
    end = network.resolve_station(query.end_station_name)
    if end is None:
        msg = f"Ending station '{query.end_station_name}' does not exist, please check the station name"
        hints = network.suggest_stations(query.end_station_name)
        if hints:
            msg += f" (did you mean: {', '.join(hints)}?)"
        raise InputValidationError(msg)
    if start == end:
        raise InputValidationError(SAME_STATION_ERROR)
    return start, end


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="Export query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance", help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated (e.g. \"Line 1\")")
    parser.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return parser


class SubwayFareApp:
    def __init__(self, network, qconfig, out=None, err=None):
        self.network = network
        self.qconfig = qconfig
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.planner = RoutePlanner(network)
        self._file_written = False
        preferred = []
        for name in qconfig.line_preference:
            resolved = network.resolve_line(name)
            if resolved is None:
                self._print(f"Warning: preferred line '{name}' not found in network data")
                preferred.append(name)
            else:
                preferred.append(resolved)
        self.path_config = PathfindingConfig(mode=qconfig.mode, max_transfers=qconfig.max_transfers,
                                             preferred_lines=preferred)

    def _print(self, text):
        print(text, file=self.out)

    def handle_query(self, raw):
        """Process one raw query line; return the rendered report or None on error."""
        try:
            query = parse_query(raw)
            start, end = validate_query(self.network, query)
        except InputValidationError as exc:
            self._print(f"Error: {exc}")
            return None
        try:
            route = self.planner.plan(start, end, self.path_config)
        except PathCalculationError as exc:
            self._print(f"Path calculation error: {exc}")
            return None
        except ValueError as exc:
            if "Fare" in str(exc):
                self._print(f"Fare calculation error: {exc}")
            else:
                self._print(f"Error: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 - graceful degradation
            self._print(f"Unexpected error during calculation: {exc}")
            return None

        content = render_report(route, self.qconfig.format, self.path_config)
        self._print(content)
        if self.qconfig.output_file:
            self._export(content)
        return content

    def _export(self, content):
        path = self.qconfig.output_file
        try:
            if self.qconfig.format == "json":
                mode = "w"
            else:
                mode = "a" if self._file_written else "w"
            with open(path, mode, encoding="utf-8") as handle:
                handle.write(content)
                handle.write("\n")
            self._file_written = True
            self._print(f"Result exported to {path}")
        except OSError as exc:
            self._print(f"Error: could not write output file '{path}': {exc}")

    def run(self, stdin=None):
        stdin = stdin or sys.stdin
        self._print("Beijing Subway Fare Calculation System")
        self._print(f"Mode: {self.path_config.mode}. Enter 'Starting Station; Ending Station' "
                    "or 'quit' to exit.")
        while True:
            try:
                self.out.write("\nQuery> ")
                self.out.flush()
                line = stdin.readline()
            except KeyboardInterrupt:
                self._print("\nGoodbye!")
                return 0
            if not line:
                self._print("\nGoodbye!")
                return 0
            text = line.strip()
            if not text:
                continue
            if text.lower() in QUIT_COMMANDS:
                self._print("Goodbye!")
                return 0
            self.handle_query(text)


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork(data_source=args.data_file)
    except FileNotFoundError:
        print(f"Error: data file '{args.data_file}' not found", file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 2

    if args.check_data:
        check = DataIntegrityCheck(network).run()
        print(check.format_report())
        return 0 if check.is_valid else 1

    prefs = []
    if args.line_preference:
        prefs = [p.strip() for p in args.line_preference.split(",") if p.strip()]
    qconfig = QueryConfiguration(output_file=args.output_file, format=args.format, mode=args.mode,
                                 max_transfers=args.max_transfers, line_preference=prefs,
                                 check_data=args.check_data)
    app = SubwayFareApp(network, qconfig)
    try:
        return app.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
