"""Command-line interface for the Beijing Subway fare calculation system."""
import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from errors import InputFormatError, InvalidQueryError, SubwayError
from pathfinding import SUPPORTED_MODES, PathfindingConfig
from reporting import render_report, write_report_file
from subway_network import SubwayNetwork, normalize_station_name

# Accepted separators between the starting and ending station.
_PAIR_SEPARATORS = re.compile(r"\s*[;；,，]\s*")
_EXIT_WORDS = ("q", "quit", "exit")
_FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def _non_negative_int(text):
    """argparse type: parse a non-negative integer."""
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return value


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="subway_fare",
        description="Beijing Subway route and fare calculator (Dijkstra-based).",
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="write the query result to this file (the latest result is kept)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: text (default) or json",
    )
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="shortest_distance",
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="maximum number of allowed transfers (default: unlimited)",
    )
    parser.add_argument(
        "--line_preference",
        default=None,
        help="preferred line(s), e.g. 'Line 1' or 'Line 1,Line 2'",
    )
    parser.add_argument(
        "--check_data",
        action="store_true",
        help="run the data integrity check and exit",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="run one query non-interactively, e.g. 'Start; End'",
    )
    return parser.parse_args(argv)


def parse_station_pair(text):
    """Split 'Starting Station; Ending Station' into two station names.

    Raises:
        InputFormatError: if the text does not contain exactly two non-empty parts.
    """
    if text is None:
        raise InputFormatError(_FORMAT_ERROR)
    parts = [p.strip() for p in _PAIR_SEPARATORS.split(text.strip())]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InputFormatError(_FORMAT_ERROR)
    return parts[0], parts[1]


def parse_line_preference(text, network):
    """Convert a comma-separated preference string into official line names.

    Raises:
        InvalidQueryError: if a named line does not exist in the network.
    """
    if text is None or not text.strip():
        return []
    result = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        key = normalize_station_name(part)
        match = None
        for line in network.line_names():
            if normalize_station_name(line) == key:
                match = line
                break
        if match is None:
            raise InvalidQueryError(
                "Unknown line preference '{}'. Available lines: {}".format(
                    part, ", ".join(network.line_names())
                )
            )
        if match not in result:
            result.append(match)
    return result


def run_query(network, text, config):
    """Parse a query string and compute the route for it."""
    start_text, end_text = parse_station_pair(text)
    return network.find_route(start_text, end_text, config)


def process_query(network, text, config, fmt, output_file):
    """Execute one query, print the report and optionally save it.

    Returns:
        True on success, False if an error was reported.
    """
    try:
        route = run_query(network, text, config)
        content = render_report(route, fmt)
    except SubwayError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return False
    except Exception as exc:  # defensive: never crash the interactive session
        print("Unexpected error while processing query: {}".format(exc), file=sys.stderr)
        return False

    print(content)
    if output_file:
        try:
            write_report_file(output_file, content)
            print("Report saved to {}".format(output_file))
        except SubwayError as exc:
            print("Error: {}".format(exc), file=sys.stderr)
            return False
    return True


def interactive_loop(network, config, fmt, output_file):
    """Read and answer queries until the user quits or input ends."""
    print("Beijing Subway fare calculator")
    print("Enter 'Starting Station; Ending Station' to query, or 'q' to quit.")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.lower() in _EXIT_WORDS:
            break
        process_query(network, stripped, config, fmt, output_file)
    return 0


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        data = load_subway_data(DATA_FILE_PATH)
        network = SubwayNetwork(data)
    except SubwayError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1

    if args.check_data:
        issues = network.check_integrity()
        if issues:
            print("Data integrity check found {} issue(s):".format(len(issues)))
            for issue in issues:
                print("  - {}".format(issue))
            return 1
        print("Data integrity check passed.")
        return 0

    try:
        preferred = parse_line_preference(args.line_preference, network)
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except (SubwayError, ValueError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 2

    if args.query is not None:
        ok = process_query(network, args.query, config, args.format, args.output_file)
        return 0 if ok else 1

    return interactive_loop(network, config, args.format, args.output_file)
