"""CLI entry point."""
import argparse
import re
import sys

from subway_system import SubwaySystem
from pathfinding import PathfindingConfig
from report import build_report, format_json, format_text

SEP = re.compile(r"[;；,，、]")


def parse_query(line, system):
    """Return (start, end) or raise ValueError with message."""
    parts = [p.strip() for p in SEP.split(line)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    a, b = parts
    if a not in system.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
    if b not in system.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")
    return a, b


def run_query(system, a, b, config, fmt):
    try:
        route = system.find_route(a, b, config)
    except Exception as e:
        raise RuntimeError("Path calculation failed: %s" % e)
    if route is None:
        raise RuntimeError("No route found between '%s' and '%s' (check transfer limit)" % (a, b))
    try:
        rep = build_report(system, a, b, route)
    except Exception as e:
        raise RuntimeError("Fare calculation failed: %s" % e)
    return format_json(rep) if fmt == "json" else format_text(rep)


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
        system = SubwaySystem()
    except Exception as e:
        print("Failed to load data: %s" % e)
        return 1

    if args.check_data:
        problems = system.check_data()
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for x in problems:
                print(" -", x)
            return 1
        print("Data check passed: %d stations, %d lines." % (
            len(system.station_to_number), len(system.lines())))
        return 0

    cfg = PathfindingConfig()
    cfg.mode = args.mode
    cfg.max_transfers = args.max_transfers
    if args.line_preference:
        cfg.preferred_lines = [x.strip() for x in args.line_preference.split(",") if x.strip()]

    outputs = []
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit).")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        try:
            a, b = parse_query(line, system)
            out = run_query(system, a, b, cfg, args.format)
        except (ValueError, RuntimeError) as e:
            print(e)
            continue
        print(out)
        outputs.append(out)

    if args.output_file and outputs:
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(outputs) + "\n")
            print("Results written to %s" % args.output_file)
        except OSError as e:
            print("Cannot write output file: %s" % e)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
