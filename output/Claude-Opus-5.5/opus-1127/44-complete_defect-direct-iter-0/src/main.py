"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--output_file PATH]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1,Line 2"]
                       [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' to exit.
"""

import argparse
import difflib
import json
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
from report import build_route_result, format_json, format_text

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"quit", "exit", "q"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES),
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


def parse_query(line):
    """Parse 'A; B' input. Returns (start, end) or raises ValueError."""
    text = line.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR)
    return start, end


def _suggest(network, name):
    matches = difflib.get_close_matches(name, list(network.station_to_number), n=3, cutoff=0.6)
    return f" (did you mean: {', '.join(matches)}?)" if matches else ""


def validate_query(network, start, end):
    """Validate station names. Returns (official_start, official_end)."""
    s = network.resolve_station(start)
    if s is None:
        raise ValueError(f"Starting station '{start}' does not exist, please check the station name"
                         + _suggest(network, start))
    e = network.resolve_station(end)
    if e is None:
        raise ValueError(f"Ending station '{end}' does not exist, please check the station name"
                         + _suggest(network, end))
    if s == e:
        raise ValueError("Starting station cannot be the same as the ending station")
    return s, e


def process_query(network, line, config):
    """Process one input line. Returns (result_dict or None, error message or None)."""
    try:
        start, end = parse_query(line)
        start, end = validate_query(network, start, end)
    except ValueError as exc:
        return None, str(exc)
    try:
        sp = ShortestPath(network.graph, network.station_to_number[start], config)
    except Exception as exc:  # path calculation exception handling
        return None, f"Path calculation error: {exc}"
    try:
        result = build_route_result(network, sp, start, end, config)
    except (ValueError, TypeError) as exc:  # fare calculation exception handling
        return None, f"Fare calculation error: {exc}"
    except Exception as exc:
        return None, f"Path calculation error: {exc}"
    if result is None:
        msg = f"No path found from '{start}' to '{end}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        return None, msg
    return result, None


class OutputWriter:
    def __init__(self, path, fmt):
        self.path = path
        self.fmt = fmt
        self.results = []
        if path:
            open(path, "w", encoding="utf-8").close()

    def write(self, result):
        if not self.path:
            return
        self.results.append(result)
        try:
            if self.fmt == "json":
                payload = self.results[0] if len(self.results) == 1 else self.results
                with open(self.path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
            else:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(format_text(result) + "\n\n")
        except OSError as exc:
            print(f"Failed to write output file: {exc}")


def main(argv=None):
    args = parse_args(argv)
    try:
        network = SubwayNetwork(path=args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = network.check_integrity()
        print(SubwayNetwork.format_integrity_report(report))
        return 0 if report["ok"] else 1

    preferred = []
    if args.line_preference:
        for raw in args.line_preference.replace("，", ",").split(","):
            raw = raw.strip()
            if not raw:
                continue
            resolved = network.resolve_line(raw)
            if resolved is None:
                print(f"Warning: line '{raw}' not found, preference ignored")
            elif resolved not in preferred:
                preferred.append(resolved)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)
    writer = OutputWriter(args.output_file, args.format)

    print("Beijing Subway Fare Calculation System")
    print(f"Loaded {len(network.station_to_number)} stations, {len(network.lines)} lines.")
    while True:
        try:
            line = input("\nPlease enter 'Starting Station; Ending Station' (or 'quit' to exit): ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in EXIT_WORDS:
            break
        result, error = process_query(network, line, config)
        if error:
            print(error)
            continue
        print(format_json(result) if args.format == "json" else format_text(result))
        writer.write(result)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
