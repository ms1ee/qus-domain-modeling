"""Command-line interface of the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--output_file FILE]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]

Enter queries as "Starting Station; Ending Station". Type 'quit' or 'exit'
(or send EOF) to leave.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, DataLoadError, load_subway_data  # noqa: E402
from data_manager import SubwayDataManager  # noqa: E402
from fare_calculator import FareCalculationError  # noqa: E402
from pathfinding import PathfindingConfig, VALID_MODES  # noqa: E402
from route_service import (PathNotFoundError, StationNotFoundError,  # noqa: E402
                           SubwaySystem)
from visualization import format_result  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = {"quit", "exit", "q"}


class QueryInputError(ValueError):
    pass


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true",
                   help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be a non-negative integer")
    return args


def parse_query(line):
    """Parse 'Start; End' (ASCII or full-width semicolon)."""
    if line is None:
        raise QueryInputError(FORMAT_ERROR)
    text = line.strip().replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryInputError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryInputError(FORMAT_ERROR)
    return start, end


def _write_output(path, fmt, results, text_block):
    try:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(text_block + "\n")
        return True
    except OSError as exc:
        print(f"Error: cannot write output file '{path}': {exc}")
        return False


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except DataLoadError as exc:
        print(f"Error: {exc}")
        return 1

    if args.check_data:
        mgr = SubwayDataManager(data)
        report = mgr.check_integrity()
        print(mgr.format_report(report))
        return 0 if report["ok"] else 1

    system = SubwaySystem(data=data)
    preferred = []
    if args.line_preference:
        preferred = [s.strip() for s in args.line_preference.replace("，", ",").split(",")
                     if s.strip()]
        known = set(system.all_lines())
        for line in preferred:
            if line not in known:
                print(f"Warning: preferred line '{line}' not found in data")
    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=preferred)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if args.output_file and args.format == "text":
        try:
            open(args.output_file, "w", encoding="utf-8").close()
        except OSError as exc:
            print(f"Error: cannot write output file '{args.output_file}': {exc}")
            return 1

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' (type 'quit' to exit)")
    results = []
    while True:
        try:
            line = input("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in EXIT_WORDS:
            break
        if not line.strip():
            print(FORMAT_ERROR)
            continue
        try:
            start, end = parse_query(line)
            result = system.query(start, end, config)
        except QueryInputError as exc:
            print(exc)
            continue
        except StationNotFoundError as exc:
            print(exc)
            continue
        except FareCalculationError as exc:
            print(f"Fare calculation error: {exc}")
            continue
        except PathNotFoundError as exc:
            print(f"Path calculation error: {exc}")
            continue
        except ValueError as exc:
            print(exc)
            continue
        except Exception as exc:  # unexpected path calculation failure
            print(f"Path calculation error: {exc}")
            continue

        block = format_result(result, args.format)
        print(block)
        results.append(result)
        if args.output_file:
            if _write_output(args.output_file, args.format, results, block):
                print(f"Result exported to {args.output_file}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
