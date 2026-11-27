"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import sys
from typing import Callable, List, Optional, Tuple

from data_loader import DataLoadError, load_subway_data
from fare_calculator import FareCalculationError
from integrity import check_data_integrity
from network import SubwayNetwork
from pathfinding import MODES, MODE_SHORTEST_DISTANCE, NoPathError, PathCalculationError, PathfindingConfig
from report import PathResult, build_path_result, export_result, render

PROMPT = "Enter route as 'Starting Station; Ending Station' (or 'quit' to exit): "
EXIT_COMMANDS = ("q", "quit", "exit")


class InputFormatError(ValueError):
    """Raised when a query does not follow the 'Start; End' format."""


class StationNotFoundError(ValueError):
    """Raised when a station name does not exist in the network."""


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("--max_transfers must be non-negative")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="beijing_subway_fare",
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="append query results to this file")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity check and exit")
    return parser


def parse_query(text: str) -> Tuple[str, str]:
    """Split a 'Starting Station; Ending Station' query into two raw names.

    Raises:
        InputFormatError: if the separator is missing or a name is empty.
    """
    message = "Input format incorrect, please use 'Starting Station; Ending Station' format"
    if ";" not in text:
        raise InputFormatError(message)
    parts = text.split(";")
    if len(parts) != 2:
        raise InputFormatError(message)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise InputFormatError(message)
    return start, end


def process_query(network: SubwayNetwork, text: str, config: PathfindingConfig) -> PathResult:
    """Validate a raw query string and compute its route summary.

    Raises:
        InputFormatError, StationNotFoundError, ValueError (logical errors),
        NoPathError, PathCalculationError, FareCalculationError.
    """
    raw_start, raw_end = parse_query(text)
    start = network.resolve_station(raw_start)
    if start is None:
        raise StationNotFoundError(
            f"Starting station '{raw_start}' does not exist, please check the station name"
        )
    end = network.resolve_station(raw_end)
    if end is None:
        raise StationNotFoundError(
            f"Ending station '{raw_end}' does not exist, please check the station name"
        )
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    return build_path_result(network, start, end, config)


def resolve_preferences(network: SubwayNetwork, raw: Optional[str]) -> List[str]:
    """Resolve the --line_preference argument into canonical line names.

    Raises:
        ValueError: if a line name is unknown.
    """
    if not raw:
        return []
    resolved: List[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        line = network.resolve_line(part)
        if line is None:
            raise ValueError(f"Unknown line '{part}' in --line_preference")
        resolved.append(line)
    return resolved


def run_interactive(network: SubwayNetwork, config: PathfindingConfig, args,
                    input_func: Callable[[str], str] = input,
                    output_func: Callable[[str], None] = print) -> int:
    """Run the continuous query loop until the user quits or input ends."""
    while True:
        try:
            raw = input_func(PROMPT)
        except (EOFError, KeyboardInterrupt):
            output_func("")
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            result = process_query(network, text, config)
        except InputFormatError as exc:
            output_func(f"Error: {exc}")
            continue
        except StationNotFoundError as exc:
            output_func(f"Error: {exc}")
            continue
        except ValueError as exc:
            output_func(f"Error: {exc}")
            continue
        except NoPathError as exc:
            output_func(f"Error: {exc}")
            continue
        except PathCalculationError as exc:
            output_func(f"Error: {exc}")
            continue
        except FareCalculationError as exc:
            output_func(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort protection for long-running sessions
            output_func(f"Error: unexpected failure while processing query: {exc}")
            continue

        output_func(render(result, args.format))

        if args.output_file:
            try:
                export_result(result, args.format, args.output_file)
                output_func(f"Result appended to {args.output_file}")
            except OSError as exc:
                output_func(f"Warning: could not write output file: {exc}")
    return 0


def main(argv: Optional[List[str]] = None, input_func: Callable[[str], str] = input) -> int:
    """Entry point for the CLI.

    Returns:
        Process exit code (0 on success, non-zero on failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data()
        network = SubwayNetwork.from_data(data)
    except (DataLoadError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}")
        return 1

    if args.check_data:
        report = check_data_integrity(network)
        print(report.format())
        return 0 if report.ok else 1

    try:
        preferred = resolve_preferences(network, args.line_preference)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {config.mode}"
          + (f", max transfers: {config.max_transfers}" if config.max_transfers is not None else "")
          + (f", preferred lines: {', '.join(config.preferred_lines)}" if config.preferred_lines else ""))
    return run_interactive(network, config, args, input_func=input_func)


if __name__ == "__main__":
    sys.exit(main())
