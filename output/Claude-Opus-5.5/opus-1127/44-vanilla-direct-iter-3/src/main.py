"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples::

    python src/main.py
    python src/main.py --mode least_transfer --format json --output_file out.json
    python src/main.py --max_transfers 1 --line_preference "Line 1"
    python src/main.py --check_data
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, build_graph, load_subway_data  # noqa: E402
from data_manager import SubwayDataManager  # noqa: E402
from pathfinding import MODES, PathfindingConfig  # noqa: E402
from report import format_json, format_text  # noqa: E402
from subway_system import (  # noqa: E402
    FareCalculationError, InputValidationError, PathCalculationError, SubwayFareSystem,
)

PROMPT = "Please enter 'Starting Station; Ending Station' (or 'quit' to exit): "


def non_negative_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    if n < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return n


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="output format")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance", help="path query mode")
    p.add_argument("--max_transfers", type=non_negative_int, default=None, help="maximum transfers")
    p.add_argument("--line_preference", default=None,
                   help="preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true", help="run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p.parse_args(argv)


class ResultWriter:
    def __init__(self, path, fmt):
        self.path = path
        self.fmt = fmt
        self.results = []
        if path:
            # start with a fresh file
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("[]\n" if fmt == "json" else "")

    def write(self, info, text):
        if not self.path:
            return
        if self.fmt == "json":
            self.results.append(info)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.results, fh, ensure_ascii=False, indent=2)
        else:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(text + "\n\n")


def run_check(path):
    try:
        manager = SubwayDataManager(path=path)
    except (OSError, ValueError) as exc:
        print("Failed to load subway data: %s" % exc)
        return 1
    report = manager.check_integrity()
    print(report.format())
    return 0 if report.ok else 1


def main(argv=None):
    args = parse_args(argv)
    if args.check_data:
        return run_check(args.data_file)

    try:
        graph = build_graph(load_subway_data(args.data_file))
    except (OSError, ValueError) as exc:
        print("Failed to load subway data: %s" % exc)
        return 1

    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers)
    system = SubwayFareSystem(graph, config)
    if args.line_preference:
        wanted = [x.strip() for x in args.line_preference.replace("，", ",").split(",") if x.strip()]
        resolved, unknown = system.resolve_lines(wanted)
        for u in unknown:
            print("Warning: line '%s' does not exist and will be ignored" % u)
        config.preferred_lines = resolved

    try:
        writer = ResultWriter(args.output_file, args.format)
    except OSError as exc:
        print("Cannot open output file: %s" % exc)
        return 1

    print("Beijing Subway Fare Calculation System (%d stations loaded)" % len(graph.station_to_number))
    while True:
        try:
            raw = input(PROMPT)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        try:
            info = system.query(text)
        except InputValidationError as exc:
            print(exc)
            continue
        except PathCalculationError as exc:
            print("Path calculation error: %s" % exc)
            continue
        except FareCalculationError as exc:
            print("Fare calculation error: %s" % exc)
            continue
        except Exception as exc:  # last-resort safety net
            print("Unexpected error: %s" % exc)
            continue
        output = format_json(info) if args.format == "json" else format_text(info)
        print(output)
        try:
            writer.write(info, output)
        except OSError as exc:
            print("Failed to write output file: %s" % exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
