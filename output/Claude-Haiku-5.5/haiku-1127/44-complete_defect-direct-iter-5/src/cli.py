"""Command-line interface for the Beijing Subway fare calculation system."""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

from data_loader import DATA_FILE_PATH, load_subway_data
from fare_calculator import Sum_money  # noqa: F401  (re-exported for convenience)
from path_report import build_summary, format_json, format_text
from pathfinding import MODE_SHORTEST_DISTANCE, MODES, PathfindingConfig, ShortestPath
from subway_network import SubwayNetwork

QUIT_COMMANDS = {"quit", "exit", "q"}
OUTPUT_FORMATS = ("text", "json")


class QueryFormatError(ValueError):
    """Raised when a query string does not follow the 'Start; End' format."""


def parse_query(raw: str) -> Tuple[str, str]:
    """Split a 'Starting Station; Ending Station' query into its two names.

    Raises:
        QueryFormatError: If the separator is missing or a name is empty.
    """
    message = "Input format incorrect, please use 'Starting Station; Ending Station' format"
    if ";" not in raw:
        raise QueryFormatError(message)
    parts = raw.split(";")
    if len(parts) != 2:
        raise QueryFormatError(message)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise QueryFormatError(message)
    return start, end


def parse_line_preference(value: Optional[str]) -> List[str]:
    """Parse a comma-separated list of preferred line names."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (shortest path and fare query)."
    )
    parser.add_argument("--output_file", default=None,
                        help="File to which query results are appended.")
    parser.add_argument("--format", dest="output_format", choices=OUTPUT_FORMATS, default="text",
                        help="Output format: text or json (default: text).")
    parser.add_argument("--mode", choices=MODES, default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")
    return args


class QueryService:
    """Executes station queries and produces formatted results."""

    def __init__(
        self,
        network: SubwayNetwork,
        mode: str = MODE_SHORTEST_DISTANCE,
        max_transfers: Optional[int] = None,
        preferred_lines: Optional[Iterable[str]] = None,
        output_format: str = "text",
        output_file: Optional[str] = None,
    ) -> None:
        self.network = network
        self.mode = mode
        self.max_transfers = max_transfers
        self.preferred_lines: List[str] = list(preferred_lines or [])
        self.output_format = output_format
        self.output_file = output_file
        self.config = PathfindingConfig(mode, max_transfers, self.preferred_lines)

    def run_query(self, raw: str) -> str:
        """Process one 'Start; End' query and return the rendered result or an error message."""
        try:
            start_raw, end_raw = parse_query(raw)
        except QueryFormatError as exc:
            return f"Error: {exc}"

        start = self.network.resolve_station_name(start_raw)
        if start is None:
            return (f"Error: Starting station '{start_raw}' does not exist, "
                    f"please check the station name")
        end = self.network.resolve_station_name(end_raw)
        if end is None:
            return (f"Error: Ending station '{end_raw}' does not exist, "
                    f"please check the station name")
        if start == end:
            return "Error: Starting station cannot be the same as the ending station"

        try:
            source_number = self.network.get_station_number(start)
            target_number = self.network.get_station_number(end)
            finder = ShortestPath(self.network.graph, source_number, self.config)
            nodes, edges = finder.path_with_edges(target_number)
        except Exception as exc:  # pragma: no cover - defensive
            return f"Error: path calculation failed: {exc}"

        if not nodes:
            limit = "unlimited" if self.max_transfers is None else str(self.max_transfers)
            return (f"Error: no route found from '{start}' to '{end}' "
                    f"(mode={self.mode}, max_transfers={limit})")

        stations = [self.network.station_name(n) for n in nodes]
        query = {
            "start": start,
            "end": end,
            "mode": self.mode,
            "max_transfers": self.max_transfers,
            "line_preference": self.preferred_lines,
        }
        try:
            summary = build_summary(query, stations, edges)
            output = format_json(summary) if self.output_format == "json" else format_text(summary)
        except Exception as exc:
            return f"Error: fare calculation failed: {exc}"

        self._export(output)
        return output

    def _export(self, output: str) -> None:
        """Append a rendered result to the output file, if configured."""
        if not self.output_file:
            return
        try:
            with open(self.output_file, "a", encoding="utf-8") as handle:
                handle.write(output + "\n\n")
        except OSError as exc:
            print(f"Warning: could not write to '{self.output_file}': {exc}", file=sys.stderr)


def run_interactive(service: QueryService, input_func=input) -> None:
    """Run the continuous query loop until the user quits."""
    print("Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' "
          "(or 'quit' to exit).")
    while True:
        try:
            raw = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in QUIT_COMMANDS:
            break
        print(service.run_query(text))
        print()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point of the CLI. Returns a process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork.from_data(data)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        issues = network.check_data_integrity()
        print(f"Stations: {network.station_count()}, connections: {network.graph.num_edges()}")
        if not issues:
            print("Data integrity check passed.")
            return 0
        print(f"Data integrity check found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    preferred = parse_line_preference(args.line_preference)
    known_lines = network.line_names()
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line preference '{line}' is not a known line", file=sys.stderr)

    service = QueryService(
        network,
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
        output_format=args.output_format,
        output_file=args.output_file,
    )
    run_interactive(service)
    return 0
