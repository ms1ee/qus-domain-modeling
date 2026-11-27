"""Command-line interface for the Beijing Subway fare calculation system."""

import argparse
import difflib
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import SubwayNetwork
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import build_summary, format_json, format_text

FORMAT_ERROR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", action="append", default=None)
    p.add_argument("--check_data", action="store_true")
    p.add_argument("--data_file", default=DATA_FILE_PATH)
    return p.parse_args(argv)


def resolve_station(network, name, role):
    """Return (resolved_name, message or None). Raises ValueError if not found."""
    if name in network.station_to_number:
        return name, None
    lower = {n.lower(): n for n in network.station_to_number}
    if name.lower() in lower:
        return lower[name.lower()], None
    match = difflib.get_close_matches(name.lower(), list(lower), n=1, cutoff=0.6)
    if match:
        real = lower[match[0]]
        return real, f"{role} station '{name}' not found, using nearest match '{real}'"
    raise ValueError(f"{role} station '{name}' does not exist, please check the station name")


def parse_query(line):
    parts = [x.strip() for x in re.split(r"[;,；，]", line)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(FORMAT_ERROR)
    return parts[0], parts[1]


def handle_query(network, line, config, fmt):
    start, end = parse_query(line)
    start, m1 = resolve_station(network, start, "Starting")
    end, m2 = resolve_station(network, end, "Ending")
    notes = [m for m in (m1, m2) if m]
    if start == end:
        raise ValueError("Starting station cannot be the same as the ending station")
    try:
        sp = ShortestPath(network.graph, network.station_to_number[start], config)
    except Exception as exc:
        raise RuntimeError(f"Path calculation error: {exc}") from exc
    summary = build_summary(network, sp, start, end, config.mode)
    text = format_json(summary) if fmt == "json" else format_text(summary)
    return notes, text


def main(argv=None):
    args = parse_args(argv)
    try:
        data = load_subway_data(args.data_file)
    except (OSError, ValueError) as exc:
        print(f"Failed to load subway data: {exc}", file=sys.stderr)
        return 1
    network = SubwayNetwork(data)

    if args.check_data:
        ok, msgs = network.check_integrity(data)
        for m in msgs:
            print(m)
        print("Data integrity check passed" if ok else "Data integrity check failed")
        return 0 if ok else 1

    try:
        config = PathfindingConfig(mode=args.mode, max_transfers=args.max_transfers,
                                   preferred_lines=args.line_preference)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    interactive = sys.stdin.isatty()
    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (or 'quit' to exit).")
    while True:
        if interactive:
            print("> ", end="", flush=True)
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        try:
            notes, text = handle_query(network, line, config, args.format)
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}")
            continue
        except Exception as exc:  # unexpected
            print(f"Error: unexpected failure: {exc}")
            continue
        for n in notes:
            print(f"Note: {n}")
        print(text)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as fh:
                    fh.write(text + "\n")
            except OSError as exc:
                print(f"Error: could not write output file: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
