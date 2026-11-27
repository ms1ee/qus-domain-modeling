"""Command line interface of the Beijing Subway fare calculation system.

Usage examples::

    python main.py
    python main.py --mode least_transfer --format json --output_file result.json
    python main.py --check_data
"""

import argparse
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import check_data_integrity
from network import SubwayError, SubwayNetwork, parse_query_input
from pathfinding import VALID_MODES, PathfindingConfig
from report import build_report, render, write_reports

EXIT_COMMANDS = {"q", "quit", "exit", "退出"}


def _non_negative_int(value):
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("max_transfers must be a non-negative integer")
    if v < 0:
        raise argparse.ArgumentTypeError("max_transfers must be a non-negative integer")
    return v


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="path query mode")
    p.add_argument("--max_transfers", type=_non_negative_int, default=None,
                   help="maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help="subway data JSON file")
    p.add_argument("--start", help="starting station (non-interactive query)")
    p.add_argument("--end", help="ending station (non-interactive query)")
    return p


def run_single(network, start, end, config, fmt, reports):
    try:
        route = network.plan_route(start, end, config)
        report = build_report(route)
    except SubwayError as exc:
        print("Error: %s" % exc)
        return False
    except Exception as exc:  # unexpected failure, keep CLI alive
        print("Error: unexpected failure during query: %s" % exc)
        return False
    print(render(report, fmt))
    reports.append(report)
    return True


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print("Error: failed to load subway data: %s" % exc)
        return 1

    if args.check_data:
        rep = check_data_integrity(data)
        print(rep.to_text())
        return 0 if rep.is_valid else 1

    try:
        network = SubwayNetwork(data=data, data_source=args.data_file)
    except Exception as exc:
        print("Error: failed to build subway network: %s" % exc)
        return 1

    prefs = []
    if args.line_preference:
        prefs = [p.strip() for p in args.line_preference.split(",") if p.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=prefs)

    reports = []
    status = 0
    if args.start or args.end:
        if not (args.start and args.end):
            print("Error: both --start and --end must be provided")
            return 1
        status = 0 if run_single(network, args.start, args.end, config, args.format, reports) else 1
    else:
        print("Beijing Subway Fare Calculator (%d stations loaded)" % len(network.station_to_number))
        print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")
        while True:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            text = line.strip()
            if not text:
                continue
            if text.casefold() in EXIT_COMMANDS:
                break
            if text.casefold() in ("help", "h", "?"):
                print("Format: Starting Station; Ending Station  (separators: ; , ->)")
                continue
            try:
                start, end = parse_query_input(text)
            except SubwayError as exc:
                print("Error: %s" % exc)
                continue
            run_single(network, start, end, config, args.format, reports)
        print("Goodbye!")

    if args.output_file and reports:
        try:
            write_reports(args.output_file, reports, args.format)
            print("Results exported to %s" % args.output_file)
        except OSError as exc:
            print("Error: failed to write output file: %s" % exc)
            return 1
    return status


if __name__ == "__main__":
    sys.exit(main())
