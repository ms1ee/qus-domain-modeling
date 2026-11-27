"""
Command-line interface of the Beijing Subway fare calculation system.

Usage:
    python main.py [--format text|json] [--output_file FILE]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as "Starting Station; Ending Station". Enter 'q' to quit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayNetwork
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_json_report, build_route, format_text_report

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit"}


class QueryError(Exception):
    """User-facing query error."""


def parse_query_input(text):
    """Split 'Start; End' into a tuple; raise QueryError on bad format."""
    if text is None:
        raise QueryError(FORMAT_ERROR)
    text = text.replace("；", ";").strip()
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def validate_stations(network, start, end):
    s = network.find_station(start)
    if s is None:
        raise QueryError(f"Starting station '{start}' does not exist, please check the station name")
    e = network.find_station(end)
    if e is None:
        raise QueryError(f"Ending station '{end}' does not exist, please check the station name")
    if s == e:
        raise QueryError("Starting station cannot be the same as the ending station")
    return s, e


def run_query(network, start, end, config):
    """Compute a route between two (validated) station names."""
    try:
        sp = ShortestPath(network.graph, network.station_to_number[start], config)
        target = network.station_to_number[end]
        path, edges = sp.path_with_edges(target)
    except Exception as exc:  # path calculation exception
        raise QueryError(f"Path calculation error: {exc}") from exc
    if not path:
        msg = f"No path found from '{start}' to '{end}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        raise QueryError(msg)
    try:
        return build_route(path, edges, network.number_to_station)
    except Exception as exc:  # fare calculation exception
        raise QueryError(f"Fare calculation error: {exc}") from exc


def build_arg_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer")
        return 2

    try:
        network = SubwayNetwork(data_file=args.data_file)
    except Exception as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        print(network.check_integrity().to_text())
        return 0

    preferred = []
    if args.line_preference:
        for raw in args.line_preference.replace("，", ",").split(","):
            raw = raw.strip()
            if not raw:
                continue
            real = network.find_line(raw)
            if real is None:
                print(f"Warning: line '{raw}' not found in data, preference ignored")
            else:
                preferred.append(real)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    json_results = []
    text_written = False

    while True:
        try:
            print("Please enter query: ", end="", flush=True)
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print()
            break
        if line == "":
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in QUIT_WORDS:
            break
        try:
            start_in, end_in = parse_query_input(line)
            start, end = validate_stations(network, start_in, end_in)
            route = run_query(network, start, end, config)
        except QueryError as exc:
            print(str(exc))
            continue
        except Exception as exc:
            print(f"Unexpected error: {exc}")
            continue

        if args.format == "json":
            data = build_json_report(route, start, end, args.mode, args.max_transfers,
                                     args.line_preference)
            output = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            data = None
            output = format_text_report(route, start, end, args.mode)
        print(output)

        if args.output_file:
            try:
                if args.format == "json":
                    json_results.append(data)
                    payload = json_results[0] if len(json_results) == 1 else json_results
                    with open(args.output_file, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh, ensure_ascii=False, indent=2)
                else:
                    with open(args.output_file, "a" if text_written else "w", encoding="utf-8") as fh:
                        fh.write(output + "\n")
                    text_written = True
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Error: failed to write output file: {exc}")

    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
