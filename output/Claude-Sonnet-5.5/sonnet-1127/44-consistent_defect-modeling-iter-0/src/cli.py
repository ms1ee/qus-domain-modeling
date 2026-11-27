"""Command line interface."""
import argparse
import sys
from data_loader import DATA_FILE_PATH
from data_manager import DataManager, DataIntegrityChecker
from validator import InputValidator
from route_service import RouteQuery, find_route, ReportExporter


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
    def __init__(self, args=None):
        self.args = build_parser().parse_args(args)
        self.manager = DataManager(DATA_FILE_PATH)
        self.network = self.manager.network()
        self.validator = InputValidator(self.network)
        self.exporter = ReportExporter(self.args.format, self.args.output_file)

    def check_data(self):
        problems = DataIntegrityChecker(self.manager).check()
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for p in problems[:50]:
                print(" -", p)
            return 1
        print("Data check passed.")
        return 0

    def query(self, line):
        try:
            start, end, notes = self.validator.parse(line)
        except ValueError as e:
            print(e)
            return
        for n in notes:
            print(n)
        q = RouteQuery(start, end, self.args.mode, self.args.max_transfers, self.args.line_preference)
        try:
            route = find_route(self.network, q)
        except Exception as e:
            print("Path calculation failed: %s" % e)
            return
        if route is None:
            print("No route found between '%s' and '%s' (check transfer limit)" % (start, end))
            return
        try:
            print(self.exporter.export(q, route))
        except Exception as e:
            print("Fare calculation or export failed: %s" % e)

    def run(self):
        if self.args.check_data:
            return self.check_data()
        print("Enter 'Starting Station; Ending Station' (empty line or 'quit' to exit)")
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if line.strip().lower() in ("", "q", "quit", "exit"):
                break
            self.query(line)
        return 0


def main(args=None):
    return CLI(args).run()


if __name__ == "__main__":
    sys.exit(main())
