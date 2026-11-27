"""CLI for Beijing Subway fare calculation."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import build_graph, check_data
from pathfinding import PathfindingConfig, ShortestPath
from report import build_summary, format_json, format_text

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_query(text):
    """Return (start, end) or raise ValueError with a message."""
    text = text.replace("；", ";")
    parts = [p.strip() for p in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def run_query(text, graph, s2n, n2s, config, fmt):
    start, end = parse_query(text)
    if start not in s2n:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % start)
    if end not in s2n:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % end)
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(graph, s2n[start], config)
        if s2n[end] not in sp.dist_to:
            raise ValueError("No route found between '%s' and '%s' under current constraints" % (start, end))
        nodes, edges = sp.path_with_edges(s2n[end])
    except ValueError:
        raise
    except Exception as ex:
        raise ValueError("Path calculation failed: %s" % ex)
    try:
        summary = build_summary(start, end, nodes, edges, n2s)
    except Exception as ex:
        raise ValueError("Fare calculation failed: %s" % ex)
    return format_json(summary) if fmt == "json" else format_text(summary)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    ap.add_argument("--output_file", default=None)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                    default="shortest_distance")
    ap.add_argument("--max_transfers", type=int, default=None)
    ap.add_argument("--line_preference", default=None)
    ap.add_argument("--check_data", action="store_true")
    args = ap.parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except Exception as ex:
        print("Failed to load data: %s" % ex)
        return 1

    if args.check_data:
        problems = check_data(data)
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for p in problems:
                print(" - " + p)
            return 1
        print("Data check passed: %d stations, %d connections" % (
            len(data["stations"]), len(data["connections"])))
        return 0

    graph, s2n, n2s = build_graph(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [args.line_preference]

    print("Enter 'Starting Station; Ending Station' (empty line or 'q' to quit)")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line or line.lower() in ("q", "quit", "exit"):
            break
        try:
            result = run_query(line, graph, s2n, n2s, config, args.format)
        except ValueError as ex:
            print(ex)
            continue
        print(result)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
