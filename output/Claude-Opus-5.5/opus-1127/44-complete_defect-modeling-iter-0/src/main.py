"""
Command-line interface of the Beijing Subway fare calculation system.

Usage:
    python src/main.py [--format text|json] [--output_file FILE]
                       [--mode shortest_distance|least_transfer|comprehensive]
                       [--max_transfers N] [--line_preference "Line 1"] [--check_data]

Enter queries as "Starting Station; Ending Station"; enter 'q' to quit.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from data_loader import DATA_FILE_PATH
    from network import SubwayNetwork, DataIntegrityChecker
    from pathfinding import PathfindingConfig, VALID_MODES
    from report import format_text_report, build_json_report
except ImportError:  # pragma: no cover
    from .data_loader import DATA_FILE_PATH
    from .network import SubwayNetwork, DataIntegrityChecker
    from .pathfinding import PathfindingConfig, VALID_MODES
    from .report import format_text_report, build_json_report

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SAME_STATION_ERROR = "Starting station cannot be the same as the ending station"
QUIT_WORDS = {"q", "quit", "exit"}


class QueryError(Exception):
    """User-facing query error."""


@dataclass
class QueryConfiguration:
    output_file: Optional[str] = None
    format: str = "text"
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: List[str] = field(default_factory=list)
    check_data: bool = False
    data_file: str = DATA_FILE_PATH


def _non_negative_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    if n < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return n


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    p.add_argument("--output_file", default=None, help="export query results to this file")
    p.add_argument("--format", choices=["text", "json"], default="text", help="output format")
    p.add_argument("--mode", choices=list(VALID_MODES), default="shortest_distance", help="path query mode")
    p.add_argument("--max_transfers", type=_non_negative_int, default=None, help="maximum transfers")
    p.add_argument("--line_preference", default=None, help="preferred line(s), comma separated")
    p.add_argument("--check_data", action="store_true", help="run data integrity check and exit")
    p.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    prefs = [x.strip() for x in a.line_preference.split(",") if x.strip()] if a.line_preference else []
    return QueryConfiguration(a.output_file, a.format, a.mode, a.max_transfers, prefs, a.check_data, a.data_file)


class CLI:
    input_separator = ";"

    def __init__(self, network, config, out=sys.stdout):
        self.network = network
        self.config = config
        self.out = out
        self.continuous_mode = True
        self.json_results = []
        self.path_config = PathfindingConfig(config.mode, config.max_transfers, config.line_preference)

    def _print(self, text=""):
        print(text, file=self.out)

    def parse_query(self, raw):
        """Validate input and return (start, end) official station names."""
        if raw is None:
            raise QueryError(FORMAT_ERROR)
        text = raw.replace("；", ";")
        parts = text.split(self.input_separator)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise QueryError(FORMAT_ERROR)
        start_raw, end_raw = parts[0].strip(), parts[1].strip()
        start = self.network.resolve_station(start_raw)
        if start is None:
            raise QueryError(self._missing("Starting", start_raw))
        end = self.network.resolve_station(end_raw)
        if end is None:
            raise QueryError(self._missing("Ending", end_raw))
        if start == end:
            raise QueryError(SAME_STATION_ERROR)
        return start, end

    def _missing(self, kind, name):
        msg = f"{kind} station '{name}' does not exist, please check the station name"
        sugg = self.network.suggest_stations(name)
        if sugg:
            msg += f" (did you mean: {', '.join(sugg)}?)"
        return msg

    def process_query(self, raw):
        """Process one query; returns the rendered output or raises QueryError."""
        start, end = self.parse_query(raw)
        try:
            route = self.network.find_route(start, end, self.path_config)
        except (ValueError, TypeError, ArithmeticError) as exc:
            if "fare" in str(exc).lower() or "distance" in str(exc).lower():
                raise QueryError(f"Fare calculation error: {exc}")
            raise QueryError(f"Path calculation error: {exc}")
        except Exception as exc:
            raise QueryError(f"Path calculation error: {exc}")
        if route is None:
            constraint = " under the current constraints" if self.config.max_transfers is not None else ""
            raise QueryError(f"No route found from '{start}' to '{end}'{constraint}")
        if self.config.format == "json":
            data = build_json_report(route, self.path_config)
            self.json_results.append(data)
            rendered = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            rendered = format_text_report(route)
        self._export(rendered)
        return rendered

    def _export(self, rendered):
        path = self.config.output_file
        if not path:
            return
        try:
            if self.config.format == "json":
                payload = self.json_results[0] if len(self.json_results) == 1 else self.json_results
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
            else:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(rendered + "\n\n")
        except OSError as exc:
            self._print(f"Failed to write output file '{path}': {exc}")

    def run(self, input_func=input):
        self._print("Beijing Subway Fare Calculation System")
        self._print("Enter 'Starting Station; Ending Station' (or 'q' to quit).")
        while self.continuous_mode:
            try:
                raw = input_func("> ")
            except (EOFError, KeyboardInterrupt):
                self._print()
                break
            raw = raw.strip()
            if not raw:
                continue
            if raw.lower() in QUIT_WORDS:
                break
            try:
                self._print(self.process_query(raw))
            except QueryError as exc:
                self._print(f"Error: {exc}")
            except Exception as exc:  # last-resort safety net
                self._print(f"Unexpected error: {exc}")
            self._print()
        self._print("Goodbye!")


def main(argv=None):
    config = parse_args(argv)
    try:
        network = SubwayNetwork(config.data_file)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1
    if config.check_data:
        checker = DataIntegrityChecker(network)
        ok = checker.run()
        print(checker.format_report())
        return 0 if ok else 1
    CLI(network, config).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
