"""Command line interface for the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--output_file FILE]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1,Line 2"]
                       [--check_data]

Enter queries as "Starting Station; Ending Station".  Type 'quit' to exit.
"""

import argparse
import json
import sys

from data_loader import DATA_FILE_PATH
from data_manager import SubwayDataManager
from pathfinding import PathfindingConfig, ShortestPath, VALID_MODES
from report import build_route_info, format_json_report, format_text_report, to_json_dict

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance",
                   help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true", help="Check data integrity and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


def parse_query(text):
    """Return (start, end) or raise ValueError with a user-facing message."""
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR)
    return start, end


def resolve_stations(manager, start, end):
    s = manager.find_station(start)
    if s is None:
        msg = f"Starting station '{start}' does not exist, please check the station name"
        sug = manager.suggest(start)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        raise ValueError(msg)
    e = manager.find_station(end)
    if e is None:
        msg = f"Ending station '{end}' does not exist, please check the station name"
        sug = manager.suggest(end)
        if sug:
            msg += f" (did you mean: {', '.join(sug)}?)"
        raise ValueError(msg)
    if s == e:
        raise ValueError("Starting station cannot be the same as the ending station")
    return s, e


def process_query(manager, config, text):
    start, end = parse_query(text)
    start, end = resolve_stations(manager, start, end)
    try:
        sp = ShortestPath(manager.graph, manager.station_to_number[start], config)
    except Exception as exc:
        raise RuntimeError(f"Path calculation error: {exc}") from exc
    return build_route_info(manager, sp, start, end, config)


def run_check(manager):
    report = manager.check_integrity()
    st = report["stats"]
    print("Data integrity check")
    print(f"  Stations: {st['stations']}, Connections: {st['connections']}, "
          f"Lines: {st['lines']}, Transfer stations: {st['transfer_stations']}, "
          f"Components: {st['components']}")
    for e in report["errors"]:
        print(f"  ERROR: {e}")
    for w in report["warnings"]:
        print(f"  WARNING: {w}")
    print("Result: " + ("PASSED" if report["ok"] else "FAILED"))
    return 0 if report["ok"] else 1


def write_output(path, fmt, results):
    with open(path, "w", encoding="utf-8") as f:
        if fmt == "json":
            data = [to_json_dict(r) for r in results]
            json.dump(data[0] if len(data) == 1 else data, f, ensure_ascii=False, indent=2)
        else:
            f.write("\n\n".join(format_text_report(r) for r in results) + "\n")


def main(argv=None):
    args = parse_args(argv)
    try:
        manager = SubwayDataManager(path=args.data_file)
    except Exception as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1
    if args.check_data:
        return run_check(manager)

    preferred = []
    if args.line_preference:
        preferred = [l.strip() for l in args.line_preference.split(",") if l.strip()]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                               preferred_lines=preferred)

    print("Beijing Subway Fare Calculator")
    print("Enter 'Starting Station; Ending Station' (type 'quit' to exit).")
    results = []
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        try:
            info = process_query(manager, config, line)
        except ValueError as exc:
            print(str(exc))
            continue
        except RuntimeError as exc:
            print(str(exc))
            continue
        except Exception as exc:
            print(f"Unexpected error: {exc}")
            continue
        if args.format == "json":
            print(format_json_report(info))
        else:
            print(format_text_report(info))
        results.append(info)
        if args.output_file:
            try:
                write_output(args.output_file, args.format, results)
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
