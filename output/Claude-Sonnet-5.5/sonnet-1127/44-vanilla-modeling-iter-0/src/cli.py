"""Command-line interface."""
import argparse
import sys

from data_manager import DataManager
from fare_calculator import FareCalculator
from models import Query, Route
from pathfinding import PathfindingConfig, ShortestPath
from report import ReportExporter
from validator import InputValidator


def build_route(graph, nodes, edges):
    names = [graph.number_to_station[n] for n in nodes]
    lines, segments, transfers = [], [], []
    cur_line, cur = None, []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if cur_line is None:
            cur_line, cur = e.line, [names[i]]
        elif e.line != cur_line:
            segments.append((cur_line, cur))
            transfers.append((names[i], cur_line, e.line))
            cur_line, cur = e.line, [names[i]]
        cur.append(names[i + 1])
    if cur_line is not None:
        segments.append((cur_line, cur))
    total = sum(e.distance for e in edges)
    return Route(names, total, len(transfers), lines, segments, transfers)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file", default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int, default=None)
    p.add_argument("--line_preference", default=None)
    p.add_argument("--check_data", action="store_true")
    return p.parse_args(argv)


class CLI:
    def __init__(self, args, data_manager=None):
        self.args = args
        self.dm = data_manager or DataManager()
        self.graph = self.dm.graph
        self.validator = InputValidator(self.graph)
        self.fares = FareCalculator()
        self.exporter = ReportExporter(args.format, args.output_file)
        prefs = [x.strip() for x in args.line_preference.split(",") if x.strip()] \
            if args.line_preference else []
        self.config = PathfindingConfig(args.mode, args.max_transfers, prefs)

    def query(self, start, end):
        """Return rendered report string or raise on error."""
        s, t = self.graph.station_to_number[start], self.graph.station_to_number[end]
        sp = ShortestPath(self.graph, s, self.config)
        nodes, edges = sp.path_with_edges(t)
        if not nodes:
            return None
        route = build_route(self.graph, nodes, edges)
        fare = self.fares.calculate_route(route)
        return self.exporter.render(Query(start, end, self.args.mode), route, fare)

    def handle_line(self, line):
        ok, start, end, err = self.validator.validate(line)
        if not ok:
            print(err)
            return
        try:
            result = self.query(start, end)
        except ValueError as e:
            print("Fare calculation error: %s" % e)
            return
        except Exception as e:  # path calculation failure
            print("Path calculation error: %s" % e)
            return
        if result is None:
            print("No route found between '%s' and '%s' (check --max_transfers)" % (start, end))
            return
        print(result)
        try:
            self.exporter.export(result)
        except OSError as e:
            print("Failed to write output file: %s" % e)

    def run(self):
        if self.args.check_data:
            ok, msgs = self.dm.check_data()
            print("\n".join(msgs))
            return 0 if ok else 1
        print("Enter 'Starting Station; Ending Station' (empty line or 'exit' to quit)")
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if line.strip().lower() in ("", "exit", "quit", "q"):
                break
            self.handle_line(line)
        return 0


def main(argv=None):
    args = parse_args(argv)
    return CLI(args).run()


if __name__ == "__main__":
    sys.exit(main())
