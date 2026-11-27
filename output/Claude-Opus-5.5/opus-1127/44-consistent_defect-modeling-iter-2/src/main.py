"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH
from network import SubwayNetwork
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_json_dict, build_route, format_text

EXIT_WORDS = {"quit", "exit", "q"}
FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH)
    return p.parse_args(argv)


def parse_query(line):
    parts = [x.strip() for x in re.split(r"[;,；，]", line)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def handle_query(network, line, config, fmt):
    """Process one query line. Returns (output string, result object or None)."""
    q = parse_query(line)
    if q is None:
        return FORMAT_ERROR, None
    notes = []
    resolved = []
    for label, name in (("Starting", q[0]), ("Ending", q[1])):
        r, exact = network.resolve_station(name)
        if r is None:
            return f"{label} station '{name}' does not exist, please check the station name", None
        if not exact:
            notes.append(f"Note: {label.lower()} station '{name}' matched to '{r}'")
        resolved.append(r)
    start, end = resolved
    if start == end:
        return "Starting station cannot be the same as the ending station", None
    try:
        sp = ShortestPath(network.graph, network.station_to_number[start], config)
        route = build_route(sp, network.station_to_number[end], network.number_to_station)
    except ValueError as exc:
        return f"Fare calculation error: {exc}", None
    except Exception as exc:  # noqa: BLE001
        return f"Path calculation error: {exc}", None
    if route is None:
        return f"No route found from '{start}' to '{end}' under the current settings", None
    if fmt == "json":
        obj = build_json_dict(start, end, route, config.mode)
        body = json.dumps(obj, ensure_ascii=False, indent=2)
    else:
        obj = format_text(start, end, route, config.mode)
        body = obj
    return "\n".join(notes + [body]), obj


def write_output(path, results, fmt):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            if fmt == "json":
                data = results[0] if len(results) == 1 else results
                json.dump(data, fh, ensure_ascii=False, indent=2)
            else:
                fh.write(("\n\n" + "-" * 40 + "\n\n").join(results) + "\n")
    except OSError as exc:
        print(f"Failed to write output file '{path}': {exc}")


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        res = network.check_integrity()
        print("Data integrity check")
        print(f"  Stations: {len(network.stations)}, connections: {len(network.connections)}")
        print(f"  Station coverage: {'OK' if res.station_coverage_valid else 'FAILED'}")
        print(f"  Connection integrity: {'OK' if res.connection_integrity_valid else 'FAILED'}")
        print(f"  Distance accuracy: {'OK' if res.distance_accuracy_valid else 'FAILED'}")
        for m in res.messages:
            print("  - " + m)
        return 0 if res.valid else 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 1
    config = PathfindingConfig(args.mode, args.max_transfers, args.line_preference)
    results = []
    print("Beijing Subway Fare Calculator (type 'quit' to exit)")
    while True:
        try:
            line = input("Please enter 'Starting Station; Ending Station': ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in EXIT_WORDS:
            break
        output, obj = handle_query(network, line, config, args.format)
        print(output)
        if obj is not None and args.output_file:
            results.append(obj)
            write_output(args.output_file, results, args.format)
    return 0


if __name__ == "__main__":
    sys.exit(main())
