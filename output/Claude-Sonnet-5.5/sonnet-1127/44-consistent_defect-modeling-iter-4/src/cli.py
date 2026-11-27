"""Command line interface."""
import argparse
import sys

from data_manager import DataManager
from pathfinding import PathfindingConfig, ShortestPath
from report import Route, RouteSummary, ReportExporter
from validator import InputValidator


def build_parser():
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p


class CLI:
    def __init__(self, args, data_manager=None):
        self.args = args
        self.dm = data_manager or DataManager()
        self.validator = InputValidator(self.dm.station_names())
        self.exporter = ReportExporter(args.format, args.output_file)

    def compute(self, start, end):
        cfg = PathfindingConfig()
        cfg.mode = self.args.mode
        cfg.max_transfers = self.args.max_transfers
        cfg.preferred_lines = [self.args.line_preference] if self.args.line_preference else []
        s, t = self.dm.station_to_number[start], self.dm.station_to_number[end]
        sp = ShortestPath(self.dm.graph, s, cfg)
        nodes, edges = sp.path_with_edges(t)
        if not nodes:
            raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
        names = [self.dm.number_to_station[n] for n in nodes]
        transfers = [names[i + 1] for i in range(len(edges) - 1) if edges[i].line != edges[i + 1].line]
        return RouteSummary(Route(names, edges, transfers))

    def handle(self, text):
        try:
            start, end = self.validator.validate(text)
        except ValueError as e:
            print(e)
            return
        try:
            summary = self.compute(start, end)
        except Exception as e:
            print("Path calculation failed: %s" % e)
            return
        try:
            content = self.exporter.render(start, end, self.args.mode, summary)
        except Exception as e:
            print("Fare calculation failed: %s" % e)
            return
        print(content)
        try:
            self.exporter.export(content)
        except OSError as e:
            print("Could not write output file: %s" % e)

    def run(self):
        if self.args.check_data:
            ok, msgs = self.dm.check_data()
            print("Data check passed" if ok else "Data check found issues:")
            for m in msgs:
                print(" - " + m)
            return 0 if ok else 1
        print("Enter 'Starting Station; Ending Station' (q to quit)")
        while True:
            try:
                text = input("> ")
            except EOFError:
                break
            if text.strip().lower() in ("q", "quit", "exit"):
                break
            if not text.strip():
                continue
            self.handle(text)
        return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    return CLI(args).run()
