"""Command-line interface for the Beijing Subway fare calculator."""
import argparse
import re
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, ShortestPath
from report import Query, Route, PathReport

SEPARATORS = re.compile(r"[;；,，]")
FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(text):
    """Return (start, end) or raise ValueError with a user message."""
    parts = [p.strip() for p in SEPARATORS.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def validate(dm, start, end):
    if not dm.has_station(start):
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if not dm.has_station(end):
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")


def run_query(dm, query, fmt="text"):
    """Compute a report for the query; raises ValueError on problems."""
    validate(dm, query.start, query.end)
    g = dm.graph
    cfg = PathfindingConfig(query.mode, query.max_transfers,
                            [query.line_preference] if query.line_preference else [])
    try:
        sp = ShortestPath(g, g.station_to_number[query.start], cfg)
        tgt = g.station_to_number[query.end]
        nodes, edges = sp.path_with_edges(tgt)
    except Exception as e:  # path calculation failure
        raise ValueError("Path calculation failed: %s" % e)
    if not nodes:
        raise ValueError("No route found between '%s' and '%s' (check --max_transfers)"
                         % (query.start, query.end))
    route = Route([g.number_to_station[n] for n in nodes], sp.dist_to[tgt], edges)
    try:
        return PathReport(query, route, fmt)
    except Exception as e:  # fare calculation failure
        raise ValueError("Fare calculation failed: %s" % e)


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None, help="write results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 2
    if args.output_file:
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as e:
            print("Cannot write output file: %s" % e)
            return 2
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' (q to quit).")
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
        try:
            start, end = parse_input(line)
            q = Query(start, end, args.mode, args.max_transfers, args.line_preference)
            rep = run_query(dm, q, args.format)
            text = rep.render()
        except ValueError as e:
            print(e)
            continue
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n\n")
            except OSError as e:
                print("Cannot write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
