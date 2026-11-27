"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import json
import re
import sys

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data
from data_manager import SubwayDataManager
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
from report import build_route_info, format_json, format_text

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_query(line):
    parts = [p.strip() for p in re.split(r"[;,；，]", line)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def resolve_station(name, station_to_number):
    name = " ".join(name.split())
    if name in station_to_number:
        return name
    candidates = [name]
    for suffix in ("站", " Station", " station"):
        if name.endswith(suffix):
            candidates.append(name[: -len(suffix)].strip())
    lower = {k.lower(): k for k in station_to_number}
    for c in candidates:
        if c in station_to_number:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def _missing_msg(role, name, station_to_number):
    msg = "%s station '%s' does not exist, please check the station name" % (role, name)
    sugg = difflib.get_close_matches(name, list(station_to_number), n=3, cutoff=0.6)
    if sugg:
        msg += " (did you mean: %s?)" % ", ".join(sugg)
    return msg


def run_query(line, graph, station_to_number, number_to_station, config):
    start_raw, end_raw = parse_query(line)
    start = resolve_station(start_raw, station_to_number)
    if start is None:
        raise LookupError(_missing_msg("Starting", start_raw, station_to_number))
    end = resolve_station(end_raw, station_to_number)
    if end is None:
        raise LookupError(_missing_msg("Ending", end_raw, station_to_number))
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(graph, station_to_number[start], config)
        nodes, edges = sp.path_with_edges(station_to_number[end])
    except Exception as exc:
        raise RuntimeError("Path calculation error: %s" % exc)
    if not nodes:
        raise RuntimeError("No route found from '%s' to '%s' under current settings" % (start, end))
    try:
        return build_route_info(start, end, config.mode, nodes, edges, number_to_station)
    except Exception as exc:
        raise RuntimeError("Fare calculation error: %s" % exc)


def check_data(path):
    try:
        mgr = SubwayDataManager(path=path)
    except Exception as exc:
        print("Failed to load data: %s" % exc)
        return 1
    res = mgr.check_integrity()
    print("Stations: %d, Connections: %d, Lines: %d"
          % (res["station_count"], res["connection_count"], res["line_count"]))
    for e in res["errors"]:
        print("ERROR: %s" % e)
    for w in res["warnings"]:
        print("WARNING: %s" % w)
    if res["errors"]:
        print("Data integrity check FAILED (%d errors)" % len(res["errors"]))
        return 1
    print("Data integrity check passed (%d warnings)" % len(res["warnings"]))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    parser.add_argument("--output_file", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance")
    parser.add_argument("--max_transfers", type=int, default=None)
    parser.add_argument("--line_preference", action="append", default=None)
    parser.add_argument("--check_data", action="store_true")
    parser.add_argument("--data_file", default=DATA_FILE_PATH)
    args = parser.parse_args(argv)

    if args.check_data:
        return check_data(args.data_file)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 2
    prefs = []
    for p in args.line_preference or []:
        prefs.extend(x.strip() for x in p.split(",") if x.strip())

    try:
        data = load_subway_data(args.data_file)
        graph, s2n, n2s = build_graph(data)
    except Exception as exc:
        print("Failed to load subway data: %s" % exc)
        return 1
    config = PathfindingConfig(args.mode, args.max_transfers, prefs)

    json_results = []
    if args.output_file:
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as exc:
            print("Cannot open output file: %s" % exc)
            return 1

    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            sys.stdout.write("> ")
            sys.stdout.flush()
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print()
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        try:
            info = run_query(line, graph, s2n, n2s, config)
        except (ValueError, LookupError, RuntimeError) as exc:
            print(str(exc))
            continue
        except Exception as exc:
            print("Unexpected error: %s" % exc)
            continue
        text = format_json(info) if args.format == "json" else format_text(info)
        print(text)
        if args.output_file:
            try:
                if args.format == "json":
                    json_results.append(info)
                    with open(args.output_file, "w", encoding="utf-8") as fh:
                        json.dump(json_results if len(json_results) > 1 else json_results[0],
                                  fh, ensure_ascii=False, indent=2)
                else:
                    with open(args.output_file, "a", encoding="utf-8") as fh:
                        fh.write(text + "\n")
            except OSError as exc:
                print("Failed to write output file: %s" % exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
