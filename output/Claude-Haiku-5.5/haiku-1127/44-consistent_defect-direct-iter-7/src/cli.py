"""Command-line interface for the Beijing Subway fare calculation system."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence

from src.path_report import PathResult, render_json, render_text
from src.pathfinding import MODE_SHORTEST_DISTANCE, VALID_MODES, PathfindingConfig
from src.query_service import QueryError, run_query
from src.subway_network import SubwayNetwork

EXIT_WORDS = {"quit", "exit", "q"}


def _non_negative_int(value: str) -> int:
    """argparse type: a non-negative integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return number


def parse_line_preference(value: Optional[str]) -> List[str]:
    """Split a comma-separated --line_preference value into line names."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (interactive CLI)."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="export the query results of this session to the given file",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format: text (default) or json",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default=MODE_SHORTEST_DISTANCE,
        help="path query mode (default: shortest_distance)",
    )
    parser.add_argument(
        "--max_transfers",
        type=_non_negative_int,
        default=None,
        help="maximum number of transfers allowed",
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
    return parser


def _write_output_file(path: str, results: Sequence[PathResult], fmt: str) -> None:
    """Write all results of the session to ``path`` (overwriting previous content)."""
    if fmt == "json":
        content = json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2)
    else:
        content = "\n\n".join(render_text(result) for result in results)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        network = SubwayNetwork()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=sys.stderr)
        return 1

    if args.check_data:
        passed, messages = network.check_data()
        for message in messages:
            print(message)
        print("Data check PASSED" if passed else "Data check FAILED")
        return 0 if passed else 1

    preferred = parse_line_preference(args.line_preference)
    known_lines = set(network.lines())
    for line in preferred:
        if line not in known_lines:
            print(f"Warning: line '{line}' is not present in the dataset")

    try:
        config = PathfindingConfig(
            mode=args.mode,
            max_transfers=args.max_transfers,
            preferred_lines=preferred,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print("Beijing Subway Fare Calculator")
    print(f"Mode: {config.mode}" + (f", max transfers: {config.max_transfers}" if config.max_transfers is not None else ""))
    print("Enter 'Starting Station; Ending Station' (or 'quit' to exit).")

    session: List[PathResult] = []
    while True:
        try:
            raw = input("\nQuery> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        text = raw.strip()
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break

        try:
            result = run_query(network, text, config)
        except QueryError as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # defensive: never crash the interactive loop
            print(f"Unexpected error while processing query: {exc}")
            continue

        session.append(result)
        if args.format == "json":
            print(render_json(result))
        else:
            print(render_text(result))

        if args.output_file:
            try:
                _write_output_file(args.output_file, session, args.format)
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")

    print("Goodbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
