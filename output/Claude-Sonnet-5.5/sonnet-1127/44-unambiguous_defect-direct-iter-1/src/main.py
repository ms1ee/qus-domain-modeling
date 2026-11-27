"""CLI entry point for the Beijing Subway fare calculator."""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from data_manager import SubwayNetwork  # noqa: E402
from pathfinding import PathfindingConfig, ShortestPath  # noqa: E402
from reporter import build_summary, format_json, format_text  # noqa: E402


def parse_input(line):
    parts = [p.strip() for p in re.split(r"[;；,，]", line)]
    parts = [p for p in parts if p != ""]
    if len(parts) != 2 or len(re.split(r"[;；,，]", line)) != 2:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    return parts[0], parts[1]


def query(network, start, end, config):
    if start not in network.station_to_number:
        raise ValueError(f"Starting station '{start}' does not exist, please check the station name")
    if end not in network.station_to_number:
        raise ValueError(f"Ending station '{end}' does not exist, please check the station name")
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    s, t = network.station_to_number[start], network.station_to_number[end]
    try:
        sp = ShortestPath(network.graph, s, config)
        nodes, edges = sp.path_with_edges(t)
    except Exception as ex:
        raise RuntimeError(f"Path calculation failed: {ex}")
    if not nodes:
        raise ValueError("No route found (check max transfer limit)")
    try:
        return build_summary(network, start, end, nodes, edges)
    except Exception as ex:
        raise RuntimeError(f"Fare calculation failed: {ex}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    ap.add_argument("--output_file")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                    default="shortest_distance")
    ap.add_argument("--max_transfers", type=int)
    ap.add_argument("--line_preference")
    ap.add_argument("--check_data", action="store_true")
    args = ap.parse_args(argv)

    try:
        network = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as ex:
        print(f"Failed to load data: {ex}")
        return 1

    if args.check_data:
        problems = network.check_integrity()
        print(f"Stations: {len(network.station_to_number)}, edges: {network.graph.edge_count()}")
        if problems:
            for p in problems:
                print("Problem:", p)
            return 1
        print("Data check passed.")
        return 0

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []

    results = []
    while True:
        try:
            line = input("Enter 'Starting Station; Ending Station' (q to quit): ")
        except EOFError:
            break
        line = line.strip()
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        try:
            start, end = parse_input(line)
            summary = query(network, start, end, config)
        except (ValueError, RuntimeError) as ex:
            print(ex)
            continue
        text = format_json(summary) if args.format == "json" else format_text(summary)
        print(text)
        results.append(text)
    if args.output_file and results:
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(results) + "\n")
        except OSError as ex:
            print(f"Cannot write output file: {ex}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
