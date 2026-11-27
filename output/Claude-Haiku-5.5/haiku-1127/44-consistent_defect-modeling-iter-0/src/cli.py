"""Command-line interface: argument parsing, input validation and continuous query loop."""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from errors import InputFormatError, LogicError, SubwayError, UnknownStationError
from integrity import run_integrity_check
from models import Route
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig, plan_route
from visualization import build_report, render_route_dict, render_route_text, write_report

# Accept ';' (documented) as well as ',' as the separator between stations.
QUERY_SEPARATOR_PATTERN = re.compile(r"[;；,，]")
EXIT_WORDS = {"quit", "exit", "q"}


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).")
    parser.add_argument("--output_file", default=None,
                        help="file to export query results to")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query(text):
    """Split 'Starting Station; Ending Station' into two station strings.

    Raises:
        InputFormatError: if the input does not contain exactly two non-empty parts.
    """
    parts = QUERY_SEPARATOR_PATTERN.split(text)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0].strip(), parts[1].strip()


class QuerySession:
    """Holds the configuration and results of an interactive session."""

    def __init__(self, network, args):
        self.network = network
        self.args = args
        self.routes = []
        self.preferred_lines = []
        if args.line_preference:
            canonical = network.resolve_line(args.line_preference)
            if canonical is None:
                raise ValueError(f"unknown line preference '{args.line_preference}'")
            self.preferred_lines = [canonical]

    def make_config(self):
        return PathfindingConfig(
            mode=self.args.mode,
            max_transfers=self.args.max_transfers,
            preferred_lines=self.preferred_lines,
        )

    def resolve(self, raw, label):
        """Resolve user input to an official station name, reporting fuzzy matches."""
        try:
            name, exact = self.network.resolve_station(raw)
        except UnknownStationError as exc:
            raise UnknownStationError(
                f"{label} station '{raw}' does not exist, please check the station name") from exc
        if not exact:
            print(f"Notice: {label.lower()} station '{raw}' matched to nearest station '{name}'.")
        return name

    def run_query(self, text):
        """Execute one query. Returns the Route, or None if no route exists."""
        raw_start, raw_end = parse_query(text)
        start = self.resolve(raw_start, "Starting")
        end = self.resolve(raw_end, "Ending")
        if start == end:
            raise LogicError("Starting station cannot be the same as the ending station")
        route = plan_route(self.network, start, end, self.make_config())
        if route is None:
            print(f"No route found from '{start}' to '{end}'"
                  + (f" within {self.args.max_transfers} transfer(s)."
                     if self.args.max_transfers is not None else "."))
        return route

    def emit(self, route):
        """Print a route and export all session results if requested."""
        if self.args.format == "json":
            print(json.dumps(render_route_dict(route), ensure_ascii=False, indent=2))
        else:
            print(render_route_text(route))
        self.routes.append(route)
        if self.args.output_file:
            try:
                report = build_report(self.routes, self.args.format)
                write_report(report, self.args.output_file)
                print(f"Results exported to {self.args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")


def run_interactive(session):
    """Continuous query loop; returns the process exit code."""
    while True:
        try:
            text = input("Enter query 'Starting Station; Ending Station' (or 'quit'): ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.lower() in EXIT_WORDS:
            break
        try:
            route = session.run_query(stripped)
            if route is not None:
                session.emit(route)
        except SubwayError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Unexpected error while processing query: {exc}")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    network = SubwayNetwork(data)

    if args.check_data:
        result = run_integrity_check(network)
        print(result.summary_text())
        return 0 if result.all_valid else 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    try:
        session = QuerySession(network, args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query. Type 'quit' to exit.")
    return run_interactive(session)


if __name__ == "__main__":
    sys.exit(main())
