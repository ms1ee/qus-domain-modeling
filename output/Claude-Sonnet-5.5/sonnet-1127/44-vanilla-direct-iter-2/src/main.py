"""CLI entry point for the Beijing Subway fare calculator."""
import argparse
import sys

from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig
from report import query_route, format_text, format_json

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(line, network):
    """Return (start, end) or raise ValueError with a message."""
    norm = line.replace("；", ";")
    parts = [p.strip() for p in norm.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERR)
    a, b = parts
    if a not in network.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
    if b not in network.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")
    return a, b


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
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
        network = SubwayNetwork()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        res = network.check_integrity()
        print("Stations: %d, Lines: %d, Connections: %d" % (res["stations"], res["lines"], res["connections"]))
        for i in res["issues"]:
            print("  - " + i)
        print("Data check %s" % ("passed" if res["ok"] else "found issues"))
        return 0 if res["ok"] else 1

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [x.strip() for x in args.line_preference.split(",") if x.strip()]

    print("Enter 'Starting Station; Ending Station' (type 'exit' to quit)")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        try:
            a, b = parse_input(line, network)
        except ValueError as e:
            print(e)
            continue
        try:
            r = query_route(network, a, b, config)
        except ArithmeticError as e:
            print(e)
            continue
        except Exception as e:
            print("Path calculation error: %s" % e)
            continue
        text = format_json(r) if args.format == "json" else format_text(r)
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n")
            except OSError as e:
                print("Failed to write output file: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
