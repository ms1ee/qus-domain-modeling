"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python main.py [--output_file FILE] [--format text|json]
                   [--mode shortest_distance|least_transfer|comprehensive]
                   [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as "Starting Station; Ending Station". Type "quit" to exit.
"""

import argparse
import json
import sys

from network import SubwayNetwork
from pathfinding import PathfindingConfig, VALID_MODES
from report import build_route_result, format_text, format_json

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"quit", "exit", "q"}


class InputError(Exception):
    """Raised for invalid user input."""


def _non_negative_int(value):
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    if v < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return v


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=_non_negative_int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated (e.g. 'Line 1')")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    return p


def parse_query(raw):
    """Split raw input into (start, end). Raises InputError."""
    if raw is None:
        raise InputError(FORMAT_ERROR)
    text = raw.strip().replace("；", ";")
    if text.count(";") != 1:
        raise InputError(FORMAT_ERROR)
    start, end = (part.strip() for part in text.split(";"))
    if not start or not end:
        raise InputError(FORMAT_ERROR)
    return start, end


def validate_query(network, raw):
    """Return official (start, end) station names. Raises InputError."""
    start, end = parse_query(raw)
    s = network.resolve_station(start)
    if s is None:
        raise InputError(f"Starting station '{start}' does not exist, please check the station name")
    e = network.resolve_station(end)
    if e is None:
        raise InputError(f"Ending station '{end}' does not exist, please check the station name")
    if s == e:
        raise InputError("Starting station cannot be the same as the ending station")
    return s, e


def process_query(network, raw, config, fmt="text"):
    """Process one query. Returns (result dict, rendered string)."""
    start, end = validate_query(network, raw)
    try:
        sp, target = network.find_route(start, end, config)
    except Exception as exc:
        raise InputError(f"Path calculation error: {exc}")
    if not sp.has_path_to(target):
        extra = ""
        if config.max_transfers is not None:
            extra = f" with at most {config.max_transfers} transfer(s)"
        raise InputError(f"No route found from '{start}' to '{end}'{extra}")
    try:
        result = build_route_result(network, sp, target, config)
    except ValueError as exc:
        raise InputError(f"Fare calculation error: {exc}")
    if result is None:
        raise InputError(f"No route found from '{start}' to '{end}'")
    rendered = format_json(result) if fmt == "json" else format_text(result)
    return result, rendered


def _write_output(path, fmt, results, texts):
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            json.dump(results, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(texts) + "\n")


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        network = SubwayNetwork()
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        check = network.check_integrity()
        print(check.summary())
        return 0 if check.is_valid else 1

    preferred = []
    if args.line_preference:
        for item in args.line_preference.replace("，", ",").split(","):
            item = item.strip()
            if not item:
                continue
            resolved = network.resolve_line(item)
            if resolved is None:
                print(f"Warning: line '{item}' not found in data, preference ignored")
            else:
                preferred.append(resolved)
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")
    results, texts = [], []
    while True:
        try:
            raw = input("\nQuery> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw.strip().lower() in EXIT_WORDS:
            break
        if not raw.strip():
            print(FORMAT_ERROR)
            continue
        try:
            result, rendered = process_query(network, raw, config, args.format)
        except InputError as exc:
            print(exc)
            continue
        except Exception as exc:  # last-resort safety net
            print(f"Unexpected error: {exc}")
            continue
        print(rendered)
        if args.output_file:
            results.append(result)
            texts.append(format_text(result) if args.format == "text" else rendered)
            try:
                _write_output(args.output_file, args.format, results, texts)
                print(f"Result saved to {args.output_file}")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
