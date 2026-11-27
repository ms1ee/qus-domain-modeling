"""Command-line interface of the Beijing Subway fare calculation system."""
import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, load_subway_data  # noqa: E402
from data_manager import SubwayDataManager  # noqa: E402
from pathfinding import PathfindingConfig, MODES  # noqa: E402
from report import format_text, format_json, to_json_dict  # noqa: E402
from subway_system import SubwaySystem, RouteError  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", action="append", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH)
    return p.parse_args(argv)


def parse_input(text):
    parts = [x.strip() for x in re.split(r"[;,；，]", text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def write_output(path, fmt, results):
    with open(path, "w", encoding="utf-8") as f:
        if fmt == "json":
            json.dump([to_json_dict(r) for r in results], f, ensure_ascii=False, indent=2)
        else:
            f.write("\n\n".join(format_text(r) for r in results) + "\n")


def run_check(path):
    data = load_subway_data(path)
    report = SubwayDataManager(data).check_integrity()
    print(f"Stations: {report['station_count']}, connections: {report['connection_count']}, "
          f"lines: {report['line_count']}")
    for e in report["errors"]:
        print("ERROR:", e)
    for w in report["warnings"]:
        print("WARNING:", w)
    print("Data integrity check passed" if report["ok"] else "Data integrity check failed")
    return 0 if report["ok"] else 1


def main(argv=None):
    args = parse_args(argv)
    if args.check_data:
        try:
            return run_check(args.data_file)
        except Exception as exc:
            print(f"Failed to check data: {exc}")
            return 1
    if args.max_transfers is not None and args.max_transfers < 0:
        print("--max_transfers must be non-negative")
        return 1
    try:
        system = SubwaySystem(args.data_file)
    except Exception as exc:
        print(f"Failed to load subway data: {exc}")
        return 1
    prefs = []
    for item in args.line_preference or []:
        prefs.extend(x.strip() for x in item.split(",") if x.strip())
    config = PathfindingConfig(args.mode, args.max_transfers, prefs)
    results = []
    print("Beijing Subway Fare Calculation System (type 'quit' to exit)")
    while True:
        try:
            line = input("Enter 'Starting Station; Ending Station': ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        try:
            raw_start, raw_end = parse_input(line)
        except ValueError as exc:
            print(exc)
            continue
        start = system.resolve_station(raw_start)
        if start is None:
            print(f"Starting station '{raw_start}' does not exist, please check the station name")
            continue
        end = system.resolve_station(raw_end)
        if end is None:
            print(f"Ending station '{raw_end}' does not exist, please check the station name")
            continue
        if start != raw_start:
            print(f"Note: '{raw_start}' matched to '{start}'")
        if end != raw_end:
            print(f"Note: '{raw_end}' matched to '{end}'")
        try:
            info = system.query(start, end, config)
        except RouteError as exc:
            print(exc)
            continue
        except Exception as exc:
            print(f"Unexpected error: {exc}")
            continue
        print(format_json(info) if args.format == "json" else format_text(info))
        results.append(info)
        if args.output_file:
            try:
                write_output(args.output_file, args.format, results)
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
