"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import re
import sys

try:
    from .data_loader import DataLoadError, DATA_FILE_PATH
    from .network import SubwayNetwork, NetworkError, LineNotFoundError, StationNotFoundError
    from .data_integrity import DataIntegrityChecker
    from .pathfinding import PathfindingConfig, VALID_MODES, MODE_SHORTEST_DISTANCE
    from .query_service import PathQueryService, QueryError, PathNotFoundError
    from .path_report import render_report, write_report, ReportError
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from data_loader import DataLoadError, DATA_FILE_PATH
    from network import SubwayNetwork, NetworkError, LineNotFoundError, StationNotFoundError
    from data_integrity import DataIntegrityChecker
    from pathfinding import PathfindingConfig, VALID_MODES, MODE_SHORTEST_DISTANCE
    from query_service import PathQueryService, QueryError, PathNotFoundError
    from path_report import render_report, write_report, ReportError


INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
SEPARATOR_PATTERN = re.compile(r"\s*[;；,，]\s*")
EXIT_COMMANDS = ("quit", "exit", "q")
HELP_COMMANDS = ("help", "?")


class InputFormatError(Exception):
    """Raised when a query line does not follow the 'Start; End' format."""


def parse_query_input(text):
    """Split a user query line into ``(start, end)`` station names.

    Accepted separators are ``;``, ``,`` and their full-width forms.

    Raises:
        InputFormatError: If the line does not contain exactly two station names.
    """
    stripped = str(text).strip()
    if not stripped:
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    parts = SEPARATOR_PATTERN.split(stripped)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


class CommandLineInterface:
    """Interactive query loop supporting continuous queries.

    Attributes:
        continuousMode: If True the loop keeps asking for queries until exit.
        prompt: Prompt string shown before each query.
    """

    def __init__(self, service, config, fmt="text", output_file=None,
                 input_func=input, output_func=print):
        self.service = service
        self.config = config
        self.format = fmt
        self.output_file = output_file
        self.continuousMode = True
        self.prompt = "Query ('Starting Station; Ending Station', 'help', 'quit'): "
        self._input = input_func
        self._output = output_func
        self._has_written = False

    def handle_query(self, text):
        """Process one query line and return the rendered report.

        Raises:
            InputFormatError, StationNotFoundError, QueryError,
            PathNotFoundError, ReportError: on user or calculation errors.
        """
        start, end = parse_query_input(text)
        result = self.service.query(start, end, self.config)
        return render_report(result, self.format)

    def _print_help(self):
        self._output("Enter a query in the form 'Starting Station; Ending Station'.")
        self._output("Separators ';' and ',' are accepted. Commands: help, quit.")

    def run(self):
        """Run the interactive loop. Returns the process exit code."""
        self._output("Beijing Subway Fare Calculation System")
        self._print_help()
        while True:
            try:
                line = self._input(self.prompt)
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
            command = line.strip()
            if not command:
                continue
            lowered = command.lower()
            if lowered in EXIT_COMMANDS:
                break
            if lowered in HELP_COMMANDS:
                self._print_help()
                continue
            try:
                content = self.handle_query(command)
            except InputFormatError as exc:
                self._output(f"Error: {exc}")
                continue
            except StationNotFoundError as exc:
                self._output(f"Error: {exc}")
                continue
            except PathNotFoundError as exc:
                self._output(f"Error: {exc}")
                continue
            except QueryError as exc:
                self._output(f"Error: {exc}")
                continue
            except Exception as exc:  # last-resort guard keeps the session alive
                self._output(f"Error: unexpected failure while answering the query: {exc}")
                continue

            self._output(content)
            if self.output_file:
                try:
                    write_report(content, self.output_file, append=self._has_written)
                    self._has_written = True
                    self._output(f"Result written to {self.output_file}")
                except ReportError as exc:
                    self._output(f"Error: {exc}")
            if not self.continuousMode:
                break
        return 0


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI).",
    )
    parser.add_argument("--output_file", default=None,
                        help="export query results to this file")
    parser.add_argument("--format", dest="format", choices=("text", "json"), default="text",
                        help="output format: text or json (default: text)")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_SHORTEST_DISTANCE,
                        help="path query mode (default: shortest_distance)")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="maximum number of allowed transfers")
    parser.add_argument("--line_preference", default=None,
                        help="preferred line, e.g. 'Line 1'")
    parser.add_argument("--check_data", action="store_true",
                        help="run data integrity checks and exit")
    return parser


def build_config(args, network):
    """Create a ``PathfindingConfig`` from command-line arguments."""
    preferred = []
    if args.line_preference:
        preferred.append(network.resolve_line(args.line_preference))
    return PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                             preferred_lines=preferred)


def main(argv=None):
    """Program entry point. Returns the process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be a non-negative integer")

    try:
        network = SubwayNetwork.from_file(DATA_FILE_PATH)
    except (DataLoadError, NetworkError, KeyError, TypeError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        report = DataIntegrityChecker(network).run()
        print(report.render())
        return 0 if report.passed else 1

    try:
        config = build_config(args, network)
    except (LineNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    for warning in network.load_warnings:
        print(f"Warning while loading data: {warning}", file=sys.stderr)

    service = PathQueryService(network)
    cli = CommandLineInterface(service, config, fmt=args.format, output_file=args.output_file)
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
