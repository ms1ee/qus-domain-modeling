"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --format json --output_file out.json
    python src/main.py --check_data
"""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError
from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig, VALID_MODES
from report import build_route_result, format_result, format_text, RouteError, FareError

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
QUIT_WORDS = {"q", "quit", "exit", "退出"}
SEPARATOR_RE = re.compile(r"[;；,，]")


class QueryError(Exception):
    """Validation error for a user query."""


def parse_query(text):
    """Split 'Start; End' into two stripped names, raising QueryError."""
    if text is None:
        raise QueryError(FORMAT_ERROR)
    parts = SEPARATOR_RE.split(text.strip())
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def validate_query(network, text):
    start_raw, end_raw = parse_query(text)
    start = network.resolve_station(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = network.resolve_station(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return start, end


def process_query(network, text, config):
    """Validate and compute a query. Returns (result dict or None, error message or None)."""
    try:
        start, end = validate_query(network, text)
        return build_route_result(network, start, end, config), None
    except QueryError as exc:
        return None, str(exc)
    except RouteError as exc:
        return None, f"Path calculation error: {exc}"
    except FareError as exc:
        return None, f"Fare calculation error: {exc}"
    except Exception as exc:  # pragma: no cover - last-resort protection
        return None, f"Unexpected error: {exc}"


def write_output(path, results, fmt):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(format_text(r) for r in results))
        fh.write("\n")


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", action="append", default=None,
                   help="Preferred line (e.g. 'Line 1'); may be repeated or comma separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help="Path of subway_data.json")
    p.add_argument("--query", help="Run a single query 'Start; End' and exit")
    return p


def run_check(network):
    report = network.check_integrity()
    stats = report["stats"]
    print("Data integrity check")
    print(f"  Stations: {stats['stations']}, Connections: {stats['connections']}, "
          f"Lines: {stats['lines']}, Transfer stations: {stats['transfer_stations']}")
    for e in report["errors"]:
        print(f"  ERROR: {e}")
    for w in report["warnings"]:
        print(f"  WARNING: {w}")
    print("Result: " + ("PASSED" if report["ok"] else "FAILED"))
    return 0 if report["ok"] else 1


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    try:
        network = SubwayNetwork(path=args.data_file)
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        return run_check(network)

    preferred = []
    for item in args.line_preference or []:
        for part in re.split(r"[,，]", item):
            part = part.strip()
            if not part:
                continue
            resolved = network.resolve_line(part)
            if resolved is None:
                print(f"Warning: line preference '{part}' not found in data", file=sys.stderr)
                preferred.append(part)
            else:
                preferred.append(resolved)

    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)
    results = []

    def handle(text):
        result, error = process_query(network, text, config)
        if error:
            print(error)
            return False
        print(format_result(result, args.format))
        results.append(result)
        if args.output_file:
            try:
                write_output(args.output_file, results, args.format)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
        return True

    if args.query:
        return 0 if handle(args.query) else 1

    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in QUIT_WORDS:
            break
        handle(line)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
