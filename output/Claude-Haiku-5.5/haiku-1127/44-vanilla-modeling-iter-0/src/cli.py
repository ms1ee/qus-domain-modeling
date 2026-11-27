"""
Command-line interface for the Beijing Subway fare calculation system.

Supports interactive, continuous queries in the form
"Starting Station; Ending Station", command-line options for output format,
query mode, transfer limits, line preference and output file, and a data
integrity check mode.
"""
from __future__ import annotations

import argparse
import sys

from data_loader import DATA_FILE_PATH
from data_manager import StationNotFoundError, SubwayNetwork
from models import normalize_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
)
from report import export_report, render_report
from route_planner import FareCalculationError, NoRouteError, Route, plan_route

PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "
EXIT_COMMANDS = {"quit", "exit", "q"}


class QueryError(Exception):
    """A user-facing error raised while processing a query."""


def parse_query_text(text: str) -> tuple[str, str]:
    """Split a query of the form 'Starting Station; Ending Station'.

    Accepts the ASCII semicolon and the full-width Chinese semicolon.

    Raises:
        QueryError: If the input does not contain exactly two non-empty parts.
    """
    parts = text.replace("\uff1b", ";").split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0].strip(), parts[1].strip()


def resolve_endpoint(network: SubwayNetwork, raw_name: str, role: str) -> str:
    """Resolve a station name, producing a user-facing message when it is unknown."""
    try:
        return network.resolve_name(raw_name)
    except StationNotFoundError as exc:
        message = f"{role} station '{exc.name}' does not exist, please check the station name"
        if exc.suggestions:
            message += ". Did you mean: " + ", ".join(exc.suggestions) + "?"
        raise QueryError(message) from exc


def process_query(network: SubwayNetwork, text: str, config: PathfindingConfig) -> Route:
    """Validate a query string and compute its route.

    Raises:
        QueryError: With a user-facing message for any invalid input or failure.
    """
    start_raw, end_raw = parse_query_text(text)
    start = resolve_endpoint(network, start_raw, "Starting")
    end = resolve_endpoint(network, end_raw, "Ending")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    try:
        return plan_route(network, start, end, config)
    except NoRouteError as exc:
        raise QueryError(str(exc)) from exc
    except FareCalculationError as exc:
        raise QueryError(str(exc)) from exc
    except Exception as exc:  # defensive: any unexpected path-calculation failure
        raise QueryError(f"Path calculation failed: {exc}") from exc


def run_interactive(network: SubwayNetwork, config: PathfindingConfig, fmt: str,
                    output_file: str | None, input_func=input) -> int:
    """Run the continuous query loop until the user quits or input ends.

    Returns:
        The number of successfully answered queries.
    """
    answered = 0
    while True:
        try:
            raw_line = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw_line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            route = process_query(network, text, config)
        except QueryError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue

        try:
            print(render_report(route, fmt).content)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if output_file:
            try:
                export_report(render_report(route, fmt, compact=True), output_file)
            except OSError as exc:
                print(f"Error: could not write output file: {exc}", file=sys.stderr)
        answered += 1
    return answered


def _non_negative_int(value: str) -> int:
    """argparse type: a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return number


def parse_line_preference(value: str | None) -> list[str]:
    """Split a comma-separated line preference string into line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="append each query result to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' (comma-separated for several)")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = network.check_integrity()
        print(report.to_text())
        return 0 if report.ok else 1

    preferred = parse_line_preference(args.line_preference)
    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    known_lines = {normalize_text(line) for line in network.line_stations}
    for line in preferred:
        if normalize_text(line) not in known_lines:
            print(f"Warning: line '{line}' is not found in the subway data", file=sys.stderr)

    print("Beijing Subway fare calculator")
    print(f"Mode: {config.mode}, output format: {args.format}. Type 'quit' to exit.")
    run_interactive(network, config, args.format, args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
