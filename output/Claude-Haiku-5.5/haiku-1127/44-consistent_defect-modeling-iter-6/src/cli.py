"""
Command-line interface for the Beijing Subway fare calculation system.

Supports an interactive continuous query loop, input validation with clear
error messages, command-line options for output format, query mode, transfer
limits, line preferences, file export and data integrity checks.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from typing import Callable, List, Optional, Sequence, Tuple

from data_loader import DATA_FILE_PATH
from fare_calculator import Sum_money  # noqa: F401  (documented dependency of the fare workflow)
from path_report import (
    QueryInfo,
    Report,
    build_report,
    build_summary,
    export_report,
)
from pathfinding import (
    VALID_MODES,
    MODE_SHORTEST_DISTANCE,
    NoRouteError,
    PathfindingConfig,
    PathfindingError,
    find_route,
)
from subway_network import SubwayNetwork, UnknownStationError

ERROR_INPUT_FORMAT = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_WORDS = ("quit", "exit", "q")


class QueryError(Exception):
    """A user-facing error in a query (bad input, unknown station, same station...)."""


class InputFormatError(QueryError):
    """The query string does not follow the 'Starting Station; Ending Station' format."""


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="Export each query result to this file (overwritten per query).")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format: text (console) or json (structured).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode.")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of transfers allowed.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), e.g. 'Line 1' (comma-separated for several).")
    parser.add_argument("--check_data", action="store_true",
                        help="Run data integrity checks and exit.")
    return parser.parse_args(argv)


def parse_query(text: str) -> Tuple[str, str]:
    """Split a query of the form 'Starting Station; Ending Station'.

    Both ';' and ',' (and their full-width forms) are accepted as separators.

    Raises:
        InputFormatError: If the input does not contain exactly two station names.
    """
    if text is None or not text.strip():
        raise InputFormatError(ERROR_INPUT_FORMAT)
    parts = [p.strip() for p in re.split(r"[;,；，]", text.strip())]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InputFormatError(ERROR_INPUT_FORMAT)
    return parts[0], parts[1]


def parse_line_preference(text: Optional[str]) -> List[str]:
    """Split a comma-separated line preference string into line names."""
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def validate_arguments(args: argparse.Namespace, network: SubwayNetwork) -> List[str]:
    """Return a list of error messages for invalid command-line arguments."""
    errors: List[str] = []
    if args.max_transfers is not None and args.max_transfers < 0:
        errors.append("--max_transfers must be a non-negative integer")
    known_lines = set(network.line_names())
    for line in parse_line_preference(args.line_preference):
        if line not in known_lines:
            errors.append(f"Unknown line in --line_preference: '{line}'")
    return errors


def _resolve_station(network: SubwayNetwork, raw: str, role: str, notices: List[str]) -> str:
    """Resolve a station name, recording a notice when fuzzy matching was used."""
    try:
        name, fuzzy = network.resolve_station(raw)
    except UnknownStationError:
        raise QueryError(f"{role} station '{raw}' does not exist, please check the station name")
    if fuzzy:
        notices.append(f"Note: {role.lower()} station '{raw}' matched to nearest station '{name}'")
    return name


def run_query(network: SubwayNetwork, text: str, args: argparse.Namespace) -> Tuple[Report, List[str]]:
    """Execute one query and return the rendered report and any notices.

    Raises:
        QueryError: For input, station or logical errors.
        PathfindingError: If no route exists or path computation fails.
    """
    notices: List[str] = []
    raw_start, raw_end = parse_query(text)
    start = _resolve_station(network, raw_start, "Starting", notices)
    end = _resolve_station(network, raw_end, "Ending", notices)

    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")

    preferred = parse_line_preference(args.line_preference)
    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    route = find_route(
        network.graph,
        network.number_to_name,
        network.number_of(start),
        network.number_of(end),
        config,
    )

    try:
        summary = build_summary(route)
    except Exception as exc:  # fare calculation exception handling
        raise QueryError(f"Fare calculation failed: {exc}") from exc

    query = QueryInfo(
        start_station=start,
        end_station=end,
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=", ".join(preferred) if preferred else None,
        timestamp=datetime.datetime.now(),
    )
    report = build_report(query, route, summary, args.format)
    return report, notices


def interactive_loop(
    network: SubwayNetwork,
    args: argparse.Namespace,
    input_func: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> int:
    """Run the continuous query loop until the user quits.

    Returns:
        Number of successful queries.
    """
    write("Beijing Subway Fare Calculation System")
    write(f"Stations loaded: {len(network.name_to_number)}, lines: {len(network.line_names())}")
    write("Enter 'Starting Station; Ending Station' to query, or 'quit' to exit.")

    successes = 0
    while True:
        try:
            text = input_func("Query> ")
        except (EOFError, KeyboardInterrupt):
            write("")
            break

        text = (text or "").strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            report, notices = run_query(network, text, args)
        except QueryError as exc:
            write(f"Error: {exc}")
            continue
        except NoRouteError as exc:
            write(f"Error: {exc}")
            continue
        except PathfindingError as exc:
            write(f"Path calculation error: {exc}")
            continue
        except Exception as exc:  # unexpected failures must not terminate the session
            write(f"Unexpected error while processing query: {exc}")
            continue

        for notice in notices:
            write(notice)
        write(report.content)

        if args.output_file:
            try:
                path = export_report(report, args.output_file)
                write(f"Result exported to {path}")
            except OSError as exc:
                write(f"Error: could not write output file: {exc}")

        successes += 1
        write("")
    write("Goodbye.")
    return successes


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point of the CLI. Returns a process exit code."""
    args = parse_arguments(argv)

    try:
        network = SubwayNetwork(data_path=DATA_FILE_PATH)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: could not load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        result = network.check_integrity()
        print("Data integrity check")
        print("=" * 40)
        print(f"Stations: {len(network.name_to_number)}, connections: {network.graph.edge_count}")
        if result["errors"]:
            print("Errors:")
            for message in result["errors"]:
                print(f"  - {message}")
        else:
            print("Errors: none")
        if result["warnings"]:
            print("Warnings:")
            for message in result["warnings"]:
                print(f"  - {message}")
        else:
            print("Warnings: none")
        return 1 if result["errors"] else 0

    errors = validate_arguments(args, network)
    if errors:
        for message in errors:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    interactive_loop(network, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
