"""Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--mode MODE] [--format text|json] [--output_file PATH]
                   [--max_transfers N] [--line_preference "Line 1,Line 2"]
                   [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'q' to quit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data
from data_manager import SubwayDataManager, format_integrity_report
from fare_calculator import FareCalculationError
from pathfinding import MODES, PathfindingConfig
from report import render, to_json_dict
from subway_network import PathNotFoundError, SubwayNetwork

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(MODES),
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true",
                   help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


def parse_query(line):
    """Split 'A; B' into (A, B); raise ValueError on bad format."""
    text = line.replace("；", ";").strip()
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR)
    return start, end


def process_query(network, line, config, fmt="text"):
    """Process one input line. Returns (success, output text, route or None)."""
    try:
        start_raw, end_raw = parse_query(line)
    except ValueError as exc:
        return False, str(exc), None
    start = network.resolve_station(start_raw)
    if start is None:
        return False, "Starting station '%s' does not exist, please check the station name" \
            % start_raw, None
    end = network.resolve_station(end_raw)
    if end is None:
        return False, "Ending station '%s' does not exist, please check the station name" \
            % end_raw, None
    if start == end:
        return False, "Starting station cannot be the same as the ending station", None
    try:
        route = network.query(start, end, config)
    except PathNotFoundError as exc:
        return False, "Path calculation error: %s" % exc, None
    except FareCalculationError as exc:
        return False, "Fare calculation error: %s" % exc, None
    except Exception as exc:  # pragma: no cover - defensive
        return False, "Path calculation error: %s" % exc, None
    try:
        output = render(route, fmt)
    except Exception as exc:  # pragma: no cover - defensive
        return False, "Fare calculation error: %s" % exc, None
    return True, output, route


class ResultWriter:
    """Exports query results to a file (text appended, JSON kept valid)."""

    def __init__(self, path, fmt):
        self.path = path
        self.fmt = fmt
        self.results = []
        self.initialized = False

    def write(self, route, text):
        if not self.path:
            return
        try:
            if self.fmt == "json":
                self.results.append(to_json_dict(route))
                payload = self.results[0] if len(self.results) == 1 else self.results
                with open(self.path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
            else:
                mode = "a" if self.initialized else "w"
                with open(self.path, mode, encoding="utf-8") as fh:
                    fh.write(text + "\n")
            self.initialized = True
        except OSError as exc:
            print("Failed to write output file: %s" % exc)


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except DataLoadError as exc:
        print("Error: %s" % exc)
        return 1

    if args.check_data:
        report = SubwayDataManager(data).check_integrity()
        print(format_integrity_report(report))
        return 0 if report["ok"] else 1

    network = SubwayNetwork(data)
    preferred = []
    if args.line_preference:
        preferred = [s.strip() for s in args.line_preference.replace("，", ",").split(",")
                     if s.strip()]
        unknown = [l for l in preferred if l not in network.all_lines()]
        if unknown:
            print("Warning: unknown line(s) in preference: %s" % ", ".join(unknown))
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)
    writer = ResultWriter(args.output_file, args.format)

    print("Beijing Subway Fare Calculator (%d stations loaded)" % len(network.station_to_number))
    print("Enter 'Starting Station; Ending Station' to query, 'q' to quit.")
    while True:
        try:
            print("> ", end="", flush=True)
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print()
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in QUIT_WORDS:
            break
        ok, output, route = process_query(network, line, config, args.format)
        print(output)
        if ok:
            writer.write(route, output)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
