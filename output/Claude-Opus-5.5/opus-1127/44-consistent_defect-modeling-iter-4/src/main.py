"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--output_file FILE] [--format text|json]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH
from network import SubwayNetwork, RouteNotFoundError
from pathfinding import PathfindingConfig, VALID_MODES
from report import format_report

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None, help="Preferred line(s), comma-separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p.parse_args(argv)


def parse_query(text):
    """Split input into (start, end); raises ValueError on bad format."""
    parts = [x.strip() for x in re.split(r"[;；,，]", text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def handle_query(network, text, config, fmt):
    """Process one query line; returns (success, output string)."""
    try:
        start, end = parse_query(text)
    except ValueError as exc:
        return False, str(exc)
    s = network.find_station(start)
    if s is None:
        msg = f"Starting station '{start}' does not exist, please check the station name"
        sug = network.suggest(start)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        return False, msg
    e = network.find_station(end)
    if e is None:
        msg = f"Ending station '{end}' does not exist, please check the station name"
        sug = network.suggest(end)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        return False, msg
    if s == e:
        return False, "Starting station cannot be the same as the ending station"
    try:
        route = network.find_route(s, e, config)
    except RouteNotFoundError as exc:
        return False, str(exc)
    except ValueError as exc:
        return False, f"Fare calculation error: {exc}"
    except Exception as exc:  # path calculation exceptions
        return False, f"Path calculation error: {exc}"
    try:
        return True, format_report(route, fmt)
    except Exception as exc:
        return False, f"Report generation error: {exc}"


def run_check(network):
    result = network.check_integrity()
    print("Data integrity check")
    print(f"  Stations: {result['station_count']}")
    print(f"  Connections: {result['connection_count']}")
    print(f"  Lines: {result['line_count']}")
    print(f"  Station coverage: {'OK' if result['station_coverage_valid'] else 'FAILED'}")
    print(f"  Connection integrity: {'OK' if result['connection_integrity_valid'] else 'FAILED'}")
    print(f"  Distance accuracy: {'OK' if result['distance_accuracy_valid'] else 'FAILED'}")
    for m in result["messages"]:
        print("  - " + m)
    print("Result: " + ("PASSED" if result["valid"] else "FAILED"))
    return 0 if result["valid"] else 1


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check(network)

    preferred = [x.strip() for x in args.line_preference.split(",")] if args.line_preference else []
    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if args.output_file:
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as exc:
            print(f"Cannot write output file: {exc}", file=sys.stderr)
            return 1

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit).")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in QUIT_WORDS:
            break
        ok, output = handle_query(network, text, config, args.format)
        print(output)
        if ok and args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as fh:
                    fh.write(output + "\n")
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
