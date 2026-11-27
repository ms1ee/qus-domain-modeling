"""CLI for the Beijing Subway fare calculation system."""
import argparse
import sys

from data_manager import DataManager
from data_loader import DATA_FILE_PATH
from pathfinding import PathfindingConfig, ShortestPath
from report import Route, to_text, to_json

PROMPT = "Enter 'Starting Station; Ending Station' (or 'q' to quit): "


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


def parse_input(text):
    """Return (start, end, error)."""
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None, None, "Input format incorrect, please use 'Starting Station; Ending Station' format"
    return parts[0].strip(), parts[1].strip(), None


def query(graph, start, end, args):
    """Run a query; return output string or raise ValueError with message."""
    if start not in graph.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if end not in graph.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    prefs = [args.line_preference] if args.line_preference else []
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = prefs
    try:
        s = graph.station_to_number[start]
        t = graph.station_to_number[end]
        sp = ShortestPath(graph, s, cfg)
        nodes, edges = sp.path_with_edges(t)
    except Exception as ex:
        raise ValueError("Path calculation failed: %s" % ex)
    if not nodes:
        raise ValueError("No route found from '%s' to '%s' under the given constraints" % (start, end))
    names = [graph.number_to_station[n] for n in nodes]
    route = Route(names, edges, sp.dist_to[t], sp.get_transfer_count(t))
    try:
        if args.format == "json":
            return to_json(route, start, end, args.mode, args.max_transfers, args.line_preference)
        return to_text(route, start, end)
    except Exception as ex:
        raise ValueError("Fare calculation failed: %s" % ex)


def emit(text, args):
    print(text)
    if args.output_file:
        try:
            with open(args.output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n\n")
        except OSError as ex:
            print("Cannot write output file: %s" % ex)


def main(argv=None):
    args = parse_args(argv)
    dm = DataManager(DATA_FILE_PATH)
    try:
        graph = dm.load()
    except Exception as ex:
        print("Failed to load subway data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("Lines: %s" % ", ".join(str(l) for l in dm.lines()))
        print("Stations: %d" % len(graph.station_to_number))
        if ok:
            print("Data check passed.")
            return 0
        print("Data check found %d issue(s):" % len(msgs))
        for m in msgs[:50]:
            print("  - " + m)
        return 1
    while True:
        try:
            line = input(PROMPT)
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        start, end, err = parse_input(line)
        if err:
            print(err)
            continue
        try:
            emit(query(graph, start, end, args), args)
        except ValueError as ex:
            print(ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
