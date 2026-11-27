"""
Command-line interface of the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--output_file PATH]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' to exit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from pathfinding import VALID_MODES, PathfindingConfig
from report import FareError, build_route_report, format_json_report, format_text_report
from subway_network import SubwayNetwork

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = {"quit", "exit", "q"}


class QueryError(Exception):
    """User-facing query error."""


def parse_query(raw):
    text = (raw or "").strip().replace("；", ";")
    if text.count(";") != 1:
        raise QueryError(FORMAT_ERROR)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def process_query(network, raw, config):
    start_raw, end_raw = parse_query(raw)
    start = network.resolve_station(start_raw)
    if start is None:
        msg = f"Starting station '{start_raw}' does not exist, please check the station name"
        sugg = network.suggest_stations(start_raw)
        if sugg:
            msg += f" (did you mean: {', '.join(sugg)}?)"
        raise QueryError(msg)
    end = network.resolve_station(end_raw)
    if end is None:
        msg = f"Ending station '{end_raw}' does not exist, please check the station name"
        sugg = network.suggest_stations(end_raw)
        if sugg:
            msg += f" (did you mean: {', '.join(sugg)}?)"
        raise QueryError(msg)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    try:
        route = network.find_route(start, end, config)
    except Exception as exc:  # path calculation exception handling
        raise QueryError(f"Path calculation error: {exc}") from exc
    if route is None:
        msg = f"No route found from '{start}' to '{end}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        raise QueryError(msg)
    try:
        return build_route_report(start, end, route, config)
    except FareError as exc:
        raise QueryError(f"Fare calculation error: {exc}") from exc


def run_check(network):
    result = network.check_data_integrity()
    print("Data integrity check")
    print("-" * 40)
    for k, v in result["stats"].items():
        print(f"  {k}: {v}")
    print(f"Errors: {len(result['errors'])}")
    for e in result["errors"]:
        print(f"  [ERROR] {e}")
    print(f"Warnings: {len(result['warnings'])}")
    for w in result["warnings"]:
        print(f"  [WARNING] {w}")
    print("Result: " + ("PASSED" if result["ok"] else "FAILED"))
    return 0 if result["ok"] else 1


def write_output(path, fmt, reports):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = reports[0] if len(reports) == 1 else reports
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(format_text_report(r) for r in reports))
        fh.write("\n")


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true",
                   help="Execute data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    try:
        network = SubwayNetwork(data_path=args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check(network)

    preferred = []
    if args.line_preference:
        for item in args.line_preference.replace("，", ",").split(","):
            item = item.strip()
            if not item:
                continue
            resolved = network.resolve_line(item)
            if resolved is None:
                print(f"Warning: line '{item}' not found in network data, preference ignored")
            else:
                preferred.append(resolved)

    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, 'quit' to exit.")
    reports = []
    while True:
        try:
            raw = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw.strip():
            continue
        if raw.strip().lower() in EXIT_COMMANDS:
            break
        try:
            report = process_query(network, raw, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort safety net
            print(f"Error: unexpected failure: {exc}")
            continue
        if args.format == "json":
            print(format_json_report(report))
        else:
            print(format_text_report(report))
        if args.output_file:
            reports.append(report)
            try:
                write_output(args.output_file, args.format, reports)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
