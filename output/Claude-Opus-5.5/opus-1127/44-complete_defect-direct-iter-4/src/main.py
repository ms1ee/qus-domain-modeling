"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--output_file PATH] [--format text|json]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' to exit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayDataManager
from fare_calculator import FareCalculationError, Sum_money, calculate_estimated_time
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_route_result, format_json, format_text

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Invalid user input."""


class PathCalculationError(Exception):
    """Path could not be computed."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="Export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--mode", choices=list(MODES), default="shortest_distance",
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated (e.g. 'Line 1')")
    parser.add_argument("--check_data", action="store_true", help="Check data integrity and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")
    return args


def parse_query(text, manager):
    """Validate a query string; return (start, end) official station names."""
    if text is None:
        raise QueryError(FORMAT_ERROR)
    normalized = text.replace("\uff1b", ";")
    parts = normalized.split(";")
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start_raw, end_raw = parts[0].strip(), parts[1].strip()
    if not start_raw or not end_raw:
        raise QueryError(FORMAT_ERROR)
    start = manager.resolve_station(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = manager.resolve_station(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return start, end


def compute_route(manager, start, end, config):
    """Compute the route and return the structured result dict."""
    try:
        s = manager.station_to_number[start]
        t = manager.station_to_number[end]
        sp = ShortestPath(manager.graph, s, config)
    except Exception as exc:
        raise PathCalculationError(str(exc)) from exc
    if not sp.has_path_to(t):
        msg = f"No route found from '{start}' to '{end}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        raise PathCalculationError(msg)
    nodes, edges = sp.path_with_edges(t)
    distance = sp.dist_to[t]
    transfers = sp.get_transfer_count(t)
    try:
        fare = Sum_money(distance)
    except FareCalculationError:
        raise
    except Exception as exc:
        raise FareCalculationError(str(exc)) from exc
    est = calculate_estimated_time(distance, transfers)
    return build_route_result(start, end, config.mode, nodes, edges, manager.number_to_station,
                              distance, fare, est, transfers)


def write_output(path, results, fmt):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(format_text(r) for r in results) + "\n")


def main(argv=None):
    args = parse_args(argv)
    try:
        manager = SubwayDataManager(path=args.data_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading subway data: {exc}")
        return 1

    if args.check_data:
        report = manager.check_integrity()
        print(manager.format_integrity_report(report))
        return 0 if report["ok"] else 1

    preferred = []
    if args.line_preference:
        for item in args.line_preference.split(","):
            item = item.strip()
            if not item:
                continue
            resolved = manager.resolve_line(item)
            if resolved is None:
                print(f"Warning: preferred line '{item}' not found in data")
                resolved = item
            preferred.append(resolved)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")
    results = []
    while True:
        try:
            raw = input("Query> ")
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break
        raw = raw.strip()
        if not raw:
            continue
        if raw.lower() in ("quit", "exit", "q"):
            break
        try:
            start, end = parse_query(raw, manager)
        except QueryError as exc:
            print(exc)
            continue
        try:
            result = compute_route(manager, start, end, config)
        except PathCalculationError as exc:
            print(f"Path calculation error: {exc}")
            continue
        except FareCalculationError as exc:
            print(f"Fare calculation error: {exc}")
            continue
        except Exception as exc:  # pragma: no cover - safety net
            print(f"Unexpected error: {exc}")
            continue

        print(format_json(result) if args.format == "json" else format_text(result))
        results.append(result)
        if args.output_file:
            try:
                write_output(args.output_file, results, args.format)
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
