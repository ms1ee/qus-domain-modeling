"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python main.py
    python main.py --mode least_transfer --format json --output_file out.json
    python main.py --check_data
Then enter queries like:  Xidan; Guomao
"""

import argparse
import json
import re
import sys
import unicodedata

from data_loader import DATA_FILE_PATH, SubwayNetwork, load_subway_data
from data_manager import SubwayDataManager
from fare_calculator import Sum_money  # noqa: F401  (re-exported for convenience)
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_route_info, format_report

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_RE = re.compile(r"[;；,，]")


class QueryError(Exception):
    """User-facing query error."""


def _normalize(name):
    s = unicodedata.normalize("NFKC", name).strip().lower()
    s = " ".join(s.split())
    return s


def _strip_suffix(s):
    for suf in (" station", "站"):
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)].strip()
    return s


class StationResolver:
    """Standardize user-entered station names to official names."""

    def __init__(self, names):
        self.names = set(names)
        self.lookup = {}
        self.stripped = {}
        for n in names:
            self.lookup.setdefault(_normalize(n), n)
            self.lookup.setdefault(_normalize(n).replace(" ", ""), n)
            self.stripped.setdefault(_strip_suffix(_normalize(n)), n)

    def resolve(self, raw):
        if raw in self.names:
            return raw
        key = _normalize(raw)
        for candidate in (key, key.replace(" ", "")):
            if candidate in self.lookup:
                return self.lookup[candidate]
        stripped = _strip_suffix(key)
        if stripped in self.lookup:
            return self.lookup[stripped]
        if stripped in self.stripped:
            return self.stripped[stripped]
        return None


def parse_query(line):
    parts = SEPARATOR_RE.split(line)
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


def run_query(network, resolver, start_raw, end_raw, config):
    start = resolver.resolve(start_raw)
    if start is None:
        raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
    end = resolver.resolve(end_raw)
    if end is None:
        raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    s = network.station_to_number[start]
    t = network.station_to_number[end]
    try:
        sp = ShortestPath(network.graph, s, config)
        stations, edges = sp.path_with_edges(t)
    except Exception as exc:  # path calculation exception
        raise QueryError(f"Path calculation error: {exc}") from exc
    if not edges:
        msg = f"No path found from '{start}' to '{end}'"
        if config.max_transfers is not None:
            msg += f" within {config.max_transfers} transfer(s)"
        raise QueryError(msg)
    try:
        return build_route_info(start, end, stations, edges, network.number_to_station, config)
    except (ValueError, TypeError) as exc:
        raise QueryError(f"Fare calculation error: {exc}") from exc


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None,
                   help="Preferred line(s), comma separated, e.g. 'Line 1'")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be a non-negative integer")
    return args


def _write_output(path, fmt, results):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            if fmt == "json":
                payload = results[0] if len(results) == 1 else results
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            else:
                fh.write("\n\n".join(format_report(r, "text") for r in results))
                fh.write("\n")
        return True
    except OSError as exc:
        print(f"Failed to write output file '{path}': {exc}")
        return False


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error loading subway data: {exc}")
        return 1

    if args.check_data:
        mgr = SubwayDataManager(data=data, path=args.data_file)
        report = mgr.check_integrity()
        print(SubwayDataManager.format_integrity_report(report))
        return 0 if report["passed"] else 1

    network = SubwayNetwork(data)
    resolver = StationResolver(network.station_names())
    preferred = [s.strip() for s in args.line_preference.split(",")] if args.line_preference else []
    preferred = [s for s in preferred if s]
    config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred)

    print("Beijing Subway Fare Calculation System")
    print("Enter 'Starting Station; Ending Station' to query, 'quit' to exit.")
    results = []
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
        if line.lower() in ("quit", "exit", "q"):
            break
        if line.lower() in ("help", "h", "?"):
            print("Enter queries as 'Starting Station; Ending Station'. Type 'quit' to exit.")
            continue
        try:
            start_raw, end_raw = parse_query(line)
            info = run_query(network, resolver, start_raw, end_raw, config)
        except QueryError as exc:
            print(str(exc))
            continue
        except Exception as exc:  # last-resort safety net
            print(f"Unexpected error: {exc}")
            continue
        print(format_report(info, args.format))
        results.append(info)
        if args.output_file:
            if _write_output(args.output_file, args.format, results):
                print(f"Result exported to {args.output_file}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
