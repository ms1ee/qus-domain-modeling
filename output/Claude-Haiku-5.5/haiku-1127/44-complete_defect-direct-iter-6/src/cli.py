"""Command-line interface for the Beijing Subway fare calculation system.

Responsibilities:
    * parse command-line arguments (--output_file, --format, --mode,
      --max_transfers, --line_preference, --check_data);
    * validate user input ("Starting Station; Ending Station");
    * run route queries and render / export the results;
    * keep accepting queries until the user quits.
"""

import argparse
import json
import sys
from typing import Callable, Optional, Sequence, Tuple

from data_check import format_check_report, run_data_check
from data_loader import DATA_FILE_PATH, load_subway_data
from network import NetworkDataError, SubwayNetwork, build_network
from path_report import append_result_to_file, render_json, render_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    ShortestPath,
)
from path_report import build_result


INPUT_FORMAT_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)
EXIT_COMMANDS = {"quit", "exit", "q"}
HELP_COMMANDS = {"help", "?"}
HELP_TEXT = (
    "Enter a query in the form 'Starting Station; Ending Station',\n"
    "for example: 西直门; 国贸\n"
    "Commands: 'help' shows this message, 'quit' (or 'exit') leaves the program."
)
RESULT_SEPARATOR = "-" * 60


class QueryError(Exception):
    """Base class for user-facing query errors."""


class InputFormatError(QueryError):
    """Raised when the query text does not follow the 'A; B' format."""


class StationNotFoundError(QueryError):
    """Raised when a station name cannot be matched to an official station."""


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Append each query result to this file.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default) or 'json'.",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default=MODE_SHORTEST_DISTANCE,
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help="Maximum number of allowed transfers.",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="Preferred line name, e.g. 'Line 1'.",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="Run the data integrity check and exit.",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return build_arg_parser().parse_args(argv)


def parse_query(text: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' into two raw station names.

    Raises:
        InputFormatError: if the separator is missing or a name is empty.
    """
    if text.count(";") != 1:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    start_raw, end_raw = (part.strip() for part in text.split(";"))
    if not start_raw or not end_raw:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return start_raw, end_raw


def standardize_station(network: SubwayNetwork, raw_name: str, role: str) -> str:
    """Map a user-typed name to the official station name.

    Args:
        network: the loaded subway network.
        raw_name: the name typed by the user.
        role: "Starting" or "Ending", used in the error message.

    Raises:
        StationNotFoundError: if no official station matches.
    """
    official = network.resolve_station(raw_name)
    if official is None:
        raise StationNotFoundError(
            f"{role} station '{raw_name.strip()}' does not exist, "
            "please check the station name"
        )
    return official


def run_query(network: SubwayNetwork, text: str, config: PathfindingConfig) -> dict:
    """Execute one route query and return the structured result dictionary.

    Raises:
        QueryError (or a subclass) for any user-facing problem.
    """
    start_raw, end_raw = parse_query(text)
    start = standardize_station(network, start_raw, "Starting")
    end = standardize_station(network, end_raw, "Ending")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    source_number = network.number_of(start)
    target_number = network.number_of(end)

    try:
        finder = ShortestPath(network.graph, source_number, config)
    except ValueError as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    if not finder.has_path(target_number):
        raise QueryError(
            f"No route found from '{start}' to '{end}' with the current settings"
        )

    try:
        nodes, edges = finder.path_with_edges(target_number)
        transfer_count = finder.get_transfer_count(target_number)
    except ValueError as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    try:
        result = build_result(network, start, end, config, nodes, edges, transfer_count)
    except (ValueError, TypeError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc
    return result


def render_result(result: dict, output_format: str) -> str:
    """Render a result dictionary for the console."""
    if output_format == "json":
        return render_json(result, indent=2)
    return render_text(result)


def run_interactive(
    network: SubwayNetwork,
    config: PathfindingConfig,
    args: argparse.Namespace,
    input_func: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
) -> int:
    """Run the continuous query loop until the user quits or input ends."""
    output(
        "Beijing Subway fare calculator. Enter 'Starting Station; Ending Station' "
        "('help' for details, 'quit' to exit)."
    )
    while True:
        try:
            line = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            output("")
            break

        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in EXIT_COMMANDS:
            break
        if lowered in HELP_COMMANDS:
            output(HELP_TEXT)
            continue

        try:
            result = run_query(network, text, config)
        except QueryError as exc:
            output(f"Error: {exc}")
            continue
        except Exception as exc:  # Last-resort guard so the session keeps running.
            output(f"Error: unexpected failure while calculating the route: {exc}")
            continue

        output(render_result(result, args.output_format))

        if args.output_file:
            try:
                append_result_to_file(args.output_file, result, args.output_format)
                output(f"Result appended to {args.output_file}")
            except OSError as exc:
                output(f"Error: could not write output file: {exc}")
    return 0


def _resolve_line_preference(network: SubwayNetwork, raw: str) -> Optional[str]:
    """Match a user-supplied line name to a known line (case-insensitive)."""
    wanted = raw.strip()
    if wanted in network.line_stations:
        return wanted
    lowered = wanted.lower()
    for line in network.line_names():
        if line.lower() == lowered:
            return line
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point. Returns a process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = run_data_check(data)
        print(format_check_report(report))
        return 0 if report.is_ok() else 1

    try:
        network = build_network(data)
    except (NetworkDataError, ValueError, TypeError) as exc:
        print(f"Error: invalid subway data: {exc}", file=sys.stderr)
        return 1

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer", file=sys.stderr)
        return 2

    preferred = []
    if args.line_preference:
        line = _resolve_line_preference(network, args.line_preference)
        if line is None:
            available = ", ".join(network.line_names())
            print(
                f"Error: unknown line '{args.line_preference}'. "
                f"Available lines: {available}",
                file=sys.stderr,
            )
            return 2
        preferred = [line]

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return run_interactive(network, config, args)


def _json_dumps_compact(value: dict) -> str:
    """Helper kept for callers that need a compact JSON line."""
    return json.dumps(value, ensure_ascii=False)
