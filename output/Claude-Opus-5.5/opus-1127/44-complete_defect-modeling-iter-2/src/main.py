"""
Beijing Subway Fare Calculation System - command-line interface.

Usage:
  python main.py [--format text|json] [--output_file PATH]
                 [--mode shortest_distance|least_transfer|comprehensive]
                 [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as "Starting Station; Ending Station". Enter 'q' to quit.
"""

import argparse
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayNetwork, check_data_integrity
from fare_calculator import FareCalculationError
from pathfinding import PathfindingConfig, VALID_MODES
from planner import RouteNotFoundError, StationNotFoundError, compute_route
from report import render, write_results

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit"}


def _non_negative_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}")
    if n < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return n


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance", help="Path query mode")
    p.add_argument("--max_transfers", type=_non_negative_int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None, help="Preferred line(s), comma separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p.parse_args(argv)


def parse_query(text):
    """Parse 'Start; End'. Returns (start, end) or raises ValueError."""
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR)
    return start, end


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(data_source=args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        print(report.to_text())
        return 0 if report.is_valid else 1

    preferred = []
    if args.line_preference:
        for item in args.line_preference.split(","):
            item = item.strip()
            if not item:
                continue
            found = network.find_line(item)
            if found is None:
                print(f"Warning: line '{item}' not found in data, preference ignored")
            else:
                preferred.append(found)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    results = []
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in QUIT_WORDS:
            break
        try:
            start, end = parse_query(line)
            if start == end or (network.find_station(start) is not None
                                and network.find_station(start) == network.find_station(end)):
                print("Error: Starting station cannot be the same as the ending station")
                continue
            route = compute_route(network, start, end, config)
        except StationNotFoundError as exc:
            print(f"Error: {exc}")
            continue
        except RouteNotFoundError as exc:
            print(f"Error: {exc}")
            continue
        except FareCalculationError as exc:
            print(f"Error: Fare calculation failed: {exc}")
            continue
        except ValueError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort handler keeps the loop alive
            print(f"Error: unexpected failure: {exc}")
            continue

        print(render(route, args.format))
        results.append(route)
        if args.output_file:
            try:
                write_results(args.output_file, results, args.format)
                print(f"Result saved to {args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
