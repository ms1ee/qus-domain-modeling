"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--format text|json] [--output_file PATH]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1[,Line 2]"]
                   [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' or 'exit' to leave.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from fare_calculator import FareCalculationError
from pathfinding import PathfindingConfig, VALID_MODES
from report import build_route_info, format_report
from subway_network import SubwayNetwork

EXIT_COMMANDS = {"quit", "exit", "q"}
FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """User-facing query error."""


def parse_query(text):
    text = (text or "").strip().replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def process_query(network, text, config):
    """Validate and run one query. Returns the route info dict; raises QueryError."""
    start_raw, end_raw = parse_query(text)
    start = network.find_station(start_raw)
    if start is None:
        raise QueryError("Starting station '%s' does not exist, please check the station name" % start_raw)
    end = network.find_station(end_raw)
    if end is None:
        raise QueryError("Ending station '%s' does not exist, please check the station name" % end_raw)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    try:
        stations, edges = network.find_route(start, end, config)
    except Exception as exc:  # path calculation exception handling
        raise QueryError("Path calculation error: %s" % exc)
    if not stations:
        if config.max_transfers is not None:
            raise QueryError("No path found from '%s' to '%s' within %d transfer(s)"
                             % (start, end, config.max_transfers))
        raise QueryError("No path found from '%s' to '%s'" % (start, end))
    query = {
        "start": start,
        "end": end,
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines),
    }
    try:
        return build_route_info(stations, edges, query)
    except FareCalculationError as exc:
        raise QueryError("Fare calculation error: %s" % exc)
    except (ValueError, TypeError) as exc:
        raise QueryError("Fare calculation error: %s" % exc)


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


def print_integrity_report(report):
    print("Data integrity check")
    print("-" * 50)
    for k, v in report["stats"].items():
        print("  %s: %s" % (k, v))
    print("Errors: %d" % len(report["errors"]))
    for e in report["errors"]:
        print("  [ERROR] %s" % e)
    print("Warnings: %d" % len(report["warnings"]))
    for w in report["warnings"]:
        print("  [WARNING] %s" % w)
    print("Result: %s" % ("PASSED" if report["passed"] else "FAILED"))


def write_output(path, fmt, results):
    with open(path, "w", encoding="utf-8") as f:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        else:
            f.write("\n\n".join(format_report(r, "text") for r in results))
            f.write("\n")


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer")
        return 2

    try:
        network = SubwayNetwork(data_path=args.data_file)
    except FileNotFoundError:
        print("Error: subway data file not found: %s" % args.data_file)
        return 1
    except (ValueError, OSError) as exc:
        print("Error: failed to load subway data: %s" % exc)
        return 1

    if args.check_data:
        report = network.check_integrity()
        print_integrity_report(report)
        return 0 if report["passed"] else 1

    preferred = []
    if args.line_preference:
        for raw in args.line_preference.replace("，", ",").split(","):
            raw = raw.strip()
            if not raw:
                continue
            line = network.find_line(raw)
            if line is None:
                print("Warning: line preference '%s' does not match any known line" % raw)
                preferred.append(raw)
            else:
                preferred.append(line)

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except (ValueError, TypeError) as exc:
        print("Error: %s" % exc)
        return 2

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, 'quit' to exit.")
    results = []
    while True:
        try:
            text = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.strip().lower() in EXIT_COMMANDS:
            break
        if not text.strip():
            print(FORMAT_ERROR)
            continue
        try:
            info = process_query(network, text, config)
        except QueryError as exc:
            print(str(exc))
            continue
        except Exception as exc:  # last-resort safety net
            print("Unexpected error: %s" % exc)
            continue
        print(format_report(info, args.format))
        if args.output_file:
            results.append(info)
            try:
                write_output(args.output_file, args.format, results)
                print("Result exported to %s" % args.output_file)
            except OSError as exc:
                print("Error: failed to write output file: %s" % exc)
        sys.stdout.flush()
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
