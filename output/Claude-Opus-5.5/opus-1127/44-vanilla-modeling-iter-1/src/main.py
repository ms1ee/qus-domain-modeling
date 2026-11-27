"""Command-line interface of the Beijing Subway fare calculation system.

Usage::

    python src/main.py [--mode MODE] [--format text|json] [--output_file F]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]

Enter queries as ``Starting Station; Ending Station``; type ``q`` to quit.
"""

import argparse
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import check_data_integrity, format_integrity_report
from pathfinding import VALID_MODES, PathfindingConfig
from report import export_results, render
from subway_system import QueryError, SubwaySystem

EXIT_COMMANDS = {"q", "quit", "exit"}


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer")
        return 2

    try:
        data = load_subway_data(args.data_file)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 1

    if args.check_data:
        result = check_data_integrity(data)
        print(format_integrity_report(result))
        return 0 if result["valid"] else 1

    try:
        system = SubwaySystem(data=data)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: failed to build subway network: {exc}")
        return 1

    preferred = []
    if args.line_preference:
        preferred = [s.strip() for s in args.line_preference.split(",") if s.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (type 'q' to quit)")
    results = []
    while True:
        try:
            print("> ", end="", flush=True)
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print()
            break
        if not line:
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break
        try:
            start, end = system.parse_query(text)
            route = system.find_route(start, end, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"Error: unexpected failure: {exc}")
            continue
        print(render(route, args.format))
        results.append(route)
        if args.output_file:
            try:
                export_results(results, args.output_file, args.format)
                print(f"Result saved to {args.output_file}")
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
