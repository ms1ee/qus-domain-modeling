"""Command line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data, build_network, check_data_integrity
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
from visualization import build_route_result, format_text_report, format_json_report

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
    lowered = {s.lower(): s for s in station_to_number}
    if name.lower() in lowered:
        return lowered[name.lower()]
    matches = difflib.get_close_matches(name, list(station_to_number), n=1, cutoff=0.5)
    if matches:
        return matches[0]
    raise ValueError(f"{role} station '{name}' does not exist, please check the station name")


def process_query(line, graph, s2n, n2s, config):
    start, end = parse_query(line)
    start = resolve_station(start, s2n, "Starting")
    end = resolve_station(end, s2n, "Ending")
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(graph, s2n[start], config)
        nodes, edges = sp.path_with_edges(s2n[end])
    except Exception as exc:
        raise RuntimeError(f"Path calculation error: {exc}")
    if not edges:
        raise RuntimeError(f"No path found from '{start}' to '{end}' under current settings")
    try:
        return build_route_result(start, end, nodes, edges, n2s,
                                  sp.get_transfer_count(s2n[end]), config.mode)
    except Exception as exc:
        raise RuntimeError(f"Fare calculation error: {exc}")


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except Exception as exc:
        print(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = check_data_integrity(data)
        st = report["stats"]
        print(f"Stations: {st['stations']}, Connections: {st['connections']}, Lines: {st['lines']}")
        for e in report["errors"]:
            print(f"ERROR: {e}")
        for w in report["warnings"]:
            print(f"WARNING: {w}")
        print("Data integrity check passed" if report["ok"] else "Data integrity check failed")
        return 0 if report["ok"] else 1

    graph, s2n, n2s = build_network(data)
    prefs = [x.strip() for x in args.line_preference.split(",")] if args.line_preference else []
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=prefs)

    out_f = None
    if args.output_file:
        try:
            out_f = open(args.output_file, "w", encoding="utf-8")
        except OSError as exc:
            print(f"Cannot open output file: {exc}")
            return 1

    try:
        while True:
            print("Enter 'Starting Station; Ending Station' (or 'quit' to exit):")
            sys.stdout.flush()
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            try:
                result = process_query(line, graph, s2n, n2s, config)
            except (ValueError, RuntimeError) as exc:
                print(exc)
                continue
            text = format_json_report(result) if args.format == "json" else format_text_report(result)
            print(text)
            if out_f:
                out_f.write(text + "\n")
                out_f.flush()
    finally:
        if out_f:
            out_f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
