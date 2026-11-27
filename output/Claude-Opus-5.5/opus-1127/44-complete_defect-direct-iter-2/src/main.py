"""Command-line interface of the Beijing Subway fare calculation system.

Usage: python main.py [--output_file F] [--format text|json]
                      [--mode shortest_distance|least_transfer|comprehensive]
                      [--max_transfers N] [--line_preference "Line 1"]
                      [--check_data]
Enter queries as "Starting Station; Ending Station". Type 'quit' to exit.
"""

import argparse
import json
import os
import sys

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data, build_network  # noqa: E402
from data_manager import DataManager, format_report  # noqa: E402
from fare_calculator import Sum_money, calculate_estimated_time  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES  # noqa: E402
from report import build_result, format_text, format_json  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"quit", "exit", "q"}


class QueryError(Exception):
    pass


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None, help="Preferred line(s), comma separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


def parse_query(line):
    text = line.replace("；", ";")
    if text.count(";") != 1:
        raise QueryError(FORMAT_ERROR)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def process_query(network, line, config):
    start_raw, end_raw = parse_query(line)
    start = network.resolve_station(start_raw)
    if start is None:
        msg = "Starting station '%s' does not exist, please check the station name" % start_raw
        sugg = network.suggest(start_raw)
        if sugg:
            msg += " (did you mean: %s?)" % ", ".join(sugg)
        raise QueryError(msg)
    end = network.resolve_station(end_raw)
    if end is None:
        msg = "Ending station '%s' does not exist, please check the station name" % end_raw
        sugg = network.suggest(end_raw)
        if sugg:
            msg += " (did you mean: %s?)" % ", ".join(sugg)
        raise QueryError(msg)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    s, t = network.station_to_number[start], network.station_to_number[end]
    try:
        sp = ShortestPath(network.graph, s, config)
        stations, edges = sp.path_with_edges(t)
    except Exception as exc:  # path calculation exception
        raise QueryError("Path calculation error: %s" % exc)
    if not stations:
        extra = " within %d transfer(s)" % config.max_transfers if config.max_transfers is not None else ""
        raise QueryError("No route found from '%s' to '%s'%s" % (start, end, extra))
    distance = sp.dist_to[t]
    transfers = sp.get_transfer_count(t)
    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, transfers)
    except Exception as exc:  # fare calculation exception
        raise QueryError("Fare calculation error: %s" % exc)
    names = [network.number_to_station[n] for n in stations]
    return build_result(start, end, config.mode, names, edges, distance, fare, est, transfers)


def export(results, path, fmt):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            if fmt == "json":
                json.dump(results if len(results) != 1 else results[0], fh, ensure_ascii=False, indent=2)
            else:
                fh.write("\n\n".join(format_text(r) for r in results) + "\n")
    except OSError as exc:
        print("Failed to write output file: %s" % exc)


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print("Failed to load subway data: %s" % exc)
        return 1

    if args.check_data:
        report = DataManager(data, args.data_file).check_integrity()
        print(format_report(report))
        return 0 if report["ok"] else 1

    network = build_network(data)
    prefs = [p.strip() for p in args.line_preference.split(",")] if args.line_preference else []
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=[p for p in prefs if p])

    results = []
    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (type 'quit' to exit).")
    while True:
        try:
            print("> ", end="", flush=True)
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print()
            break
        if not line:
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in EXIT_WORDS:
            break
        try:
            result = process_query(network, line, config)
        except QueryError as exc:
            print(str(exc))
            continue
        except Exception as exc:
            print("Unexpected error: %s" % exc)
            continue
        print(format_json(result) if args.format == "json" else format_text(result))
        results.append(result)
        if args.output_file:
            export(results, args.output_file, args.format)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
