"""Command-line interface."""
import argparse
import sys

from data_manager import DataManager
from pathfinding import ShortestPath, PathfindingConfig
import report

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


def parse_query(text):
    """Return (start, end) or raise ValueError with a message."""
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def run_query(dm, args, text):
    start, end = parse_query(text)
    g = dm.graph
    if start not in g.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if end not in g.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    if args.line_preference:
        cfg.preferred_lines = [dm.resolve_line(args.line_preference)]
    try:
        sp = ShortestPath(g, g.station_to_number[start], cfg)
        nodes, edges = sp.path_with_edges(g.station_to_number[end])
    except Exception as e:
        raise ValueError("Path calculation failed: %s" % e)
    if not edges:
        raise ValueError("No route found between '%s' and '%s' under the given constraints" % (start, end))
    try:
        route = report.build_route(g, nodes, edges)
        return report.generate(start, end, args.mode, route, args.format)
    except Exception as e:
        raise ValueError("Fare calculation failed: %s" % e)


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' (q to quit).")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in ("q", "quit", "exit"):
            break
        try:
            result = run_query(dm, args, text)
        except ValueError as e:
            print(e)
            continue
        except Exception as e:
            print("Unexpected error: %s" % e)
            continue
        print(result)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n\n")
            except OSError as e:
                print("Cannot write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
