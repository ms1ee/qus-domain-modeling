"""Command-line interface for the Beijing Subway fare calculation system.

Responsibilities:
    * parse command-line arguments
    * validate user input ("Starting Station; Ending Station")
    * run continuous query loops
    * print or export query results
    * run the data integrity check when ``--check_data`` is given
"""

import argparse
from typing import List, Optional, Tuple

from data_manager import run_integrity_check
from data_loader import DATA_FILE_PATH  # noqa: F401  (re-exported for convenience)
from path_visualizer import render
from pathfinding import PathfindingConfig, VALID_MODES
from route_service import (
    InvalidQueryError,
    RouteError,
    StationNotFoundError,
    compute_route,
)
from subway_network import SubwayNetwork


EXIT_COMMANDS = ("quit", "exit", "q")
PROMPT_TEXT = "Enter query as 'Starting Station; Ending Station' (or 'quit' to exit): "


class InputFormatError(ValueError):
    """Raised when the user input does not match 'Starting Station; Ending Station'."""


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (command-line interface)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Export query results to this file (results are appended).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format: 'text' (default) or 'json'.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="shortest_distance",
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers",
        type=int,
        default=None,
        help="Maximum number of allowed transfers (default: unlimited).",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="Preferred subway line, e.g. \"Line 1\". Other lines are penalised softly.",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="Run the data integrity check and exit.",
    )
    return parser


def parse_query(text: str) -> Tuple[str, str]:
    """Split a raw query string into (starting station, ending station).

    Accepts the ASCII semicolon ';' as well as the full-width '；' separator.

    Raises:
        InputFormatError: if the format is not 'Starting Station; Ending Station'.
    """
    if not isinstance(text, str):
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    normalized = text.replace("\uff1b", ";")
    if normalized.count(";") != 1:
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    start, end = [part.strip() for part in normalized.split(";")]
    if not start or not end:
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    return start, end


def resolve_query(network: SubwayNetwork, text: str) -> Tuple[str, str]:
    """Parse the query and standardise both station names against the network.

    Returns:
        (official starting station name, official ending station name)

    Raises:
        InputFormatError, StationNotFoundError, InvalidQueryError
    """
    start_input, end_input = parse_query(text)

    start = network.resolve_station(start_input)
    if start is None:
        raise StationNotFoundError(
            f"Starting station '{start_input}' does not exist, please check the station name"
        )
    end = network.resolve_station(end_input)
    if end is None:
        raise StationNotFoundError(
            f"Ending station '{end_input}' does not exist, please check the station name"
        )
    if start == end:
        raise InvalidQueryError("Starting station cannot be the same as the ending station")
    return start, end


def resolve_line(network: SubwayNetwork, text: Optional[str]) -> Optional[str]:
    """Match a user supplied line name (case-insensitive, '1' accepted for 'Line 1')."""
    if text is None:
        return None
    key = text.strip().casefold()
    if not key:
        return None
    lines = network.lines()
    for line in lines:
        if line.casefold() == key:
            return line
    for line in lines:
        if line.casefold() == "line " + key:
            return line
    return None


def run_query(
    network: SubwayNetwork,
    text: str,
    config: PathfindingConfig,
    fmt: str,
    output_file: Optional[str],
) -> bool:
    """Execute one query, print the result and optionally export it.

    Returns:
        True if the query succeeded, False otherwise.
    """
    try:
        start, end = resolve_query(network, text)
    except RouteError as exc:
        print(f"Error: {exc}")
        return False
    except InputFormatError as exc:
        print(f"Error: {exc}")
        return False

    try:
        route = compute_route(network, start, end, config)
        output = render(route, fmt)
    except RouteError as exc:
        print(f"Error: {exc}")
        return False
    except Exception as exc:  # Path or fare calculation failure must not stop the CLI.
        print(f"Error: path or fare calculation failed: {exc}")
        return False

    print(output)

    if output_file:
        try:
            with open(output_file, "a", encoding="utf-8") as handle:
                handle.write(output)
                handle.write("\n\n")
            print(f"Result exported to: {output_file}")
        except OSError as exc:
            print(f"Error: could not write output file '{output_file}': {exc}")
            return False
    return True


def interactive_loop(
    network: SubwayNetwork,
    config: PathfindingConfig,
    fmt: str,
    output_file: Optional[str],
) -> None:
    """Continuously read queries until the user quits or input ends."""
    print("Beijing Subway fare calculator. Type 'quit' to exit.")
    print("Input format: Starting Station; Ending Station")
    while True:
        try:
            raw = input(PROMPT_TEXT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = raw.strip()
        if not text:
            continue
        if text.casefold() in EXIT_COMMANDS:
            break
        run_query(network, text, config, fmt, output_file)
        print()
    print("Goodbye.")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork.from_file()
    except (OSError, ValueError) as exc:
        print(f"Error: could not load subway data: {exc}")
        return 1

    if args.check_data:
        report = run_integrity_check(network)
        print(report.render())
        return 0 if report.ok else 1

    preferred: List[str] = []
    if args.line_preference:
        line = resolve_line(network, args.line_preference)
        if line is None:
            print(
                f"Warning: line '{args.line_preference}' not found in the network; "
                "line preference ignored."
            )
        else:
            preferred = [line]

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    interactive_loop(network, config, args.format, args.output_file)
    return 0
