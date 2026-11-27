"""Command line interface."""
import argparse
import re
import sys

from data_manager import DataManager, DataChecker
from route import Query, RouteSummary, find_route, MODES
from report import Report


class CLI:
    def __init__(self, args, manager=None):
        self.args = args
        self.output_file = args.output_file
        self.format = args.format
        self.check_data = args.check_data
        self.manager = manager or DataManager()

    def parse_input(self, line):
        parts = [p.strip() for p in re.split(r"[;；,，]", line)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
        return parts

    def process(self, line):
        """Returns output text or raises ValueError with message."""
        a, b = self.parse_input(line)
        start, ex1 = self.manager.match_station(a)
        if start is None:
            raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
        end, ex2 = self.manager.match_station(b)
        if end is None:
            raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
        if start == end:
            raise ValueError("Starting station cannot be the same as the ending station")
        notes = []
        if not ex1:
            notes.append("Starting station '%s' matched to '%s'" % (a, start))
        if not ex2:
            notes.append("Ending station '%s' matched to '%s'" % (b, end))
        q = Query(start, end, self.args.mode, self.args.max_transfers, self.args.line_preference)
        try:
            route = find_route(self.manager.graph, q)
        except Exception as e:
            raise ValueError("Path calculation failed: %s" % e)
        if route is None:
            raise ValueError("No route found between '%s' and '%s'" % (start, end))
        try:
            summary = RouteSummary(route)
        except Exception as e:
            raise ValueError("Fare calculation failed: %s" % e)
        rep = Report(q, route, summary, self.format, self.output_file)
        rep.save()
        text = rep.content
        if notes and self.format == "text":
            text = "\n".join(notes) + "\n" + text
        return text

    def run_check(self):
        res = DataChecker(self.manager).check()
        print("Stations: %d, Lines: %d" % (res["stations"], res["lines"]))
        if res["ok"]:
            print("Data check passed")
        else:
            print("Data check found %d issue(s):" % len(res["issues"]))
            for i in res["issues"][:50]:
                print(" - " + i)
        return 0 if res["ok"] else 1

    def run(self):
        if self.check_data:
            return self.run_check()
        print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (q to quit)")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if line.lower() in ("q", "quit", "exit"):
                break
            if not line:
                continue
            try:
                print(self.process(line))
            except ValueError as e:
                print(e)
            except Exception as e:
                print("Unexpected error: %s" % e)
        return 0


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
    return CLI(args).run()


if __name__ == "__main__":
    sys.exit(main())
