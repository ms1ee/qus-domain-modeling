"""Command-line interface: argument parsing, interactive query loop and export."""

import argparse
import sys

from data_integrity import check_integrity
from data_loader import DataLoadError, load_subway_data
from fare_calculator import FareError
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    PathfindingError,
)
from query_parser import (
    QueryError,
    parse_line_preference,
    resolve_query,
)
from report import format_json, format_text
from route_planner import RouteError, plan_route
from subway_network import StationNotFoundError, SubwayNetwork

HELP_TEXT = """Enter a query in the form:  Starting Station; Ending Station
Examples:  Xizhimen; Dongzhimen
Commands:
  help   show this help text
  quit   leave the program (also: exit, q)"""


def _non_negative_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def build_arg_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="export the most recent query result to this file (overwritten per query)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: text (default) or json",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=MODE_SHORTEST_DISTANCE,
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="maximum number of allowed transfers",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line(s), e.g. 'Line 1' or 'Line 1, Line 2'",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def _export(path, content):
    """Write query output to a file. Returns True on success."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.write("\n")
    except OSError as exc:
        print(f"Error: could not write output file '{path}': {exc}")
        return False
    print(f"Result exported to {path}")
    return True


def answer_query(network, text, config, fmt):
    """Process one query string and return the formatted report.

    Raises:
        QueryError, StationNotFoundError, RouteError, PathfindingError, FareError
    """
    start, end = resolve_query(text, network)
    result = plan_route(network, start, end, config)
    return format_json(result) if fmt == "json" else format_text(result)


def _run_loop(network, config, fmt, output_file):
    """Interactive continuous query loop. Returns the process exit code."""
    print("Beijing Subway Fare Calculator")
    print(HELP_TEXT)
    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in ("quit", "exit", "q"):
            break
        if lowered in ("help", "?"):
            print(HELP_TEXT)
            continue
        try:
            output = answer_query(network, text, config, fmt)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except StationNotFoundError as exc:
            print(f"Error: {exc}")
            continue
        except RouteError as exc:
            print(f"Error: {exc}")
            continue
        except PathfindingError:
            print(
                "Error: no route found between these stations under the current settings "
                "(check --max_transfers and --line_preference)."
            )
            continue
        except FareError as exc:
            print(f"Fare calculation error: {exc}")
            continue
        except Exception as exc:  # last-resort guard to keep the session alive
            print(f"Unexpected error while processing the query: {exc}")
            continue
        print(output)
        if output_file:
            _export(output_file, output)
    print("Goodbye.")
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data()
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_integrity(data)
        print(report.format())
        return 0 if report.ok else 1

    network = SubwayNetwork.from_data(data)
    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not in the network data and will be ignored.")

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return _run_loop(network, config, args.format, args.output_file)
