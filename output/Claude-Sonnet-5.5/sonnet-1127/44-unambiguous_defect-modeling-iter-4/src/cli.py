"""Command-line interface."""
import argparse
import re
import sys

from data_manager import DataManager, DataIntegrityChecker
from pathfinding import PathfindingConfig, MODES
from report import build_route, summary, render

SEP = re.compile(r"[;；,，]")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


def parse_query(text, names):
    """Return (start, end) or raise ValueError with a user-facing message."""
    parts = [x.strip() for x in SEP.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    a, b = parts
    if a not in names:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
    if b not in names:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")
    return a, b


def run_query(dm, text, args, config):
    a, b = parse_query(text, dm.graph.station_to_number)
    try:
        route = build_route(dm.graph, a, b, config)
    except ValueError as e:
        raise ValueError("Path calculation failed: %s" % e)
    try:
        info = summary(route, {"start": a, "end": b, "mode": args.mode,
                               "max_transfers": args.max_transfers,
                               "line_preference": args.line_preference})
    except Exception as e:
        raise ValueError("Fare calculation failed: %s" % e)
    return render(info, args.format)


def write_output(path, content):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content + "\n")
    except OSError as e:
        print("Cannot write output file: %s" % e)


def main(argv=None):
    args = parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print("Failed to load subway data: %s" % e)
        return 1
    if args.check_data:
        ok, msgs = DataIntegrityChecker(dm).run()
        print("\n".join(msgs))
        return 0 if ok else 1
    config = PathfindingConfig(args.mode, args.max_transfers,
                               [args.line_preference] if args.line_preference else [])
    print("Enter 'Starting Station; Ending Station' (empty line or 'q' to quit):")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line or line.lower() in ("q", "quit", "exit"):
            break
        try:
            out = run_query(dm, line, args, config)
        except ValueError as e:
            print(e)
            continue
        except Exception as e:
            print("Unexpected error: %s" % e)
            continue
        print(out)
        if args.output_file:
            write_output(args.output_file, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
