"""
Command-line interface for the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--output_file FILE] [--format text|json]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"]
                       [--check_data]

Enter queries as "Starting Station; Ending Station".  Type 'quit' to exit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DATA_FILE_PATH, SubwayDataManager, load_subway_data  # noqa: E402
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath  # noqa: E402
from visualization import build_route_info, format_json_report, format_text_report, to_json_dict  # noqa: E402

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = {"quit", "exit", "q"}


class QueryError(Exception):
    """Raised for invalid user input."""


def _normalize(name: str) -> str:
    return " ".join(name.split()).lower()


class StationResolver:
    def __init__(self, names):
        self.names = set(names)
        self.norm = {}
        for n in names:
            self.norm.setdefault(_normalize(n), n)

    def resolve(self, raw: str):
        name = raw.strip()
        if name in self.names:
            return name
        key = _normalize(name)
        if key in self.norm:
            return self.norm[key]
        for suffix in (" station", "站"):
            if key.endswith(suffix) and key[: -len(suffix)].strip() in self.norm:
                return self.norm[key[: -len(suffix)].strip()]
        return None


def parse_query(text: str):
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise QueryError(FORMAT_ERROR)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryError(FORMAT_ERROR)
    return start, end


class SubwayFareApp:
    def __init__(self, network, config, output_format="text", output_file=None):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file
        self.resolver = StationResolver(network.station_names())
        self._results = []
        self._file_started = False

    def query(self, text: str) -> dict:
        start_raw, end_raw = parse_query(text)
        start = self.resolver.resolve(start_raw)
        if start is None:
            raise QueryError(f"Starting station '{start_raw}' does not exist, please check the station name")
        end = self.resolver.resolve(end_raw)
        if end is None:
            raise QueryError(f"Ending station '{end_raw}' does not exist, please check the station name")
        if start == end:
            raise QueryError("Starting station cannot be the same as the ending station")
        s_num = self.network.station_to_number[start]
        e_num = self.network.station_to_number[end]
        try:
            sp = ShortestPath(self.network.graph, s_num, self.config)
            path, edges = sp.path_with_edges(e_num)
        except Exception as exc:  # path calculation exception handling
            raise QueryError(f"Path calculation error: {exc}")
        if not path:
            msg = f"No route found from '{start}' to '{end}'"
            if self.config.max_transfers is not None:
                msg += f" within {self.config.max_transfers} transfer(s)"
            raise QueryError(msg)
        names = [self.network.number_to_station[n] for n in path]
        query = {
            "start": start, "end": end, "mode": self.config.mode,
            "max_transfers": self.config.max_transfers,
            "line_preference": self.config.preferred_lines,
        }
        try:
            return build_route_info(names, edges, query)
        except Exception as exc:  # fare calculation exception handling
            raise QueryError(f"Fare calculation error: {exc}")

    def render(self, info: dict) -> str:
        return format_json_report(info) if self.output_format == "json" else format_text_report(info)

    def export(self, info: dict) -> None:
        if not self.output_file:
            return
        if self.output_format == "json":
            self._results.append(to_json_dict(info))
            content = self._results[0] if len(self._results) == 1 else self._results
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            mode = "a" if self._file_started else "w"
            with open(self.output_file, mode, encoding="utf-8") as f:
                f.write(format_text_report(info) + "\n")
        self._file_started = True

    def handle(self, text: str) -> bool:
        """Process one input line; returns True on success."""
        try:
            info = self.query(text)
        except QueryError as exc:
            print(f"Error: {exc}")
            return False
        except Exception as exc:
            print(f"Error: unexpected failure: {exc}")
            return False
        print(self.render(info))
        try:
            self.export(info)
            if self.output_file:
                print(f"Result exported to {self.output_file}")
        except OSError as exc:
            print(f"Error: cannot write output file: {exc}")
        return True

    def run(self) -> None:
        print("Beijing Subway Fare Calculation System")
        print("Enter 'Starting Station; Ending Station' (type 'quit' to exit).")
        while True:
            try:
                line = input("Query> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            line = line.strip()
            if not line:
                continue
            if line.lower() in EXIT_COMMANDS:
                break
            self.handle(line)
        print("Goodbye!")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="Export query results to this file")
    p.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    p.add_argument("--mode", default="shortest_distance", choices=list(VALID_MODES), help="Path query mode")
    p.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    p.add_argument("--line_preference", default=None, help="Preferred line(s), comma separated")
    p.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    return p.parse_args(argv)


def print_check_report(report: dict) -> None:
    print("Data integrity check")
    for k, v in report["stats"].items():
        print(f"  {k}: {v}")
    print(f"Errors: {len(report['errors'])}")
    for e in report["errors"]:
        print(f"  [ERROR] {e}")
    print(f"Warnings: {len(report['warnings'])}")
    for w in report["warnings"]:
        print(f"  [WARNING] {w}")
    print("Result: " + ("PASSED" if report["ok"] else "FAILED"))


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers cannot be negative")
        return 2
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1
    manager = SubwayDataManager(data, args.data_file)
    if args.check_data:
        report = manager.check_integrity()
        print_check_report(report)
        return 0 if report["ok"] else 1

    network = manager.build_network()
    preferred = []
    if args.line_preference:
        preferred = [p.strip() for p in args.line_preference.split(",") if p.strip()]
        known = {l.lower() for l in manager.get_lines()}
        for p in preferred:
            if p.lower() not in known:
                print(f"Warning: preferred line '{p}' not found in data")
    try:
        config = PathfindingConfig(args.mode, args.max_transfers, preferred)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2
    app = SubwayFareApp(network, config, args.format, args.output_file)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
