"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--output_file FILE] [--format text|json]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"]
                   [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' to exit.
"""

import argparse
import json
import sys

from data_checker import DataIntegrityChecker, format_check_report
from data_loader import DATA_FILE_PATH
from fare_calculator import Sum_money
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath
from report import build_result, build_route, render

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"quit", "exit", "q"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="Export query results to this file")
    parser.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    parser.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES),
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated (e.g. 'Line 1')")
    parser.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_query(raw):
    """Split 'Start; End' input. Returns (start, end) or raises ValueError."""
    if raw is None:
        raise ValueError(FORMAT_ERROR)
    text = raw.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR)
    return start, end


def _unknown_station_msg(network, kind, name):
    msg = f"{kind} station '{name}' does not exist, please check the station name"
    sugg = network.suggest_stations(name)
    if sugg:
        msg += " (did you mean: " + ", ".join(sugg) + "?)"
    return msg


def process_query(network, raw, config=None):
    """Process one raw query. Returns (True, result_dict) or (False, error message)."""
    config = config or PathfindingConfig()
    try:
        start_in, end_in = parse_query(raw)
    except ValueError as exc:
        return False, str(exc)

    start = network.resolve_station(start_in)
    if start is None:
        return False, _unknown_station_msg(network, "Starting", start_in)
    end = network.resolve_station(end_in)
    if end is None:
        return False, _unknown_station_msg(network, "Ending", end_in)
    if start == end:
        return False, "Starting station cannot be the same as the ending station"

    try:
        sp = ShortestPath(network.graph, network.station_number(start), config)
        route = build_route(network, sp, network.station_number(end))
    except Exception as exc:  # path calculation exception handling
        return False, f"Path calculation error: {exc}"
    if route is None:
        if config.max_transfers is not None:
            return False, (f"No route found from '{start}' to '{end}' "
                           f"within {config.max_transfers} transfer(s)")
        return False, f"No route found from '{start}' to '{end}'"

    try:
        fare = Sum_money(route.total_distance)
    except Exception as exc:  # fare calculation exception handling
        return False, f"Fare calculation error: {exc}"

    query_info = {
        "start": start,
        "end": end,
        "raw_input": raw.strip(),
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines),
    }
    return True, build_result(route, query_info, fare)


def export_results(path, results, fmt):
    """Write all results so far to the output file."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(render(r, "text") for r in results))
        fh.write("\n")


def build_config(network, args):
    preferred = []
    if args.line_preference:
        for item in args.line_preference.split(","):
            item = item.strip()
            if not item:
                continue
            resolved = network.resolve_line(item)
            if resolved is None:
                print(f"Warning: line '{item}' does not exist, preference ignored")
            else:
                preferred.append(resolved)
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                             preferred_lines=preferred)


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(data_source=args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error loading subway data: {exc}")
        return 1

    if args.check_data:
        result = DataIntegrityChecker(network).run()
        print(format_check_report(result))
        return 0 if result["ok"] else 1

    config = build_config(network, args)
    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")

    results = []
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        raw = raw.strip()
        if not raw:
            continue
        if raw.lower() in QUIT_WORDS:
            break
        ok, result = process_query(network, raw, config)
        if not ok:
            print(result)
            continue
        print(render(result, args.format))
        if args.output_file:
            results.append(result)
            try:
                export_results(args.output_file, results, args.format)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
