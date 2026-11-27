"""CLI for the Beijing Subway fare calculator."""
import argparse
import re
import sys

from data_loader import DATA_FILE_PATH, load_subway_data
from data_manager import SubwayNetwork
from pathfinding import PathfindingConfig, ShortestPath
from report import build_result, to_json, to_text

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


def parse_input(line):
    parts = [p.strip() for p in re.split(r"[;；,，]", line) if p.strip()]
    if len(parts) != 2:
        return None
    return parts


def run_query(network, line, args, config):
    parts = parse_input(line)
    if parts is None:
        return FORMAT_ERR
    a, b = parts
    s, exact_s = network.match_station(a)
    if s is None:
        return "Starting station '%s' does not exist, please check the station name" % a
    t, exact_t = network.match_station(b)
    if t is None:
        return "Ending station '%s' does not exist, please check the station name" % b
    notes = []
    if not exact_s:
        notes.append("Starting station '%s' matched to '%s'" % (a, s))
    if not exact_t:
        notes.append("Ending station '%s' matched to '%s'" % (b, t))
    if s == t:
        return "Starting station cannot be the same as the ending station"
    try:
        sn, tn = network.station_to_number[s], network.station_to_number[t]
        sp = ShortestPath(network.graph, sn, config)
        path, edges = sp.path_with_edges(tn)
        if not path:
            return "No route found between '%s' and '%s' under current settings" % (s, t)
        transfers = sp.get_transfer_count(tn)
    except Exception as ex:
        return "Path calculation error: %s" % ex
    try:
        result = build_result(network, s, t, path, edges, transfers)
    except Exception as ex:
        return "Fare calculation error: %s" % ex
    text = to_json(result) if args.format == "json" else to_text(result)
    if args.format != "json" and notes:
        text = "\n".join(notes) + "\n" + text
    return text


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        network = SubwayNetwork(load_subway_data(DATA_FILE_PATH))
    except Exception as ex:
        print("Failed to load data: %s" % ex)
        return 1

    if args.check_data:
        problems, ns, nc, lines = network.check_data()
        print("Stations: %d, connections: %d, lines: %d" % (ns, nc, len(lines)))
        for pr in problems:
            print("Problem: " + pr)
        print("Data check passed" if not problems else "Data check found %d problem(s)" % len(problems))
        return 0 if not problems else 1

    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    config.preferred_lines = [args.line_preference] if args.line_preference else []

    print("Enter 'Starting Station; Ending Station' (empty line or 'q' to quit)")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line.strip() or line.strip().lower() in ("q", "quit", "exit"):
            break
        out = run_query(network, line, args, config)
        print(out)
        if args.output_file:
            try:
                with open(args.output_file, "a", encoding="utf-8") as f:
                    f.write(out + "\n\n")
            except OSError as ex:
                print("Cannot write output file: %s" % ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
