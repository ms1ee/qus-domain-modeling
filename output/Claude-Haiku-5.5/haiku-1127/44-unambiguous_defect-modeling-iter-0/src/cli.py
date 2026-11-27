"""
Command-line interface for the Beijing Subway fare calculation system.

Provides argument parsing, station name standardization, input validation,
continuous interactive queries and multi-level error handling.
"""

import argparse
import difflib
import re
import sys
import unicodedata

from data_loader import DATA_FILE_PATH, load_subway_data
from integrity import DataIntegrityChecker
from network import build_network
from pathfinding import MODE_SHORTEST_DISTANCE, PathfindingConfig, VALID_MODES
from report import FORMAT_TEXT, SUPPORTED_FORMATS, ReportExporter
from route import NoPathError, Query, plan_route

# Accepted separators between starting and ending station.
SEPARATORS = (";", "；", ",", "，")
EXIT_COMMANDS = ("quit", "exit")


class InputFormatError(Exception):
    """Raised when the query text does not follow the expected format."""


class StationNotFoundError(Exception):
    """Raised when a station name does not match any official station."""

    def __init__(self, role, name, suggestions=None):
        self.role = role
        self.name = name
        self.suggestions = list(suggestions or [])
        message = f"{role} station '{name}' does not exist, please check the station name"
        if self.suggestions:
            message += ". Did you mean: " + ", ".join(self.suggestions) + "?"
        super().__init__(message)


class LogicError(Exception):
    """Raised when a query is logically invalid."""


def normalize_station_name(name):
    """Normalize a station name for comparison (full-width to half-width, spacing, case)."""
    text = unicodedata.normalize("NFKC", str(name))
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


class StationResolver:
    """Maps user-entered station names to official station names."""

    def __init__(self, station_names):
        self._lookup = {}
        names = list(station_names)
        # Official names take priority over aliases.
        for name in names:
            self._lookup.setdefault(normalize_station_name(name), name)
        for name in names:
            key = normalize_station_name(name)
            alias = key[:-1] if key.endswith("站") else key + "站"
            if alias:
                self._lookup.setdefault(alias, name)
        self._keys = list(self._lookup.keys())

    def resolve(self, raw, role="Starting"):
        """
        Return the official station name for user input.

        Raises:
            InputFormatError: If the input is empty.
            StationNotFoundError: If no matching station exists.
        """
        key = normalize_station_name(raw)
        if not key:
            raise InputFormatError(f"{role} station name is empty")
        if key in self._lookup:
            return self._lookup[key]
        suggestions = []
        for close in difflib.get_close_matches(key, self._keys, n=3, cutoff=0.6):
            name = self._lookup[close]
            if name not in suggestions:
                suggestions.append(name)
        raise StationNotFoundError(role, str(raw).strip(), suggestions)


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system. Enter queries as "
                    "'Starting Station; Ending Station'.")
    parser.add_argument("--output_file", default=None,
                        help="write query results to this file")
    parser.add_argument("--format", choices=list(SUPPORTED_FORMATS), default=FORMAT_TEXT,
                        help="output format: text or json")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="path query mode")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_line_preference(value):
    """Split the --line_preference argument into a list of line names."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_query_text(text):
    """
    Split user input into (starting station, ending station).

    Raises:
        InputFormatError: If the separator is missing or a station part is empty.
    """
    stripped = text.strip()
    for separator in SEPARATORS:
        if separator in stripped:
            left, right = stripped.split(separator, 1)
            if left.strip() and right.strip():
                return left.strip(), right.strip()
            break
    raise InputFormatError(
        "Input format incorrect, please use 'Starting Station; Ending Station' format")


def answer_query(network, resolver, start_raw, end_raw, mode, max_transfers, preferred_lines):
    """
    Validate a query and compute its route.

    Returns:
        tuple: (Query, Route)

    Raises:
        StationNotFoundError, LogicError, NoPathError, ValueError, KeyError
    """
    start = resolver.resolve(start_raw, "Starting")
    end = resolver.resolve(end_raw, "Ending")
    if start == end:
        raise LogicError("Starting station cannot be the same as the ending station")
    query = Query(start, end, mode, max_transfers, preferred_lines)
    route = plan_route(network, query)
    return query, route


def run_interactive(network, resolver, exporter, mode, max_transfers, preferred_lines):
    """Run the continuous query loop until the user quits or input ends."""
    prompt = "Enter query as 'Starting Station; Ending Station' ('quit' to exit): "
    while True:
        try:
            text = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            start_raw, end_raw = parse_query_text(text)
            query, route = answer_query(network, resolver, start_raw, end_raw,
                                        mode, max_transfers, preferred_lines)
        except InputFormatError as exc:
            print(f"Error: {exc}")
        except StationNotFoundError as exc:
            print(f"Error: {exc}")
        except LogicError as exc:
            print(f"Error: {exc}")
        except NoPathError as exc:
            print(f"Path error: {exc}")
        except (ValueError, KeyError, ArithmeticError) as exc:
            print(f"Calculation error: {exc}")
        else:
            try:
                output = exporter.export(query, route)
            except OSError as exc:
                print(f"Error: failed to write output file: {exc}")
                output = exporter.render(query, route)
            print(output)


def main(argv=None):
    """
    Program entry point.

    Returns:
        int: Process exit code (0 success, 1 failed data check, 2 setup error).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        raw = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 2
    try:
        network = build_network(raw)
    except ValueError as exc:
        print(f"Error: invalid subway data: {exc}", file=sys.stderr)
        return 2

    if args.check_data:
        checker = DataIntegrityChecker()
        passed = checker.run(network)
        print(checker.report())
        return 0 if passed else 1

    preferred_lines = parse_line_preference(args.line_preference)
    try:
        PathfindingConfig(args.mode, args.max_transfers, preferred_lines)
    except ValueError as exc:
        print(f"Error: invalid option: {exc}", file=sys.stderr)
        return 2

    known_lines = set(network.line_names())
    for line in preferred_lines:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not a known subway line")

    exporter = ReportExporter(args.format, args.output_file)
    if args.output_file:
        try:
            exporter.prepare_output_file()
        except OSError as exc:
            print(f"Error: cannot open output file: {exc}", file=sys.stderr)
            return 2

    resolver = StationResolver(network.station_names())
    print("Beijing Subway Fare Calculation System")
    print(f"Loaded {len(network.station_names())} stations and "
          f"{network.graph.edge_count} connections.")
    print(f"Mode: {args.mode}  Format: {args.format}")
    run_interactive(network, resolver, exporter, args.mode, args.max_transfers, preferred_lines)
    print("Goodbye.")
    return 0
