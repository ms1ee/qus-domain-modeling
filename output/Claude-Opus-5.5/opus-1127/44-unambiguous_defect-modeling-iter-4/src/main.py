"""
Command-line interface of the Beijing Subway fare calculation system.

Usage::

    python main.py [--mode MODE] [--format text|json] [--output_file PATH]
                   [--max_transfers N] [--line_preference "Line 1"]
                   [--check_data] [--data_file PATH]

Enter queries as ``Starting Station; Ending Station`` (``,`` / ``->`` also
accepted).  Type ``quit`` to exit, ``help`` for help, ``lines`` to list lines.
"""

import argparse
import json
import re
import sys

from data_loader import DATA_FILE_PATH, DataLoadError
from data_manager import SubwayNetwork, check_data_integrity
from fare_calculator import FareCalculationError
from pathfinding import PathfindingConfig, VALID_MODES
from report import build_route_result, format_result

FORMAT_ERROR = ("Input format incorrect, please use "
                "'Starting Station; Ending Station' format")
SEPARATOR_RE = re.compile(r"\s*(?:;|；|,|，|->|→|\t)\s*")
EXIT_COMMANDS = {"quit", "exit", "q"}
HELP_TEXT = ("Enter 'Starting Station; Ending Station' to query a route and fare.\n"
             "Commands: 'lines' (list lines), 'help', 'quit'.")


class QueryError(Exception):
    """User-facing query error."""


def parse_query(text):
    """Split an input line into (start, end); raise QueryError on bad format."""
    if text is None:
        raise QueryError(FORMAT_ERROR)
    parts = SEPARATOR_RE.split(text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise QueryError(FORMAT_ERROR)
    return parts[0].strip(), parts[1].strip()


def process_query(network, text, config):
    """Validate and run a query; return the result dict or raise QueryError."""
    start_raw, end_raw = parse_query(text)
    start = network.find_station(start_raw)
    if start is None:
        msg = f"Starting station '{start_raw}' does not exist, please check the station name"
        sugg = network.suggest_stations(start_raw)
        if sugg:
            msg += f" (did you mean: {', '.join(sugg)}?)"
        raise QueryError(msg)
    end = network.find_station(end_raw)
    if end is None:
        msg = f"Ending station '{end_raw}' does not exist, please check the station name"
        sugg = network.suggest_stations(end_raw)
        if sugg:
            msg += f" (did you mean: {', '.join(sugg)}?)"
        raise QueryError(msg)
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    try:
        _, names, edges = network.shortest_path(start, end, config)
    except Exception as exc:  # path calculation exception
        raise QueryError(f"Path calculation error: {exc}")
    if not edges:
        extra = ""
        if config.max_transfers is not None:
            extra = f" with at most {config.max_transfers} transfer(s)"
        raise QueryError(f"No route found from '{start}' to '{end}'{extra}")
    try:
        return build_route_result(start, end, names, edges, config.mode, config)
    except FareCalculationError as exc:
        raise QueryError(f"Fare calculation error: {exc}")


def write_output(path, results, fmt):
    """Export results to file (single result as object, several as list)."""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            if fmt == "json":
                payload = results[0] if len(results) == 1 else results
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            else:
                fh.write("\n\n".join(format_result(r, "text") for r in results))
                fh.write("\n")
    except OSError as exc:
        print(f"Error: cannot write output file '{path}': {exc}")


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", help="export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text",
                   help="output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="path query mode")
    p.add_argument("--max_transfers", type=int, default=None,
                   help="maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="preferred line(s), e.g. 'Line 1' (comma separated)")
    p.add_argument("--check_data", action="store_true",
                   help="run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p


def resolve_preferences(network, pref):
    if not pref:
        return []
    resolved = []
    candidates = [pref] if network.find_line(pref) else re.split(r"[,，;；]", pref)
    for item in candidates:
        item = item.strip()
        if not item:
            continue
        line = network.find_line(item)
        if line is None:
            print(f"Warning: line '{item}' not found, preference ignored")
        elif line not in resolved:
            resolved.append(line)
    return resolved


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers cannot be negative")
        return 2

    try:
        network = SubwayNetwork(data_source_file=args.data_file)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 2

    if args.check_data:
        check = check_data_integrity(network)
        print(check.report())
        return 0 if check.is_valid else 1

    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=resolve_preferences(network,
                                                                   args.line_preference))
    interactive = sys.stdin.isatty()
    if interactive:
        print("Beijing Subway Fare Calculation System")
        print(HELP_TEXT)

    results = []
    while True:
        try:
            line = input("Enter 'Starting Station; Ending Station': " if interactive else "")
        except (EOFError, KeyboardInterrupt):
            if interactive:
                print()
            break
        text = line.strip()
        if not text:
            continue
        cmd = text.lower()
        if cmd in EXIT_COMMANDS:
            break
        if cmd == "help":
            print(HELP_TEXT)
            continue
        if cmd == "lines":
            print("\n".join(network.get_line_names()))
            continue
        try:
            result = process_query(network, text, config)
        except QueryError as exc:
            print(exc)
            continue
        except Exception as exc:  # last-resort safety net
            print(f"Unexpected error: {exc}")
            continue
        print(format_result(result, args.format))
        results.append(result)
        if args.output_file:
            write_output(args.output_file, results, args.format)
    if interactive:
        print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
