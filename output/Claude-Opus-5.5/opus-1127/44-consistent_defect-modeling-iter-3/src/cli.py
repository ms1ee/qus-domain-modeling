"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import re
import sys

from data_checker import DataIntegrityChecker
from data_loader import DATA_FILE_PATH, DataLoadError, build_graph, load_subway_data
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_route_info, export_results, format_json, format_text

QUIT_WORDS = {"q", "quit", "exit"}
FORMAT_ERROR = ("Input format incorrect, please use "
                "'Starting Station; Ending Station' format")


class ValidationError(Exception):
    def __init__(self, error_type, message):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH)
    args = p.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        p.error("--max_transfers must be non-negative")
    return args


class CommandLineInterface:
    def __init__(self, args, data):
        self.args = args
        self.data = data
        self.graph, self.station_to_number, self.number_to_station = build_graph(data)
        prefs = []
        if args.line_preference:
            prefs = [s.strip() for s in re.split(r"[,，]", args.line_preference) if s.strip()]
        self.config = PathfindingConfig(args.mode, args.max_transfers, prefs)
        self.results = []
        self.is_running = False
        self._lower = {n.lower(): n for n in self.station_to_number}

    def resolve_station(self, name, role):
        name = name.strip()
        if name in self.station_to_number:
            return name
        cands = [name.lower()]
        for suffix in ("站", " station"):
            if name.lower().endswith(suffix):
                cands.append(name.lower()[:-len(suffix)].strip())
        for c in cands:
            if c in self._lower:
                return self._lower[c]
        msg = f"{role} station '{name}' does not exist, please check the station name"
        close = difflib.get_close_matches(name, list(self.station_to_number), n=3)
        if close:
            msg += " (did you mean: " + ", ".join(close) + "?)"
        raise ValidationError("station_not_found", msg)

    def parse_query(self, line):
        parts = re.split(r"[;,；，]", line)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ValidationError("format", FORMAT_ERROR)
        start = self.resolve_station(parts[0], "Starting")
        end = self.resolve_station(parts[1], "Ending")
        if start == end:
            raise ValidationError("logic",
                                  "Starting station cannot be the same as the ending station")
        return start, end

    def process_query(self, line):
        """Process one query line; returns output text."""
        try:
            start, end = self.parse_query(line)
        except ValidationError as e:
            return e.message
        try:
            s = self.station_to_number[start]
            t = self.station_to_number[end]
            sp = ShortestPath(self.graph, s, self.config)
            if not sp.has_path_to(t):
                msg = f"No path found from '{start}' to '{end}'"
                if self.config.max_transfers is not None:
                    msg += f" within {self.config.max_transfers} transfer(s)"
                return msg
            stations, edges = sp.path_with_edges(t)
            transfers = sp.get_transfer_count(t)
        except Exception as e:  # path calculation exception
            return f"Path calculation error: {e}"
        try:
            info = build_route_info(start, end, self.config.mode, stations, edges,
                                    self.number_to_station, transfers)
        except Exception as e:  # fare calculation exception
            return f"Fare calculation error: {e}"
        self.results.append(info)
        if self.args.output_file:
            try:
                export_results(self.results, self.args.output_file, self.args.format)
            except OSError as e:
                print(f"Failed to write output file: {e}", file=sys.stderr)
        return format_json(info) if self.args.format == "json" else format_text(info)

    def run(self, stdin=None):
        stdin = stdin or sys.stdin
        self.is_running = True
        print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' "
              "(or 'quit' to exit).")
        while self.is_running:
            print("> ", end="", flush=True)
            line = stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            if line.lower() in QUIT_WORDS:
                break
            print(self.process_query(line), flush=True)
        self.is_running = False
        print("Goodbye.")


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except DataLoadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.check_data:
        checker = DataIntegrityChecker(data)
        ok = checker.run()
        print(checker.report())
        return 0 if ok else 1
    CommandLineInterface(args, data).run()
    return 0
