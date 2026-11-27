"""Command-line interface: argument parsing, input validation, continuous
query loop and error handling."""

import argparse
import re
import sys
from typing import List, Optional, Tuple

from .data_loader import DATA_FILE_PATH
from .fare_calculator import Sum_money  # noqa: F401  (fare module is used via report)
from .integrity import DataIntegrityChecker, line_key
from .models import Query
from .network import SubwayNetwork
from .pathfinding import VALID_MODES, NoPathError, find_route
from .report import build_summary, render_report, write_report

OUTPUT_FORMATS = ("text", "json")
EXIT_WORDS = ("quit", "exit", "q")
FORMAT_ERROR_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"[;,；，]")
PROMPT = "Enter 'Starting Station; Ending Station' (or 'quit' to exit): "


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (command-line interface)."
    )
    parser.add_argument(
        "--output_file", type=str, default=None,
        help="append each query result to this file",
    )
    parser.add_argument(
        "--format", choices=OUTPUT_FORMATS, default="text",
        help="output format: text or json (default: text)",
    )
    parser.add_argument(
        "--mode", choices=VALID_MODES, default="comprehensive",
        help="path query mode (default: comprehensive)",
    )
    parser.add_argument(
        "--max_transfers", type=int, default=None,
        help="maximum number of transfers allowed",
    )
    parser.add_argument(
        "--line_preference", type=str, default=None,
        help="preferred line, e.g. 'Line 1'",
    )
    parser.add_argument(
        "--check_data", action="store_true",
        help="run the data integrity check and exit",
    )
    return parser


def parse_query_text(text: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' input into two names.

    Raises:
        ValueError: If the input does not contain exactly two non-empty parts.
    """
    parts = SEPARATOR_PATTERN.split(text)
    if len(parts) != 2:
        raise ValueError(FORMAT_ERROR_MESSAGE)
    start, end = parts[0].strip(), parts[1].strip()
    if not start or not end:
        raise ValueError(FORMAT_ERROR_MESSAGE)
    return start, end


def resolve_station_name(network: SubwayNetwork, text: str, role: str) -> Tuple[str, Optional[str]]:
    """Standardise a station name; return (official name, optional notice).

    Raises:
        ValueError: If no station can be matched.
    """
    result = network.resolve_station(text)
    if result is None:
        raise ValueError(f"{role} station '{text}' does not exist, please check the station name")
    name, exact = result
    notice = None
    if not exact:
        notice = f"Note: {role.lower()} station '{text}' was matched to the nearest station '{name}'."
    return name, notice


def _canonical_line(network: SubwayNetwork, text: str) -> Optional[str]:
    """Map a user-entered line name to the official line name, or None."""
    lowered = text.strip().lower()
    for line in network.line_names():
        if line.lower() == lowered:
            return line
    key = line_key(text)
    for line in network.line_names():
        if line_key(line) == key:
            return line
    return None


def answer_query(network: SubwayNetwork, text: str, args) -> Tuple[str, List[str]]:
    """Process one query line and return (rendered report, notices).

    Raises:
        ValueError: For user input errors (format, unknown stations, same station,
            no route under the constraints).
        RuntimeError: For unexpected failures in path or fare calculation.
    """
    start_text, end_text = parse_query_text(text)
    start, notice_start = resolve_station_name(network, start_text, "Starting")
    end, notice_end = resolve_station_name(network, end_text, "Ending")
    notices = [n for n in (notice_start, notice_end) if n]
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")

    query = Query(
        start_station=start,
        end_station=end,
        mode=args.mode,
        max_transfers=args.max_transfers,
        line_preference=args.line_preference,
    )
    try:
        route = find_route(network, query)
    except NoPathError as exc:
        raise ValueError(
            f"No route found from '{start}' to '{end}' under the current constraints"
        ) from exc
    except ValueError:
        raise
    except Exception as exc:  # path calculation failure
        raise RuntimeError(f"Path calculation failed: {exc}") from exc

    try:
        summary = build_summary(route)
        rendered = render_report(args.format, query, route, summary)
    except Exception as exc:  # fare or rendering failure
        raise RuntimeError(f"Fare calculation failed: {exc}") from exc
    return rendered, notices


def run_session(network: SubwayNetwork, args) -> int:
    """Run the continuous query loop until the user quits or input ends."""
    while True:
        try:
            text = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        text = text.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            output, notices = answer_query(network, text, args)
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # last-resort guard so the session survives
            print(f"Error: unexpected failure while processing the query: {exc}")
            continue

        notice_stream = sys.stderr if args.format == "json" else sys.stdout
        for notice in notices:
            print(notice, file=notice_stream)
        print(output)

        if args.output_file:
            try:
                write_report(output + "\n", args.output_file, append=True)
            except OSError as exc:
                print(f"Warning: could not write output file: {exc}", file=sys.stderr)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point of the command-line program. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (OSError, ValueError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        checker = DataIntegrityChecker(network)
        passed = checker.run()
        print(checker.report())
        return 0 if passed else 1

    if args.line_preference:
        canonical = _canonical_line(network, args.line_preference)
        if canonical is None:
            print(
                f"Warning: line preference '{args.line_preference}' is not a known line; "
                "it will have no effect.",
                file=sys.stderr,
            )
        args.line_preference = canonical or args.line_preference

    print("Beijing Subway Fare Calculation System")
    print(f"Mode: {args.mode} | Format: {args.format}"
          + (f" | Max transfers: {args.max_transfers}" if args.max_transfers is not None else "")
          + (f" | Line preference: {args.line_preference}" if args.line_preference else ""))
    return run_session(network, args)
