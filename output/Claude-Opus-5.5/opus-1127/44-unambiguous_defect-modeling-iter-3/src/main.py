"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples::

    python src/main.py
    python src/main.py --mode least_transfer --format json --output_file out.json
    python src/main.py --check_data

Enter queries as ``Starting Station; Ending Station`` (``,`` or ``->`` are
also accepted as separators).  Type ``quit`` to exit.
"""

import argparse
import re
import sys

from data_loader import DataLoadError
from data_manager import SubwayNetwork, check_data_integrity
from fare_calculator import FareCalculationError
from pathfinding import VALID_MODES, PathfindingConfig
from report import format_json, format_text
from route_service import PathCalculationError, RouteNotFoundError, find_route

FORMAT_ERROR_MSG = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SAME_STATION_MSG = "Starting station cannot be the same as the ending station"
QUIT_COMMANDS = {"q", "quit", "exit", "退出"}
_SEPARATOR = re.compile(r"\s*(?:;|；|,|，|->|→)\s*")


class QueryError(Exception):
    """Invalid user query (format, station or logic)."""


def parse_query(text):
    """Split 'A; B' into ('A', 'B'); raise QueryError on bad format."""
    if not isinstance(text, str):
        raise QueryError(FORMAT_ERROR_MSG)
    parts = [p.strip() for p in _SEPARATOR.split(text.strip())]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise QueryError(FORMAT_ERROR_MSG)
    return parts[0], parts[1]


def validate_query(network, start_raw, end_raw):
    """Return official (start, end) names or raise QueryError."""
    start = network.resolve_station(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = network.resolve_station(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError(SAME_STATION_MSG)
    return start, end


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=None, help=argparse.SUPPRESS)
    p.add_argument("--query", default=None, help="Run a single query 'Start; End' and exit")
    return p


def _write_output(path, results, fmt, err):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            if fmt == "json":
                fh.write(format_json(results) + "\n")
            else:
                fh.write("\n\n".join(format_text(r) for r in results) + "\n")
        return True
    except OSError as exc:
        print(f"Failed to write output file '{path}': {exc}", file=err)
        return False


def process_query(network, text, config):
    """Handle one query line; returns a RouteResult or raises an error with message."""
    start_raw, end_raw = parse_query(text)
    start, end = validate_query(network, start_raw, end_raw)
    return find_route(network, start, end, config)


def main(argv=None, stdin=None, stdout=None, stderr=None):
    stdin = stdin or sys.stdin
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be a non-negative integer", file=out)
        return 2

    try:
        network = SubwayNetwork(data_file=args.data_file)
    except (DataLoadError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=out)
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        print(report.format_report(), file=out)
        return 0 if report.is_valid else 1

    preferred = []
    if args.line_preference:
        for raw in args.line_preference.split(","):
            raw = raw.strip()
            if not raw:
                continue
            line = network.resolve_line(raw)
            if line is None:
                print(f"Warning: line '{raw}' does not exist, preference ignored", file=err)
            else:
                preferred.append(line)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    results = []
    interactive = hasattr(stdin, "isatty") and stdin.isatty()

    def handle(text):
        try:
            route = process_query(network, text, config)
        except QueryError as exc:
            print(str(exc), file=out)
            return
        except RouteNotFoundError as exc:
            print(str(exc), file=out)
            return
        except PathCalculationError as exc:
            print(f"Path calculation error: {exc}", file=out)
            return
        except FareCalculationError as exc:
            print(f"Fare calculation error: {exc}", file=out)
            return
        except Exception as exc:  # defensive: never crash the query loop
            print(f"Unexpected error: {exc}", file=out)
            return
        results.append(route)
        print(format_json(route) if args.format == "json" else format_text(route), file=out)
        if args.output_file:
            if _write_output(args.output_file, results, args.format, err):
                print(f"Results saved to {args.output_file}", file=err)

    if args.query is not None:
        handle(args.query)
        return 0

    if interactive:
        print("Beijing Subway Fare Calculation System", file=out)
        print("Enter 'Starting Station; Ending Station' to query, 'quit' to exit.", file=out)
    while True:
        if interactive:
            print("> ", end="", file=out, flush=True)
        line = stdin.readline()
        if not line:
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in QUIT_COMMANDS:
            break
        if text.lower() in {"help", "h", "?"}:
            print("Enter 'Starting Station; Ending Station', e.g. 'Xidan; Guomao'. "
                  "Type 'quit' to exit.", file=out)
            continue
        handle(text)
        out.flush() if hasattr(out, "flush") else None
    if interactive:
        print("Goodbye!", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
