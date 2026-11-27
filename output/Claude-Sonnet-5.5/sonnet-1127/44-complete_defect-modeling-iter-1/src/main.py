"""CLI entry point for the Beijing Subway fare system."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager
from pathfinding import ShortestPath, PathfindingConfig
from fare_calculator import Sum_money, calculate_estimated_time
import report

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def parse_input(text):
    text = text.replace("；", ";")
    parts = [x.strip() for x in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    return parts[0], parts[1]


def compute_route(dm, start, end, config):
    s, e = dm.station_to_number[start], dm.station_to_number[end]
    sp = ShortestPath(dm.graph, s, config)
    nodes, edges = sp.path_with_edges(e)
    if not nodes:
        raise RuntimeError("No route found between the stations")
    dist = sum(x.distance for x in edges)
    transfers = sp.get_transfer_count(e)
    segments, lines, details = [], [], []
    for i, ed in enumerate(edges):
        a, b = dm.number_to_station[ed.source], dm.number_to_station[ed.dest]
        if segments and segments[-1][0] == ed.line:
            segments[-1][2] = b
        else:
            if segments:
                details.append((a, segments[-1][0], ed.line))
            segments.append([ed.line, a, b])
        if ed.line not in lines:
            lines.append(ed.line)
    try:
        fare = Sum_money(dist)
    except Exception as ex:
        raise ArithmeticError(f"Fare calculation failed: {ex}")
    return {"stations": [dm.number_to_station[n] for n in nodes], "distance": dist,
            "fare": fare, "time": calculate_estimated_time(dist, transfers),
            "transfers": transfers, "lines": lines, "segments": segments,
            "transfer_details": details}


def handle(dm, line, args, config):
    start, end = parse_input(line)
    if start not in dm.station_to_number:
        raise ValueError(f"Starting station '{start}' does not exist, please check the station name")
    if end not in dm.station_to_number:
        raise ValueError(f"Ending station '{end}' does not exist, please check the station name")
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    query = {"start": start, "end": end, "mode": args.mode,
             "max_transfers": args.max_transfers, "line_preference": args.line_preference}
    route = compute_route(dm, start, end, config)
    return report.to_json(query, route) if args.format == "json" else report.to_text(query, route)


def main(argv=None):
    args = parse_args(argv)
    dm = DataManager()
    if args.check_data:
        problems = dm.check_data()
        if problems:
            print("Data check found problems:")
            for p in problems:
                print(" -", p)
            return 1
        print("Data check passed.")
        return 0
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []
    print("Enter 'Starting Station; Ending Station' (empty line or 'quit' to exit)")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line or line.lower() in ("quit", "exit", "q"):
            break
        try:
            result = handle(dm, line, args, config)
        except ValueError as ex:
            print(ex)
            continue
        except Exception as ex:
            print(f"Error: {ex}")
            continue
        print(result)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n\n")
            except OSError as ex:
                print(f"Could not write output file: {ex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
