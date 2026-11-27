"""CLI entry point for the Beijing Subway fare system."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataIntegrityChecker, DataManager  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath  # noqa: E402
from report import Route, json_report, summarize, text_report  # noqa: E402

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


def validate_input(text, graph):
    """Return (start, end, error)."""
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, FORMAT_ERR
    s, e = parts
    if s not in graph.station_to_number:
        return None, None, f"Starting station '{s}' does not exist, please check the station name"
    if e not in graph.station_to_number:
        return None, None, f"Ending station '{e}' does not exist, please check the station name"
    if s == e:
        return None, None, "Starting station cannot be the same as the ending station"
    return s, e, None


def run_query(graph, start, end, args):
    cfg = PathfindingConfig(args.mode, args.max_transfers,
                            [args.line_preference] if args.line_preference else [])
    try:
        sp = ShortestPath(graph, graph.station_to_number[start], cfg)
        nodes, edges = sp.path_with_edges(graph.station_to_number[end])
    except Exception as ex:  # path calculation failure
        return None, f"Path calculation failed: {ex}"
    if not nodes:
        return None, "No route found between the stations (check --max_transfers)"
    names = [graph.number_to_station[n] for n in nodes]
    route = Route(names, edges, graph)
    try:
        summary = summarize(route)
    except Exception as ex:  # fare failure
        return None, f"Fare calculation failed: {ex}"
    if args.format == "json":
        return json_report(start, end, args.mode, route, summary), None
    return text_report(start, end, route, summary), None


def emit(content, args):
    print(content)
    if args.output_file:
        try:
            with open(args.output_file, "a", encoding="utf-8") as f:
                f.write(content + "\n")
        except OSError as ex:
            print(f"Cannot write output file: {ex}")


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as ex:
        print(f"Failed to load subway data: {ex}")
        return 1
    if args.check_data:
        ok, problems = DataIntegrityChecker(dm).run()
        print("Data check passed" if ok else "Data check found problems:")
        for p in problems:
            print(" - " + p)
        return 0 if ok else 1
    graph = dm.get_graph()
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' (q to quit).")
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
        s, e, err = validate_input(line, graph)
        if err:
            print(err)
            continue
        content, err = run_query(graph, s, e, args)
        if err:
            print(err)
            continue
        emit(content, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
