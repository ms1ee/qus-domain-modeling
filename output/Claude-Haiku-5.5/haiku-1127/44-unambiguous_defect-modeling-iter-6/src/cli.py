"""Command-line interface: argument parsing and interactive query session."""

import argparse
import json
import os
import sys
from typing import Callable, List, Optional, Sequence

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from data_loader import DataLoadError, build_network, load_subway_data  # noqa: E402
from input_validator import InputValidationError, InputValidator  # noqa: E402
from integrity_checker import DataIntegrityChecker  # noqa: E402
from models import SubwayNetwork  # noqa: E402
from pathfinding import (  # noqa: E402
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    PathNotFoundError,
    ShortestPath,
)
from reporting import (  # noqa: E402
    FORMAT_JSON,
    FORMAT_TEXT,
    SUPPORTED_FORMATS,
    format_route_text,
    render_reports,
    route_to_dict,
    write_report_file,
)
from route import Query, Route, build_route  # noqa: E402

EXIT_WORDS = ("q", "quit", "exit")


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (interactive CLI)."
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", dest="format", choices=SUPPORTED_FORMATS, default=FORMAT_TEXT,
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=_non_negative_int, default=None,
                        help="maximum number of transfers allowed (default: unlimited)")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line name, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run the data integrity check and exit")
    return parser


def resolve_line_preference(value: str, line_names: Sequence[str]) -> str:
    """Return the canonical line name matching ``value`` (case-insensitive).

    Raises:
        ValueError: if no such line exists.
    """
    wanted = value.strip().casefold()
    for line in line_names:
        if line.casefold() == wanted:
            return line
    raise ValueError(f"Unknown line '{value}'. Available lines: {', '.join(line_names)}")


class QuerySession:
    """Interactive loop that answers fare/path queries."""

    def __init__(
        self,
        network: SubwayNetwork,
        config: PathfindingConfig,
        output_format: str,
        output_file: Optional[str],
        input_func: Callable[[str], str] = input,
        out: Callable[[str], None] = print,
    ) -> None:
        self._network = network
        self._config = config
        self._format = output_format
        self._output_file = output_file
        self._input = input_func
        self._out = out
        self._validator = InputValidator(network.station_names())
        self._routes: List[Route] = []

    def run(self) -> int:
        """Run the query loop until the user quits or input ends."""
        self._out("Beijing Subway fare calculator.")
        self._out("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
        while True:
            try:
                line = self._input("> ")
            except (EOFError, KeyboardInterrupt):
                self._out("")
                break
            text = line.strip()
            if not text:
                continue
            if text.lower() in EXIT_WORDS:
                break
            self.handle_query(text)
        if self._output_file and not self._routes:
            self._export()
        return 0

    def handle_query(self, text: str) -> Optional[Route]:
        """Validate, compute and display one query. Returns the Route or None."""
        try:
            raw_start, raw_end = self._validator.parse(text)
            start = self._validator.resolve(raw_start, "Starting")
            end = self._validator.resolve(raw_end, "Ending")
            self._validator.validate_pair(start, end)
        except InputValidationError as exc:
            self._out(f"Error: {exc}")
            return None

        query = Query(
            start_station=start,
            end_station=end,
            mode=self._config.mode,
            max_transfers=self._config.max_transfers,
            line_preference=self._config.preferred_lines[0] if self._config.preferred_lines else None,
        )

        try:
            source = self._network.number_of(start)
            target = self._network.number_of(end)
            finder = ShortestPath(self._network.graph, source, self._config)
            station_numbers, edges = finder.path_with_edges(target)
        except PathNotFoundError as exc:
            self._out(f"Error: {exc}. Try relaxing --max_transfers or --line_preference.")
            return None
        except Exception as exc:  # defensive: unexpected path calculation failure
            self._out(f"Error: path calculation failed: {exc}")
            return None

        try:
            route = build_route(self._network, query, station_numbers, edges)
        except (ValueError, ArithmeticError) as exc:
            self._out(f"Error: fare calculation failed: {exc}")
            return None

        if self._format == FORMAT_JSON:
            self._out(json.dumps(route_to_dict(route), ensure_ascii=False, indent=2))
        else:
            self._out(format_route_text(route))

        self._routes.append(route)
        if self._output_file:
            self._export()
        return route

    def _export(self) -> None:
        try:
            content = render_reports(self._routes, self._format)
            write_report_file(self._output_file, content)
            self._out(f"Results exported to {self._output_file}")
        except OSError as exc:
            self._out(f"Error: cannot write output file: {exc}")


def run(argv: Optional[Sequence[str]] = None, input_func: Callable[[str], str] = input,
        out: Callable[[str], None] = print) -> int:
    """Entry point logic shared by the script and tests. Returns an exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data()
    except DataLoadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    network = build_network(data)

    if args.check_data:
        report = DataIntegrityChecker().check(data, network)
        out(report.to_text())
        return 0 if report.ok else 1

    preferred: List[str] = []
    if args.line_preference:
        try:
            preferred.append(resolve_line_preference(args.line_preference, network.line_names))
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    session = QuerySession(network, config, args.format, args.output_file, input_func, out)
    return session.run()
