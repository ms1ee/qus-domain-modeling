"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re

from data_check import format_integrity_report, run_integrity_checks
from data_loader import DATA_FILE_PATH, DataLoadError
from network import SubwayNetwork
from pathfinding import VALID_MODES, PathfindingConfig, ShortestPath
from route_report import build_route_result, format_json, format_text

INPUT_FORMAT_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)
_SEPARATOR_RE = re.compile(r"\s*[;\uff1b,\uff0c]\s*")

HELP_TEXT = """Commands:
  <Start>; <End>      Query the route and fare, e.g. "Xizhimen; Dongzhimen"
  mode <name>         Change query mode: shortest_distance, least_transfer, comprehensive
  lines               List all subway lines
  help                Show this help
  quit                Exit the program"""


class QueryError(Exception):
    """A user-facing error in a query (input, station, or calculation)."""


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Beijing Subway fare calculation system")
    parser.add_argument("--output_file", default=None,
                        help="file that receives the most recent query result")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default="shortest_distance",
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line(s), comma separated, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser.parse_args(argv)


def parse_query(text):
    """Split a 'Starting Station; Ending Station' input into two names."""
    parts = [p.strip() for p in _SEPARATOR_RE.split(text.strip())]
    if len(parts) != 2 or not all(parts):
        raise QueryError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def resolve_station(network, name, role):
    """Standardize a station name and verify that it exists."""
    canonical = network.standardize_station_name(name)
    if canonical is None:
        raise QueryError(f"{role} station '{name}' does not exist, please check the station name")
    return canonical


def normalize_line_name(token, known_lines):
    """Map user input such as '1' or 'line 1' to a known line name."""
    text = " ".join(token.split())
    if re.fullmatch(r"\d+", text):
        text = f"Line {text}"
    for known in known_lines:
        if known.casefold() == text.casefold():
            return known
    raise QueryError(f"Unknown line '{token.strip()}' for --line_preference")


def parse_preferences(text, known_lines):
    """Parse a comma-separated line preference string."""
    if not text:
        return []
    result = []
    for token in text.split(","):
        if token.strip():
            name = normalize_line_name(token, known_lines)
            if name not in result:
                result.append(name)
    return result


def run_query(network, start, end, config):
    """Compute the route between two official station names.

    Returns:
        The route result dictionary built by ``build_route_result``.

    Raises:
        QueryError: If no path exists or path calculation fails.
    """
    try:
        source = network.number_of(start)
        target = network.number_of(end)
        searcher = ShortestPath(network.graph, source, config)
        if not searcher.has_path(target):
            raise QueryError(
                f"No route found from '{start}' to '{end}' with the current settings")
        stations, edges = searcher.path_with_edges(target)
        transfers = searcher.get_transfer_count(target)
    except (KeyError, ValueError) as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    return build_route_result(network, start, end, config.mode, stations, edges,
                              transfers, config.max_transfers, config.preferred_lines)


def render(result, output_format):
    """Render a result in the requested format."""
    if output_format == "json":
        return format_json(result)
    return format_text(result)


class QuerySession:
    """Interactive continuous-query session."""

    def __init__(self, network, config, output_format="text", output_file=None):
        self.network = network
        self.config = config
        self.output_format = output_format
        self.output_file = output_file

    def run(self):
        """Run the read-evaluate-print loop until the user quits."""
        print("Beijing Subway fare calculator. Type 'help' for commands.")
        while True:
            try:
                raw = input("Query> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            text = raw.strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in ("quit", "exit"):
                break
            if lowered == "help":
                print(HELP_TEXT)
            elif lowered == "lines":
                print(", ".join(self.network.all_lines()))
            elif lowered.startswith("mode"):
                self._change_mode(text)
            else:
                self._process_query(text)
        return 0

    def _change_mode(self, text):
        parts = text.split()
        if len(parts) != 2 or parts[1] not in VALID_MODES:
            print(f"Error: usage 'mode <{'|'.join(VALID_MODES)}>'")
            return
        self.config.mode = parts[1]
        print(f"Query mode set to {parts[1]}")

    def _process_query(self, text):
        try:
            start_raw, end_raw = parse_query(text)
            start = resolve_station(self.network, start_raw, "Starting")
            end = resolve_station(self.network, end_raw, "Ending")
            if start == end:
                raise QueryError("Starting station cannot be the same as the ending station")
            result = run_query(self.network, start, end, self.config)
        except QueryError as exc:
            print(f"Error: {exc}")
            return
        except Exception as exc:  # fare or other unexpected calculation failure
            print(f"Error: route or fare calculation failed: {exc}")
            return

        output = render(result, self.output_format)
        print(output)
        if self.output_file:
            try:
                with open(self.output_file, "w", encoding="utf-8") as handle:
                    handle.write(output + "\n")
                print(f"Result written to {self.output_file}")
            except OSError as exc:
                print(f"Error: unable to write output file: {exc}")


def main(argv=None):
    """Program entry point. Returns the process exit code."""
    args = parse_args(argv)

    try:
        network = SubwayNetwork(path=DATA_FILE_PATH)
    except (DataLoadError, KeyError, TypeError, ValueError) as exc:
        print(f"Error: unable to load subway data: {exc}")
        return 1

    if args.check_data:
        result = run_integrity_checks(network)
        print(format_integrity_report(result))
        return 1 if result["errors"] else 0

    if args.max_transfers is not None and args.max_transfers < 0:
        print("Error: --max_transfers must be a non-negative integer")
        return 2

    try:
        preferred = parse_preferences(args.line_preference, network.all_lines())
        config = PathfindingConfig(args.mode, args.max_transfers, preferred)
    except (QueryError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    session = QuerySession(network, config, args.format, args.output_file)
    return session.run()
