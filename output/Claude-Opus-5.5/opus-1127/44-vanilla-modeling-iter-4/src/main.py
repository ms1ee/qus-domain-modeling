"""
Command-line interface for the Beijing Subway fare calculation system.

Usage examples::

    python src/main.py
    python src/main.py --mode least_transfer --format json --output_file out.json
    python src/main.py --check_data
"""

import argparse
import difflib
import sys

from data_loader import DATA_FILE_PATH, build_network, load_subway_data
from data_manager import SubwayDataManager
from fare_calculator import Sum_money
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_route_result, export_results, format_result

QUIT_WORDS = {"q", "quit", "exit"}
FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base error for user-facing query problems."""


class InputFormatError(QueryError):
    pass


class StationNotFoundError(QueryError):
    pass


class PathCalculationError(QueryError):
    pass


class FareCalculationError(QueryError):
    pass


def _norm(name):
    return " ".join(str(name).split()).casefold()


def parse_query_input(text):
    """Parse 'Start; End' into (start, end). Raises InputFormatError."""
    if text is None:
        raise InputFormatError(FORMAT_ERROR)
    text = text.replace("；", ";")
    parts = text.split(";")
    if len(parts) != 2:
        raise InputFormatError(FORMAT_ERROR)
    start, end = (" ".join(p.split()) for p in parts)
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR)
    return start, end


class SubwayFareApp:
    """Application facade combining network, path finding, fares and reports."""

    def __init__(self, network):
        self.network = network
        self._name_index = {_norm(n): n for n in network.station_names()}
        self._line_index = {_norm(l): l for l in network.all_lines()}

    def resolve_station(self, name):
        """Return official station name or None."""
        if name in self.network.station_to_number:
            return name
        return self._name_index.get(_norm(name))

    def suggest(self, name):
        matches = difflib.get_close_matches(name, self.network.station_names(), n=3, cutoff=0.6)
        return matches

    def resolve_lines(self, preference):
        """Parse comma-separated line preference into known line names."""
        if not preference:
            return [], []
        known, unknown = [], []
        for part in str(preference).split(","):
            part = part.strip()
            if not part:
                continue
            resolved = self._line_index.get(_norm(part))
            if resolved:
                known.append(resolved)
            else:
                unknown.append(part)
        return known, unknown

    def query(self, start, end, mode="shortest_distance", max_transfers=None, line_preference=None):
        official_start = self.resolve_station(start)
        if official_start is None:
            msg = f"Starting station '{start}' does not exist, please check the station name"
            sugg = self.suggest(start)
            if sugg:
                msg += f" (did you mean: {', '.join(sugg)}?)"
            raise StationNotFoundError(msg)
        official_end = self.resolve_station(end)
        if official_end is None:
            msg = f"Ending station '{end}' does not exist, please check the station name"
            sugg = self.suggest(end)
            if sugg:
                msg += f" (did you mean: {', '.join(sugg)}?)"
            raise StationNotFoundError(msg)
        if official_start == official_end:
            raise InputFormatError("Starting station cannot be the same as the ending station")

        preferred, _unknown = self.resolve_lines(line_preference)
        try:
            config = PathfindingConfig(mode=mode, max_transfers=max_transfers, preferred_lines=preferred)
            src = self.network.station_to_number[official_start]
            sp = ShortestPath(self.network.graph_obj, src, config)
        except Exception as exc:
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc
        target = self.network.station_to_number[official_end]
        if not sp.has_path_to(target):
            extra = f" within {max_transfers} transfer(s)" if max_transfers is not None else ""
            raise PathCalculationError(
                f"No route found from '{official_start}' to '{official_end}'{extra}")
        try:
            Sum_money(sp.dist_to[target])
        except Exception as exc:
            raise FareCalculationError(f"Fare calculation failed: {exc}") from exc
        try:
            return build_route_result(self.network, sp, official_start, official_end, mode,
                                      max_transfers, line_preference)
        except Exception as exc:
            raise PathCalculationError(f"Path calculation failed: {exc}") from exc


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None, help="Export query results to this file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--mode", choices=list(MODES), default="shortest_distance",
                        help="Path query mode")
    parser.add_argument("--max_transfers", type=int, default=None, help="Maximum number of transfers")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true", help="Run data integrity check and exit")
    parser.add_argument("--data_file", default=DATA_FILE_PATH, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = SubwayDataManager(data, args.data_file).check_integrity()
        print(report.to_text())
        return 0 if report.is_valid else 1

    network = build_network(data, args.data_file)
    app = SubwayFareApp(network)

    if args.line_preference:
        _known, unknown = app.resolve_lines(args.line_preference)
        if unknown:
            print(f"Warning: unknown line(s) in preference ignored: {', '.join(unknown)}")

    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {args.mode}. Enter 'Starting Station; Ending Station', or 'q' to quit.")
    results = []
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in QUIT_WORDS:
            break
        if not line.strip():
            continue
        try:
            start, end = parse_query_input(line)
            result = app.query(start, end, args.mode, args.max_transfers, args.line_preference)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # unexpected failure; keep the loop alive
            print(f"Error: unexpected failure: {exc}")
            continue
        print(format_result(result, args.format))
        if args.output_file:
            results.append(result)
            try:
                export_results(results, args.output_file, args.format)
                print(f"Result exported to {args.output_file}")
            except OSError as exc:
                print(f"Error: failed to write output file: {exc}")
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
