"""Command-line interface for the Beijing Subway fare calculation system."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence, TextIO, Tuple

from data_integrity import check_network
from data_loader import DATA_FILE_PATH, load_subway_data
from errors import DataError, InputFormatError, QueryError, SubwayError
from network import SubwayNetwork, build_network
from pathfinding import (
    VALID_MODES,
    MODE_COMPREHENSIVE,
    PathfindingConfig,
    normalize_line_name,
)
from report import build_path_result, render_json, render_text

QUERY_SEPARATORS = (";", "；", ",", "，")
EXIT_COMMANDS = {"q", "quit", "exit"}
BANNER = (
    "Beijing Subway Fare Calculator\n"
    "Enter 'Starting Station; Ending Station' to query a route, "
    "or 'quit' to exit."
)


def parse_query(text: str) -> Tuple[str, str]:
    """Split a query of the form 'Starting Station; Ending Station'."""
    positions = [i for i, ch in enumerate(text) if ch in QUERY_SEPARATORS]
    if len(positions) != 1:
        raise InputFormatError()
    pos = positions[0]
    start = text[:pos].strip()
    end = text[pos + 1 :].strip()
    if not start or not end:
        raise InputFormatError()
    return start, end


def resolve_stations(
    network: SubwayNetwork, start_raw: str, end_raw: str
) -> Tuple[str, str]:
    """Standardise and validate both station names."""
    start = network.require_station(start_raw, "Starting")
    end = network.require_station(end_raw, "Ending")
    if start == end:
        raise QueryError("Starting station cannot be the same as the ending station")
    return start, end


def run_query(
    network: SubwayNetwork, config: PathfindingConfig, text: str, fmt: str
) -> str:
    """Process one query string and return the rendered report."""
    start_raw, end_raw = parse_query(text)
    start, end = resolve_stations(network, start_raw, end_raw)
    result = build_path_result(network, start, end, config)
    return render_json(result) if fmt == "json" else render_text(result)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Beijing Subway fare calculation system (CLI)."
    )
    parser.add_argument(
        "--output_file", default=None,
        help="export query results to this file",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--mode", choices=list(VALID_MODES), default=MODE_COMPREHENSIVE,
        help="path query mode (default: comprehensive)",
    )
    parser.add_argument(
        "--max_transfers", type=int, default=None,
        help="maximum number of transfers allowed",
    )
    parser.add_argument(
        "--line_preference", default=None,
        help="preferred line(s), e.g. 'Line 1' (comma-separated for several)",
    )
    parser.add_argument(
        "--check_data", action="store_true",
        help="run data integrity check and exit",
    )
    return parser


def build_config(
    args: argparse.Namespace, network: SubwayNetwork, out: TextIO
) -> PathfindingConfig:
    """Create a validated ``PathfindingConfig`` from command-line arguments."""
    known = {normalize_line_name(name): name for name in network.line_names()}
    preferred = []
    if args.line_preference:
        for raw in args.line_preference.split(","):
            raw = raw.strip()
            if not raw:
                continue
            key = normalize_line_name(raw)
            if key in known:
                preferred.append(known[key])
            else:
                print(f"Warning: line '{raw}' not found; preference ignored", file=out)
    config = PathfindingConfig(
        mode=args.mode,
        max_transfers=args.max_transfers,
        preferred_lines=preferred,
    )
    config.validate()
    return config


def write_output(path: str, content: str, append: bool) -> None:
    with open(path, "a" if append else "w", encoding="utf-8") as handle:
        handle.write(content + "\n\n")


def main(
    argv: Optional[Sequence[str]] = None,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    """Run the CLI. Returns a process exit code."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    inp = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout

    if args.max_transfers is not None and args.max_transfers < 0:
        parser.error("--max_transfers must be >= 0")

    try:
        network = build_network(load_subway_data(DATA_FILE_PATH))
    except (OSError, ValueError, DataError) as exc:
        print(f"Error: failed to load subway data: {exc}", file=out)
        return 1

    if args.check_data:
        report = check_network(network)
        print(report.format(), file=out)
        return 0 if report.ok else 1

    try:
        config = build_config(args, network, out)
    except ValueError as exc:
        print(f"Error: invalid settings: {exc}", file=out)
        return 2

    print(BANNER, file=out)
    first_write = True
    while True:
        out.write("Query> ")
        out.flush()
        line = inp.readline()
        if not line:  # end of input
            break
        text = line.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            break

        try:
            rendered = run_query(network, config, text, args.format)
        except SubwayError as exc:
            print(f"Error: {exc}", file=out)
            continue
        except ValueError as exc:
            print(f"Error: route or fare calculation failed: {exc}", file=out)
            continue
        except Exception as exc:  # keep the session alive on unexpected failures
            print(f"Error: unexpected failure while querying: {exc}", file=out)
            continue

        print(rendered, file=out)
        if args.output_file:
            try:
                write_output(args.output_file, rendered, append=not first_write)
                first_write = False
            except OSError as exc:
                print(f"Error: cannot write output file: {exc}", file=out)

    return 0
