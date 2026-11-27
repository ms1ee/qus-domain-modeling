"""Command line interface."""
import argparse
import re
import sys

from data_manager import DataManager
from pathfinding import MODES, PathfindingConfig, ShortestPath
from report import Query, RouteReport, build_route

FORMAT_ERR = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class CLI:
    def __init__(self, data_manager=None, output_file=None, fmt="text", mode="shortest_distance",
                 max_transfers=None, line_preference=None):
        self.dm = data_manager or DataManager()
        self.output_file = output_file
        self.format = fmt
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference

    def parse_input(self, text):
        parts = [p.strip() for p in re.split(r"[;；,，]", text)]
        if len(parts) != 2 or not all(parts):
            raise ValueError(FORMAT_ERR)
        return parts

    def process(self, text):
        """Return the output string for one query line."""
        try:
            a, b = self.parse_input(text)
        except ValueError as e:
            return str(e)
        s, exact_s = self.dm.find_station(a)
        if s is None:
            return "Starting station '%s' does not exist, please check the station name" % a
        t, exact_t = self.dm.find_station(b)
        if t is None:
            return "Ending station '%s' does not exist, please check the station name" % b
        notes = []
        if not exact_s:
            notes.append("Starting station '%s' matched to '%s'" % (a, s))
        if not exact_t:
            notes.append("Ending station '%s' matched to '%s'" % (b, t))
        if s == t:
            return "Starting station cannot be the same as the ending station"
        g = self.dm.graph
        cfg = PathfindingConfig(self.mode, self.max_transfers,
                                [self.line_preference] if self.line_preference else [])
        try:
            sp = ShortestPath(g, g.station_to_number[s], cfg)
            tn = g.station_to_number[t]
            nodes, edges = sp.path_with_edges(tn)
            if not nodes:
                return "No route found from '%s' to '%s' under the given constraints" % (s, t)
            route = build_route(g, nodes, edges)
        except Exception as e:
            return "Path calculation failed: %s" % e
        try:
            rep = RouteReport(route, Query(s, t, self.mode, self.max_transfers,
                                           self.line_preference), self.format, self.output_file)
        except Exception as e:
            return "Fare calculation failed: %s" % e
        try:
            rep.save()
        except OSError as e:
            notes.append("Could not write output file: %s" % e)
        text_out = rep.render()
        if notes and self.format != "json":
            text_out = "\n".join(notes) + "\n" + text_out
        return text_out

    def run(self):
        print("Beijing Subway fare calculator. Enter 'Start; End' (empty line or 'quit' to exit).")
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if line.strip().lower() in ("", "quit", "exit", "q"):
                break
            print(self.process(line))


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=list(MODES), default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        dm = DataManager()
    except Exception as e:
        print("Failed to load data: %s" % e)
        return 1
    if args.check_data:
        ok, issues = dm.check_data()
        print("Data check passed" if ok else "Data check found issues:")
        for i in issues:
            print(" - " + i)
        return 0 if ok else 1
    CLI(dm, args.output_file, args.format, args.mode, args.max_transfers,
        args.line_preference).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
