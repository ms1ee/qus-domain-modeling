"""Command-line interface for the Beijing Subway fare calculation system."""

from __future__ import annotations

import argparse
import sys
from typing import Any, List, Optional, TextIO, Tuple

from data_loader import load_subway_data
from data_manager import DataManager
from pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig
from query_service import SubwayError, SubwayService
from report import format_json, format_text

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"
EXIT_COMMANDS = ("quit", "exit", "q")
WELCOME_MESSAGE = (
    "Beijing Subway Fare Calculator\n"
    "Enter 'Starting Station; Ending Station' to query (or 'quit' to exit)."
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (Dijkstra-based)."
    )
    parser.add_argument("--output_file", default=None,
                        help="Write query results to this file.")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text).")
    parser.add_argument("--mode", choices=list(VALID_MODES), default=MODE_SHORTEST_DISTANCE,
                        help="Path query mode (default: shortest_distance).")
    parser.add_argument("--max_transfers", type=int, default=None,
                        help="Maximum number of allowed transfers.")
    parser.add_argument("--line_preference", default=None,
                        help="Preferred line(s), comma separated, e.g. 'Line 1'.")
    parser.add_argument("--check_data", action="store_true",
                        help="Run the data integrity check and exit.")
    return parser


def parse_query_input(text: str) -> Tuple[str, str]:
    """Split 'Starting Station; Ending Station' into its two parts.

    Raises:
        ValueError: If the input does not match the required format.
    """
    parts = text.split(";")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError(INPUT_FORMAT_MESSAGE)
    return parts[0].strip(), parts[1].strip()


def _parse_line_preference(text: Optional[str], service: SubwayService) -> List[str]:
    """Resolve the comma-separated --line_preference value to official lines."""
    if not text:
        return []
    result: List[str] = []
    for item in text.split(","):
        item = item.strip()
        if item:
            result.append(service.resolve_line(item))
    return result


def _render(result: Any, fmt: str) -> str:
    return format_text(result) if fmt == "text" else format_json(result)


def _write_output_file(path: str, content: str, append: bool) -> None:
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as handle:
        handle.write(content + "\n")


def interactive_loop(
    service: SubwayService,
    config: PathfindingConfig,
    fmt: str,
    output_file: Optional[str],
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    """Read queries until 'quit' or end of input, answering each one."""
    file_started = False
    while True:
        stdout.write("\nQuery> ")
        stdout.flush()
        raw = stdin.readline()
        if raw == "":
            stdout.write("\n")
            break
        line = raw.strip()
        if not line:
            continue
        if line.lower() in EXIT_COMMANDS:
            break

        try:
            start_text, end_text = parse_query_input(line)
            result = service.query(start_text, end_text, config)
            rendered = _render(result, fmt)
        except ValueError as exc:
            stderr.write(f"Error: {exc}\n")
            continue
        except SubwayError as exc:
            stderr.write(f"Error: {exc}\n")
            continue
        except Exception as exc:  # pragma: no cover - safety net
            stderr.write(f"Error: unexpected failure while answering query: {exc}\n")
            continue

        stdout.write(rendered + "\n")
        stdout.flush()

        if output_file:
            try:
                _write_output_file(output_file, rendered, append=file_started)
                file_started = True
            except OSError as exc:
                stderr.write(f"Error: could not write output file '{output_file}': {exc}\n")


def main(
    argv: Optional[List[str]] = None,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    """Entry point. Returns the process exit code."""
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        data = load_subway_data()
    except (OSError, ValueError) as exc:
        stderr.write(f"Error: failed to load subway data: {exc}\n")
        return 1

    if args.check_data:
        issues = DataManager(data).check_integrity()
        if not issues:
            stdout.write("Data integrity check passed.\n")
            return 0
        stdout.write(f"Data integrity check found {len(issues)} issue(s):\n")
        for issue in issues:
            stdout.write(f"  - {issue}\n")
        return 1

    if args.max_transfers is not None and args.max_transfers < 0:
        stderr.write("Error: --max_transfers must be non-negative\n")
        return 2

    try:
        service = SubwayService(data)
    except (ValueError, KeyError) as exc:
        stderr.write(f"Error: failed to build subway network: {exc}\n")
        return 1

    try:
        preferred = _parse_line_preference(args.line_preference, service)
    except ValueError as exc:
        stderr.write(f"Error: {exc}\n")
        return 2

    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    try:
        config.validate()
    except ValueError as exc:
        stderr.write(f"Error: {exc}\n")
        return 2

    stdout.write(WELCOME_MESSAGE + "\n")
    interactive_loop(service, config, args.format, args.output_file, stdin, stdout, stderr)
    return 0
