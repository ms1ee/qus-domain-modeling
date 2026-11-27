"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data, build_graph  # noqa: E402
from data_manager import SubwayDataManager  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES  # noqa: E402
from report import build_route_info, format_text, format_json  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH)
    return p.parse_args(argv)


def parse_query(line):
    parts = [x.strip() for x in re.split(r"[;,；，]", line)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def resolve_station(name, station_to_number, role):
    if name in station_to_number:
        return name
    lower = {k.lower(): k for k in station_to_number}
    if name.lower() in lower:
        return lower[name.lower()]
    matches = difflib.get_close_matches(name, list(station_to_number), n=1, cutoff=0.5)
    if matches:
        print("Note: %s station '%s' not found, using nearest match '%s'" % (role, name, matches[0]))
        return matches[0]
    raise ValueError("%s station '%s' does not exist, please check the station name" % (role, name))


def run_check(data):
    ok, errors, warnings = SubwayDataManager(data).check_integrity()
    print("Data integrity check: %d stations, %d connections" %
          (len(data["stations"]), len(data["connections"])))
    for e in errors:
        print("ERROR: " + e)
    for w in warnings:
        print("WARNING: " + w)
    print("Result: %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def handle_query(line, graph, s2n, n2s, config, args):
    start, end = parse_query(line)
    start = resolve_station(start, s2n, "Starting")
    end = resolve_station(end, s2n, "Ending")
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(graph, s2n[start], config)
    except Exception as exc:
        raise RuntimeError("Path calculation error: %s" % exc)
    if not sp.has_path_to(s2n[end]):
        raise RuntimeError("No path found from '%s' to '%s' under current settings" % (start, end))
    try:
        info = build_route_info(sp, s2n[end], n2s,
                                {"start": start, "end": end, "mode": config.mode})
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Fare calculation error: %s" % exc)
    text = format_json(info) if args.format == "json" else format_text(info)
    print(text)
    if args.output_file:
        try:
            with open(args.output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
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
        return run_check(data)
    graph, s2n, n2s = build_graph(data)
    prefs = [x.strip() for x in args.line_preference.split(",")] if args.line_preference else []
    config = PathfindingConfig(args.mode, args.max_transfers, prefs)
    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (or 'quit').")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        try:
            handle_query(line, graph, s2n, n2s, config, args)
        except (ValueError, RuntimeError) as exc:
            print(exc)
        except Exception as exc:  # last-resort handler
            print("Unexpected error: %s" % exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
