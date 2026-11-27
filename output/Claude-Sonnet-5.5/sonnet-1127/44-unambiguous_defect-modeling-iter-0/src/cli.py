"""Command-line interface."""
import argparse
import re
import sys

from data_manager import DataManager
from models import PathQuery, Route
from pathfinding import ShortestPath, PathfindingConfig
from report import RouteReport

MODES = ("shortest_distance", "least_transfer", "comprehensive")


def find_route(dm, query):
    g = dm.graph
    s = g.station_to_number[query.start]
    t = g.station_to_number[query.end]
    pref = [query.line_preference] if query.line_preference else []
    cfg = PathfindingConfig(query.mode, query.max_transfers, pref)
    sp = ShortestPath(g, s, cfg)
    nodes, edges = sp.path_with_edges(t)
    if not nodes:
        return None
    names = [g.number_to_station[n] for n in nodes]
    lines, tstations = [], []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    for a, b in zip(edges, edges[1:]):
        if a.line != b.line:
            tstations.append((g.number_to_station[a.dest], a.line, b.line))
    return Route(names, edges, sp.dist_to[t], len(tstations), lines, tstations)


def parse_input(text):
    parts = [p.strip() for p in re.split(r"[;；,，]", text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts


def validate(dm, a, b):
    for label, n in (("Starting", a), ("Ending", b)):
        if not dm.has_station(n):
            msg = "%s station '%s' does not exist, please check the station name" % (label, n)
            sug = dm.suggest(n)
            if sug:
                msg += " (did you mean: %s?)" % ", ".join(sug)
            raise ValueError(msg)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=MODES, default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p


def run_query(dm, text, args):
    a, b = parse_input(text)
    validate(dm, a, b)
    q = PathQuery(a, b, args.mode, args.max_transfers, args.line_preference)
    try:
        route = find_route(dm, q)
    except Exception as ex:
        raise ValueError("Path calculation failed: %s" % ex)
    if route is None:
        raise ValueError("No route found between '%s' and '%s'%s" % (
            a, b, " within the transfer limit" if args.max_transfers is not None else ""))
    try:
        rep = RouteReport(q, route, args.format, args.output_file)
    except Exception as ex:
        raise ValueError("Fare calculation failed: %s" % ex)
    return rep


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 2
    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, issues = dm.check_data()
        print("Data check passed." if ok else "Data check found %d issue(s):" % len(issues))
        for i in issues:
            print(" - " + i)
        return 0 if ok else 1
    first = True
    print("Enter 'Starting Station; Ending Station' (q to quit)")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        try:
            rep = run_query(dm, line, args)
        except ValueError as ex:
            print(ex)
            continue
        out = rep.render()
        print(out)
        if args.output_file:
            try:
                with open(args.output_file, "w" if first else "a", encoding="utf-8") as f:
                    f.write(out + "\n")
                first = False
            except OSError as ex:
                print("Could not write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
