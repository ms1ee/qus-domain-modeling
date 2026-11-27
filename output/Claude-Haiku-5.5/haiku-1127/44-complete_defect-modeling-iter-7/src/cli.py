"""Command-line interface: argument parsing, input validation and the query loop."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .data_loader import DataLoadError
from .integrity import IntegrityChecker
from .network import SubwayNetwork, UnknownStationError
from .pathfinding import (
    DEFAULT_MAX_TRANSFERS,
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    NoPathError,
    PathfindingConfig,
    ShortestPath,
)
from .report import TripSummary, build_summary, export_report, render_json, render_text

PROMPT = "Enter 'Starting Station; Ending Station' (or 'quit' to exit): "
EXIT_COMMANDS = {"quit", "exit", "q"}


class InputFormatError(ValueError):
    """Raised when a query line does not follow the 'Start; End' format."""


def parse_query(text: str) -> tuple[str, str]:
    """Split a 'Starting Station; Ending Station' line into its two names.

    Raises:
        InputFormatError: if the separator is missing or a name is empty.
    """
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(text)
    return parts[0].strip(), parts[1].strip()


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Beijing Subway fare calculation system (Dijkstra shortest path).",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="write query results to this file (results are appended during a session)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: text or json (default: text)",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=MODE_SHORTEST_DISTANCE,
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help=f"maximum number of line transfers (default: {DEFAULT_MAX_TRANSFERS})",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line name, e.g. 'Line 1'",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def _normalize(text: str) -> str:
    return "".join(text.split()).casefold()


def _match_line(network: SubwayNetwork, requested: str) -> Optional[str]:
    """Return the canonical network line name matching ``requested``, or None."""
    key = _normalize(requested)
    for line in network.lines():
        if _normalize(line) == key:
            return line
    return None


def run_query(
    network: SubwayNetwork, start_name: str, end_name: str, config: PathfindingConfig
) -> TripSummary:
    """Compute the route and summary between two official station names.

    Raises:
        UnknownStationError: if a station does not exist.
        NoPathError: if no route satisfies the constraints.
        ValueError: on invalid configuration or fare errors.
    """
    src = network.station_number(start_name)
    dst = network.station_number(end_name)
    search = ShortestPath(network.graph, src, config)
    numbers, edges = search.path_with_edges(dst)
    query = {
        "start_station": network.station_name(src),
        "end_station": network.station_name(dst),
        "mode": config.mode,
        "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines) if config.preferred_lines else None,
    }
    return build_summary(network, query, numbers, edges)


def _interactive_loop(network: SubwayNetwork, config: PathfindingConfig, args: argparse.Namespace) -> int:
    """Continuously read and answer queries until the user quits."""
    print("Beijing Subway fare calculator. Type 'quit' to exit.")
    first_write = True
    while True:
        try:
            raw = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            start_raw, end_raw = parse_query(text)
        except InputFormatError:
            print("Input format incorrect, please use 'Starting Station; Ending Station' format")
            continue

        start = network.standard_name(start_raw)
        if start is None:
            print(f"Starting station '{start_raw}' does not exist, please check the station name")
            continue
        end = network.standard_name(end_raw)
        if end is None:
            print(f"Ending station '{end_raw}' does not exist, please check the station name")
            continue
        if start == end:
            print("Starting station cannot be the same as the ending station")
            continue

        try:
            summary = run_query(network, start, end, config)
        except NoPathError as exc:
            print(f"Path calculation failed: {exc}")
            continue
        except (UnknownStationError, KeyError, ValueError) as exc:
            print(f"Path or fare calculation failed: {exc}")
            continue

        content = render_json(summary) if args.format == "json" else render_text(summary)
        if args.output_file:
            try:
                export_report(content, args.output_file, append=not first_write)
            except OSError as exc:
                print(f"Failed to write output file: {exc}")
                continue
            first_write = False
            print(f"Result written to {args.output_file}")
        else:
            print(content)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    try:
        network = SubwayNetwork()
    except (DataLoadError, KeyError, TypeError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = IntegrityChecker(network).run()
        print(report.render())
        return 0 if report.passed else 1

    preferred: list[str] = []
    if args.line_preference:
        canonical = _match_line(network, args.line_preference)
        if canonical is None:
            print(f"Error: line '{args.line_preference}' does not exist", file=sys.stderr)
            return 2
        preferred = [canonical]

    max_transfers = DEFAULT_MAX_TRANSFERS if args.max_transfers is None else args.max_transfers
    try:
        config = PathfindingConfig(
            mode=args.mode, max_transfers=max_transfers, preferred_lines=preferred
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return _interactive_loop(network, config, args)
