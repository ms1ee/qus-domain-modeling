"""CLI entry point for the Beijing Subway fare system."""
import argparse
import re
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, MODES
from report import compute_route, format_json, format_text

SEP = re.compile(r"[;；,，]")


def parse_query(text, dm):
    """Return (start, end) or raise ValueError with a message."""
    parts = [p.strip() for p in SEP.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    a, b = parts
    if a not in dm.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
    if b not in dm.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")
    return a, b


def run_query(dm, a, b, config, fmt):
    try:
        r = compute_route(dm, a, b, config)
    except RuntimeError as ex:
        return None, "Path calculation error: %s" % ex
    except Exception as ex:
        return None, "Path calculation error: %s" % ex
    return r, (format_json(r) if fmt == "json" else format_text(r))


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        dm = DataManager()
    except Exception as ex:
        print("Failed to load data: %s" % ex)
        return 1
    if args.check_data:
        ok, msgs = dm.check_data()
        print("\n".join(msgs))
        return 0 if ok else 1

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [x.strip() for x in SEP.split(args.line_preference) if x.strip()]

    if args.output_file:
        open(args.output_file, "w", encoding="utf-8").close()
    print("Enter 'Starting Station; Ending Station' (or 'q' to quit):")
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
        try:
            a, b = parse_query(line, dm)
        except ValueError as ex:
            print(ex)
            continue
        r, text = run_query(dm, a, b, config, args.format)
        print(text)
        if r is not None and args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
