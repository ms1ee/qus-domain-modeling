"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--mode MODE] [--format text|json] [--output_file PATH]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]
"""

import argparse
import json
import re
import sys

try:
    from data_loader import DATA_FILE_PATH
    from network import SubwayNetwork, StationNotFoundError, RouteNotFoundError
    from pathfinding import PathfindingConfig, VALID_MODES
    from report import format_route, route_to_dict
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH
    from .network import SubwayNetwork, StationNotFoundError, RouteNotFoundError
    from .pathfinding import PathfindingConfig, VALID_MODES
    from .report import format_route, route_to_dict

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"q", "quit", "exit"}


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None, help="Preferred line(s), comma separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p


def parse_query(text):
    """Split 'Start; End' (or comma separated) input. Returns (start, end) or None."""
    parts = [p.strip() for p in re.split(r"[;；,，]", text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def process_query(network, text, config):
    """Process one input line. Returns (route or None, message or None)."""
    parsed = parse_query(text)
    if parsed is None:
        return None, FORMAT_ERROR
    start_raw, end_raw = parsed
    start = network.find_station(start_raw)
    if start is None:
        return None, f"Starting station '{start_raw}' does not exist, please check the station name"
    end = network.find_station(end_raw)
    if end is None:
        return None, f"Ending station '{end_raw}' does not exist, please check the station name"
    if start == end:
        return None, "Starting station cannot be the same as the ending station"
    notes = []
    if start != start_raw:
        notes.append(f"Note: '{start_raw}' matched to station '{start}'")
    if end != end_raw:
        notes.append(f"Note: '{end_raw}' matched to station '{end}'")
    try:
        route = network.compute_route(start, end, config)
    except (StationNotFoundError, RouteNotFoundError) as exc:
        return None, str(exc)
    except Exception as exc:  # path or fare calculation failures
        return None, f"Path calculation error: {exc}"
    return route, "\n".join(notes) if notes else None


def print_check_report(result):
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


def write_output(path, fmt, routes):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            data = route_to_dict(routes[0]) if len(routes) == 1 else [route_to_dict(r) for r in routes]
            json.dump(data, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(format_route(r, "text") for r in routes) + "\n")


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        network = SubwayNetwork(args.data_file)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        result = network.check_integrity()
        print_check_report(result)
        return 0 if result["valid"] else 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 2
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=args.line_preference)
    if config.preferred_lines:
        known = set(network.lines)
        for ln in config.preferred_lines:
            if ln not in known:
                print(f"Warning: preferred line '{ln}' not found in network data")

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit).")
    routes = []
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        route, message = process_query(network, text, config)
        if message:
            print(message)
        if route is None:
            continue
        try:
            print(format_route(route, args.format))
        except Exception as exc:
            print(f"Fare calculation error: {exc}")
            continue
        routes.append(route)
        if args.output_file:
            try:
                write_output(args.output_file, args.format, routes)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
