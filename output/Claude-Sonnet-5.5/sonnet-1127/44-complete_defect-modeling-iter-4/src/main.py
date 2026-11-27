"""CLI entry point for the Beijing Subway fare system."""
import argparse
import sys

from fare_calculator import Sum_money
from network import DataManager
from pathfinding import PathfindingConfig, ShortestPath
from report import build_route, make_report


def parse_input(text):
    text = text.replace("；", ";")
    parts = [p.strip() for p in text.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts


def run_query(dm, start, end, args):
    net = dm.network
    if not net.has_station(start):
        return "Starting station '%s' does not exist, please check the station name" % start
    if not net.has_station(end):
        return "Ending station '%s' does not exist, please check the station name" % end
    if start == end:
        return "Starting station cannot be the same as the ending station"
    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    cfg.preferred_lines = [args.line_preference] if args.line_preference else []
    try:
        s, t = net.station_to_number[start], net.station_to_number[end]
        sp = ShortestPath(net.graph, s, cfg)
        route = build_route(net, sp, t)
    except Exception as e:
        return "Path calculation failed: %s" % (
            "no route found (check the transfer limit)" if str(e) == "no path" else e)
    try:
        fare = Sum_money(route.totalDistance)
    except Exception as e:
        return "Fare calculation failed: %s" % e
    return make_report(route, fare, start, end, args.mode, args.format)


def emit(msg, args):
    print(msg)
    if args.output_file:
        try:
            with open(args.output_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError as e:
            print("Cannot write output file: %s" % e)


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        issues = dm.check_data()
        if issues:
            print("Data check found %d issue(s):" % len(issues))
            for i in issues:
                print(" - " + i)
            return 1
        print("Data check passed: %d stations, %d connections" % (
            len(dm.data["stations"]), len(dm.data["connections"])))
        return 0
    print("Beijing Subway fare query. Input 'Starting Station; Ending Station' (q to quit)")
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
        parts = parse_input(line)
        if parts is None:
            print("Input format incorrect, please use 'Starting Station; Ending Station' format")
            continue
        emit(run_query(dm, parts[0], parts[1], args), args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
