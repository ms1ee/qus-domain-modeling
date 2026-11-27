"""Command line interface."""
import argparse
import re
import sys

from data_manager import DataManager, DataIntegrityChecker
from pathfinding import PathfindingConfig, ShortestPath
from report import build_summary, render

SEP = re.compile(r"[;；,，]")


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


def validate_input(text, graph):
    """Return (start, end, error)."""
    parts = SEP.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None, None, "Input format incorrect, please use 'Starting Station; Ending Station' format"
    a, b = parts[0].strip(), parts[1].strip()
    if not graph.has_station(a):
        return None, None, "Starting station '%s' does not exist, please check the station name" % a
    if not graph.has_station(b):
        return None, None, "Ending station '%s' does not exist, please check the station name" % b
    if a == b:
        return None, None, "Starting station cannot be the same as the ending station"
    return a, b, None


def query(manager, a, b, args):
    g = manager.graph
    cfg = PathfindingConfig(args.mode, args.max_transfers,
                            [args.line_preference] if args.line_preference else [])
    try:
        sp = ShortestPath(g, g.station_to_number[a], cfg)
        t = g.station_to_number[b]
        nodes, edges = sp.path_with_edges(t)
    except Exception as ex:
        raise RuntimeError("Path calculation failed: %s" % ex)
    if not nodes:
        raise RuntimeError("No route found between '%s' and '%s' (check --max_transfers)" % (a, b))
    return build_summary(g, a, b, nodes, edges, args.mode)


def main(argv=None, stdin=None, stdout=None):
    args = parse_args(argv)
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        manager = DataManager()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex, file=stdout)
        return 1
    if args.check_data:
        checker = DataIntegrityChecker(manager)
        print(checker.report(), file=stdout)
        return 0 if checker.check() else 1
    if args.output_file:
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as ex:
            print("Cannot write output file: %s" % ex, file=stdout)
            args.output_file = None
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit):", file=stdout)
    while True:
        line = stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        a, b, err = validate_input(line, manager.graph)
        if err:
            print(err, file=stdout)
            continue
        try:
            content = render(query(manager, a, b, args), args.format)
        except Exception as ex:
            print(str(ex), file=stdout)
            continue
        print(content, file=stdout)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(content + "\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex, file=stdout)
    return 0
