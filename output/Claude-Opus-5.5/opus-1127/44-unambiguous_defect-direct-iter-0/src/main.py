"""Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--mode MODE] [--format text|json] [--output_file PATH]
                   [--max_transfers N] [--line_preference "Line 1"]
                   [--check_data] [--query "Start; End"]

Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from data_manager import SubwayNetwork, format_integrity_report  # noqa: E402
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath  # noqa: E402
from visualization import FareCalculationError, build_route_result, format_json, format_text  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_RE = re.compile(r"\s*(?:;|；|,|，|->|→)\s*")
QUIT_COMMANDS = {"q", "quit", "exit"}


class QueryError(Exception):
    pass


def parse_query(text):
    """Split 'Start; End' into (start, end); raises QueryError on bad format."""
    if not isinstance(text, str):
        raise QueryError(FORMAT_ERROR)
    parts = SEPARATOR_RE.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryError(FORMAT_ERROR)
    return parts[0].strip(), parts[1].strip()


def process_query(network, text, config):
    """Validate input, compute route and return the result dict.

    Raises QueryError with a user-friendly message on any failure.
    """
    start_raw, end_raw = parse_query(text)
    start = network.resolve_station(start_raw)
    if start is None:
        raise QueryError("Starting station '%s' does not exist, please check the station name" % start_raw)
    end = network.resolve_station(end_raw)
    if end is None:
        raise QueryError("Ending station '%s' does not exist, please check the station name" % end_raw)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(network.graph, network.station_number(start), config)
    except Exception as exc:  # path calculation failure
        raise QueryError("Path calculation error: %s" % exc)
    try:
        result = build_route_result(network, sp, start, end, config)
    except FareCalculationError as exc:
        raise QueryError("Fare calculation error: %s" % exc)
    except Exception as exc:
        raise QueryError("Path calculation error: %s" % exc)
    if result is None:
        msg = "No route found from '%s' to '%s'" % (start, end)
        if config.max_transfers is not None:
            msg += " within %d transfer(s)" % config.max_transfers
        raise QueryError(msg)
    return result


def _non_negative_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    if n < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return n


def build_parser():
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", help="Export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated (e.g. 'Line 1')")
    parser.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help="Path of subway data JSON file")
    parser.add_argument("--query", default=None, help="Run a single query 'Start; End' and exit")
    return parser


def _resolve_preferences(network, raw):
    preferred = []
    if not raw:
        return preferred
    for item in re.split(r"[,，;；]", raw):
        item = item.strip()
        if not item:
            continue
        resolved = network.resolve_line(item)
        if resolved is None:
            print("Warning: line '%s' not found in network data, preference ignored" % item)
        elif resolved not in preferred:
            preferred.append(resolved)
    return preferred


class OutputWriter:
    def __init__(self, path, fmt):
        self.path = path
        self.fmt = fmt
        self.results = []

    def render(self, result):
        return format_json(result) if self.fmt == "json" else format_text(result)

    def add(self, result):
        self.results.append(result)
        if not self.path:
            return
        if self.fmt == "json":
            content = format_json(self.results[0] if len(self.results) == 1 else self.results)
        else:
            content = "\n\n".join(format_text(r) for r in self.results)
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(content + "\n")
        except OSError as exc:
            print("Error: cannot write output file '%s': %s" % (self.path, exc))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data(args.data_file)
        network = SubwayNetwork(data)
    except (OSError, ValueError) as exc:
        print("Error: failed to load subway data: %s" % exc)
        return 1

    if args.check_data:
        report = network.check_integrity()
        print(format_integrity_report(report))
        return 0 if report["valid"] else 1

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=_resolve_preferences(network, args.line_preference))
    except ValueError as exc:
        print("Error: %s" % exc)
        return 1

    writer = OutputWriter(args.output_file, args.format)

    def handle(text):
        try:
            result = process_query(network, text, config)
        except QueryError as exc:
            print("Error: %s" % exc)
            return False
        print(writer.render(result))
        writer.add(result)
        if args.output_file:
            print("Result exported to %s" % args.output_file)
        return True

    if args.query is not None:
        return 0 if handle(args.query) else 1

    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' to query, 'quit' to exit.")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in QUIT_COMMANDS:
            break
        if text.lower() in ("help", "h", "?"):
            print("Format: Starting Station; Ending Station  (separators: ; , ->)")
            continue
        handle(text)
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
