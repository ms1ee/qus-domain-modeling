"""Command-line interface of the Beijing Subway fare calculation system.

Usage::

    python main.py [--output_file FILE] [--format text|json]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as ``Starting Station; Ending Station``; type ``q`` to quit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, DataLoadError
from data_manager import DataError, DataIntegrityChecker, SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath
from report import build_route, format_json_report, format_text_report, generate_summary, route_to_dict

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SAME_STATION_ERROR = "Starting station cannot be the same as the ending station"
QUIT_COMMANDS = {"q", "quit", "exit"}


class QueryError(Exception):
    """User-facing query error."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="Export query results to this file")
    parser.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    parser.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES),
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. 'Line 1' (comma separated for several)")
    parser.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def parse_query_input(raw):
    """Split 'Start; End' into two station names (raises QueryError)."""
    if raw is None:
        raise QueryError(FORMAT_ERROR)
    text = raw.replace("；", ";").strip()
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def validate_stations(network, start, end):
    """Return the official names of start and end stations (raises QueryError)."""
    resolved_start = network.resolve_station_name(start)
    if resolved_start is None:
        msg = f"Starting station '{start}' does not exist, please check the station name"
        hints = network.suggest_stations(start)
        if hints:
            msg += f" (did you mean: {', '.join(hints)}?)"
        raise QueryError(msg)
    resolved_end = network.resolve_station_name(end)
    if resolved_end is None:
        msg = f"Ending station '{end}' does not exist, please check the station name"
        hints = network.suggest_stations(end)
        if hints:
            msg += f" (did you mean: {', '.join(hints)}?)"
        raise QueryError(msg)
    if resolved_start == resolved_end:
        raise QueryError(SAME_STATION_ERROR)
    return resolved_start, resolved_end


def resolve_preferred_lines(network, line_preference, err=sys.stderr):
    if not line_preference:
        return []
    result = []
    for item in line_preference.split(","):
        item = item.strip()
        if not item:
            continue
        matches = network.resolve_line_names(item)
        if not matches:
            print(f"Warning: preferred line '{item}' not found in network data, ignored", file=err)
        result.extend(m for m in matches if m not in result)
    return result


def process_query(network, start, end, config):
    """Compute the route for two official station names. Returns (route, summary)."""
    try:
        sp = ShortestPath(network.graph, network.station_to_number[start], config)
        stations, edges = sp.path_with_edges(network.station_to_number[end])
    except Exception as exc:  # path calculation exception handling
        raise QueryError(f"Path calculation error: {exc}") from exc
    if not stations:
        if config.max_transfers is not None:
            raise QueryError(f"No route found from '{start}' to '{end}' within "
                             f"{config.max_transfers} transfer(s)")
        raise QueryError(f"No route found from '{start}' to '{end}'")
    try:
        route = build_route(network, stations, edges)
        summary = generate_summary(route)
    except Exception as exc:  # fare calculation exception handling
        raise QueryError(f"Fare calculation error: {exc}") from exc
    return route, summary


def _write_output(args, text_report, json_results):
    try:
        if args.format == "json":
            payload = json_results[0] if len(json_results) == 1 else json_results
            with open(args.output_file, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        else:
            with open(args.output_file, "a", encoding="utf-8") as handle:
                handle.write(text_report + "\n\n")
        return True
    except OSError as exc:
        print(f"Error: unable to write output file '{args.output_file}': {exc}")
        return False


def run_interactive(network, args, config):
    print("Beijing Subway Fare Calculation System")
    print(f"Loaded {len(network.stations)} stations, {len(network.connections)} connections, "
          f"{len(network.all_line_names())} lines.")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    json_results = []
    if args.output_file and args.format == "text":
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as exc:
            print(f"Error: unable to write output file '{args.output_file}': {exc}")
    while True:
        try:
            raw = input("\nQuery> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        raw = raw.strip()
        if not raw:
            continue
        if raw.lower() in QUIT_COMMANDS:
            print("Goodbye!")
            break
        try:
            start, end = parse_query_input(raw)
            start, end = validate_stations(network, start, end)
            route, summary = process_query(network, start, end, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # never crash the query loop
            print(f"Error: unexpected failure: {exc}")
            continue
        query_info = {
            "start": start,
            "end": end,
            "raw_input": raw,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": config.preferred_lines,
        }
        text_report = format_text_report(route, summary, query_info)
        if args.format == "json":
            print(format_json_report(route, summary, query_info))
        else:
            print(text_report)
        if args.output_file:
            json_results.append(route_to_dict(route, summary, query_info))
            if _write_output(args, text_report, json_results):
                print(f"Result exported to {args.output_file}")
    return 0


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(data_source=args.data_file)
    except (DataLoadError, DataError) as exc:
        print(f"Error: {exc}")
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(network)
        result = checker.run_all()
        print(checker.format_report(result))
        return 0 if result["valid"] else 1

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=resolve_preferred_lines(network, args.line_preference,
                                                                           sys.stdout))
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    return run_interactive(network, args, config)


if __name__ == "__main__":
    sys.exit(main())
