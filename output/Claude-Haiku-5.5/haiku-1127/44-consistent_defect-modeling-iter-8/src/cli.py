"""Command-line interface of the Beijing Subway fare calculation system.

Usage examples:
    python src/main.py
    python src/main.py --mode least_transfer --max_transfers 2 --format json
    python src/main.py --output_file result.txt --line_preference "Line 1"
    python src/main.py --check_data
"""

import argparse
import difflib
import re
from dataclasses import dataclass
from typing import Optional

from data_checker import DataIntegrityChecker
from fare_calculator import Sum_money
from models import line_matches
from network import StationNotFoundError, SubwayNetwork
from path_report import build_summary, render_json, render_text
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
    ShortestPath,
)

FORMAT_CHOICES = ("text", "json")
EXIT_WORDS = ("quit", "exit", "q")


class InputFormatError(ValueError):
    """Raised when a query string does not follow the 'Start; End' format."""


class LogicValidationError(ValueError):
    """Raised when a query is logically invalid (e.g. identical start and end)."""


@dataclass
class QueryOptions:
    """Options that apply to every query of a session."""

    mode: str = MODE_SHORTEST_DISTANCE
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None
    output_format: str = "text"
    output_file: Optional[str] = None


def _non_negative_int(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based route planner)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Write the result of each query to this file (overwritten on every query).",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=FORMAT_CHOICES,
        default="text",
        help="Output format: text or json (default: text).",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=MODE_SHORTEST_DISTANCE,
        help="Path query mode (default: shortest_distance).",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="Maximum number of transfers allowed.",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help='Preferred line, e.g. "Line 1".',
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="Run the data integrity check and exit.",
    )
    return parser


def parse_query_text(text) -> tuple:
    """Split a 'Starting Station; Ending Station' query into two names.

    Accepts ';' or ',' (and their full-width forms) as separator.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    parts = re.split(r"[;,；，]", text.strip())
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )
    return parts[0].strip(), parts[1].strip()


def _normalize_name(name) -> str:
    text = re.sub(r"\s+", "", name).lower()
    if len(text) > 1 and text.endswith("站"):
        text = text[:-1]
    return text


def resolve_station(network: SubwayNetwork, raw_name: str, label: str) -> tuple:
    """Resolve a user-entered station name to an official station name.

    Exact names are accepted directly. Otherwise a normalized match is tried,
    then the nearest name by string similarity.

    Returns:
        (official station name, True if the name was changed by matching).

    Raises:
        StationNotFoundError: If no station is close enough.
    """
    if network.has_station(raw_name):
        return raw_name, False
    candidates = {}
    for name in network.station_names():
        candidates.setdefault(_normalize_name(name), name)
    key = _normalize_name(raw_name)
    if key in candidates:
        return candidates[key], True
    close = difflib.get_close_matches(key, list(candidates), n=1, cutoff=0.6)
    if close:
        return candidates[close[0]], True
    raise StationNotFoundError(
        f"{label} station '{raw_name}' does not exist, please check the station name"
    )


def run_query(network: SubwayNetwork, text: str, options: QueryOptions) -> tuple:
    """Execute one query and return (report text, list of notes).

    Raises:
        InputFormatError, LogicValidationError, StationNotFoundError,
        PathNotFoundError, RuntimeError (calculation failures).
    """
    start_raw, end_raw = parse_query_text(text)
    notes = []
    start, start_changed = resolve_station(network, start_raw, "Starting")
    if start_changed:
        notes.append(f"Matched starting station '{start_raw}' to '{start}'")
    end, end_changed = resolve_station(network, end_raw, "Ending")
    if end_changed:
        notes.append(f"Matched ending station '{end_raw}' to '{end}'")
    if start == end:
        raise LogicValidationError("Starting station cannot be the same as the ending station")

    try:
        preferred = [options.line_preference] if options.line_preference else []
        config = PathfindingConfig(
            mode=options.mode,
            max_transfers=options.max_transfers,
            preferred_lines=preferred,
        )
        finder = ShortestPath(network.graph, network.get_number(start), config)
        route = finder.route_to(network.get_number(end))
    except PathNotFoundError:
        raise
    except Exception as exc:  # defensive: unexpected algorithm failure
        raise RuntimeError(f"Path calculation failed: {exc}") from exc

    try:
        fare = Sum_money(route.total_distance)
    except Exception as exc:  # defensive: fare calculation failure
        raise RuntimeError(f"Fare calculation failed: {exc}") from exc

    summary = build_summary(route, fare)
    query_info = {
        "start": start,
        "end": end,
        "mode": options.mode,
        "max_transfers": options.max_transfers,
        "line_preference": options.line_preference,
    }
    name_of = network.get_name
    if options.output_format == "json":
        report = render_json(query_info, route, summary, name_of)
    else:
        report = render_text(query_info, route, summary, name_of)
    return report, notes


def interactive_session(network, options, input_func=input, out=print) -> int:
    """Run the continuous query loop until the user quits or input ends."""
    out("Beijing Subway fare query. Enter 'Starting Station; Ending Station' ('quit' to exit).")
    while True:
        try:
            raw = input_func("> ")
        except (EOFError, KeyboardInterrupt):
            out("")
            break
        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            report, notes = run_query(network, text, options)
        except (InputFormatError, LogicValidationError, StationNotFoundError,
                PathNotFoundError, RuntimeError) as exc:
            out(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive catch-all keeps the session alive
            out(f"Unexpected error: {exc}")
            continue
        for note in notes:
            out(note)
        out(report)
        if options.output_file:
            try:
                with open(options.output_file, "w", encoding="utf-8") as handle:
                    handle.write(report + "\n")
                out(f"Result written to {options.output_file}")
            except OSError as exc:
                out(f"Could not write output file: {exc}")
    return 0


def main(argv=None, input_func=input, out=print) -> int:
    """Entry point of the CLI. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork.from_file()
    except (OSError, ValueError) as exc:
        out(f"Failed to load subway data: {exc}")
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(network)
        passed = checker.run()
        out(checker.report())
        return 0 if passed else 1

    if args.line_preference and not any(
        line_matches(args.line_preference, line) for line in network.line_names()
    ):
        out(f"Warning: line '{args.line_preference}' is not a known line; preference will have no effect.")

    options = QueryOptions(
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=args.line_preference,
        output_format=args.output_format,
        output_file=args.output_file,
    )
    return interactive_session(network, options, input_func=input_func, out=out)
