"""Command-line interface: argument parsing, input validation and continuous query loop."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from data_integrity import DataIntegrityChecker
from data_loader import DATA_FILE_PATH, DataLoadError
from models import Query, Route
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig, PathNotFoundError
from report import SUPPORTED_FORMATS, ReportExporter
from route_planner import plan_route

INPUT_PROMPT = "Enter query as 'Starting Station; Ending Station' (or 'q' to quit): "
QUIT_WORDS = ("q", "quit", "exit")
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class InputFormatError(ValueError):
    """The query text does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(LookupError):
    """A station name does not match any official station."""


class LogicalQueryError(ValueError):
    """The query is syntactically valid but logically invalid."""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway fare calculation system (shortest path + fare).",
    )
    parser.add_argument("--output_file", default=None, help="file to export query results to")
    parser.add_argument(
        "--format", choices=SUPPORTED_FORMATS, default="text", help="output format: text or json"
    )
    parser.add_argument(
        "--mode", choices=VALID_MODES, default="shortest_distance", help="path query mode"
    )
    parser.add_argument("--max_transfers", type=int, default=None, help="maximum number of transfers")
    parser.add_argument("--line_preference", default=None, help="preferred line, e.g. 'Line 1'")
    parser.add_argument(
        "--check_data", action="store_true", help="run the data integrity check and exit"
    )
    args = parser.parse_args(argv)
    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be non-negative")
    return args


def parse_query(text: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' into two stripped names."""
    if ";" not in text:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    parts = text.split(";")
    if len(parts) != 2:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(FORMAT_ERROR_MESSAGE)
    return start, end


def resolve_station(network: SubwayNetwork, raw_name: str, role: str) -> str:
    """Map user input to an official station name or raise StationNotFoundError."""
    canonical = network.standardize_station(raw_name)
    if canonical is None:
        raise StationNotFoundError(
            f"{role} station '{raw_name}' does not exist, please check the station name"
        )
    return canonical


def run_query(network: SubwayNetwork, text: str, config: PathfindingConfig) -> Tuple[Route, Query]:
    """Validate the query text, compute the route and return (route, query)."""
    raw_start, raw_end = parse_query(text)
    start = resolve_station(network, raw_start, "Starting")
    end = resolve_station(network, raw_end, "Ending")
    if start == end:
        raise LogicalQueryError("Starting station cannot be the same as the ending station")
    query = Query(start_station=start, end_station=end, mode=config.mode, timestamp=datetime.now())
    route = plan_route(network, start, end, config)
    return route, query


def _interactive_loop(network: SubwayNetwork, config: PathfindingConfig, exporter: ReportExporter) -> None:
    """Read queries until the user quits, reporting errors without terminating."""
    while True:
        try:
            raw = input(INPUT_PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in QUIT_WORDS:
            break

        try:
            route, query = run_query(network, text, config)
        except (InputFormatError, StationNotFoundError, LogicalQueryError) as exc:
            print(f"Error: {exc}")
            continue
        except PathNotFoundError:
            print(
                "Error: no route found between the two stations under the current "
                "transfer/line constraints"
            )
            continue
        except Exception as exc:  # path calculation / fare calculation failures
            print(f"Error: failed to calculate the route: {exc}")
            continue

        try:
            output = exporter.render(route, query)
        except Exception as exc:
            print(f"Error: failed to generate the report: {exc}")
            continue
        print(output)

        if exporter.output_file:
            try:
                written = exporter.write()
                print(f"Results saved to: {written}")
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (DataLoadError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = DataIntegrityChecker(network).run()
        print(report.format_text())
        return 0 if report.passed else 1

    preferred: List[str] = []
    if args.line_preference:
        preferred = [args.line_preference.strip()]
        if preferred[0] not in network.line_names():
            print(f"Warning: line preference '{preferred[0]}' is not a known line; it will be ignored.")

    try:
        config = PathfindingConfig(
            mode=args.mode, max_transfers=args.max_transfers, preferred_lines=preferred
        )
        exporter = ReportExporter(format_name=args.format, output_file=args.output_file)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway Fare Calculator")
    print(f"Mode: {config.mode}  Max transfers: {config.max_transfers if config.max_transfers is not None else 'unlimited'}")
    print("Type 'q' to quit.")
    _interactive_loop(network, config, exporter)
    return 0
