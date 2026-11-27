"""CLI entry point for the Beijing Subway fare calculator."""
import argparse
import difflib
import re
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, ShortestPath
from report import PathSummary, ReportExporter, make_route

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def resolve_station(name, dm):
    if name in dm.station_to_number:
        return name
    m = difflib.get_close_matches(name, list(dm.station_to_number), n=1, cutoff=0.5)
    return m[0] if m else None


def process_query(text, dm, args, exporter):
    parts = [p.strip() for p in re.split(r"[;；,，]", text) if p.strip()]
    if len(parts) != 2:
        return FORMAT_ERR
    s_raw, e_raw = parts
    s = resolve_station(s_raw, dm)
    if s is None:
        return "Starting station '%s' does not exist, please check the station name" % s_raw
    e = resolve_station(e_raw, dm)
    if e is None:
        return "Ending station '%s' does not exist, please check the station name" % e_raw
    if s == e:
        return "Starting station cannot be the same as the ending station"
    cfg = PathfindingConfig(args.mode, args.max_transfers,
                            [args.line_preference] if args.line_preference else [])
    try:
        sp = ShortestPath(dm.graph, dm.station_to_number[s], cfg)
        t = dm.station_to_number[e]
        nodes, edges = sp.path_with_edges(t)
    except Exception as ex:
        return "Path calculation failed: %s" % ex
    if not nodes:
        return "No route found from '%s' to '%s' under the current settings" % (s, e)
    try:
        route = make_route([dm.number_to_station[n] for n in nodes], edges, sp.dist_to[t])
        summary = PathSummary(route)
    except Exception as ex:
        return "Fare calculation failed: %s" % ex
    out = exporter.render(s, e, summary)
    try:
        exporter.export(out)
    except OSError as ex:
        out += "\n(Could not write output file: %s)" % ex
    return out


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    exporter = ReportExporter(args.format, args.output_file)
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit):")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        print(process_query(line, dm, args, exporter))
    return 0


if __name__ == "__main__":
    sys.exit(main())
