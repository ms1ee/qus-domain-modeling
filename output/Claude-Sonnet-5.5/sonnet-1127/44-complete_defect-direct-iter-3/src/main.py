"""CLI for Beijing Subway fare calculation."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_loader
import data_manager
from models import Edge, Graph
from pathfinding import PathfindingConfig, ShortestPath
from fare_calculator import Sum_money, calculate_estimated_time


class SubwaySystem:
    def __init__(self, data):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for s in data["stations"]:
            self._num(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in data["connections"]:
            a, b = self._num(c["source"]), self._num(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))
            for n in (c["source"], c["dest"]):
                self.graph.station_lines.setdefault(n, [])
                if c["line"] not in self.graph.station_lines[n]:
                    self.graph.station_lines[n].append(c["line"])

    def _num(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
        return self.station_to_number[name]

    def query(self, start, end, config):
        sp = ShortestPath(self.graph, self.station_to_number[start], config)
        t = self.station_to_number[end]
        nodes, edges = sp.path_with_edges(t)
        if not nodes:
            raise RuntimeError("No route found between '%s' and '%s'" % (start, end))
        dist = sp.dist_to[t]
        transfers = sp.get_transfer_count(t)
        try:
            fare = Sum_money(dist)
        except Exception as e:
            raise ArithmeticError("Fare calculation failed: %s" % e)
        names = [self.number_to_station[n] for n in nodes]
        tstations = []
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                tstations.append({"station": names[i], "from_line": edges[i - 1].line,
                                  "to_line": edges[i].line})
        lines = []
        segments = []
        for i, e in enumerate(edges):
            if e.line not in lines:
                lines.append(e.line)
            if segments and segments[-1]["line"] == e.line:
                segments[-1]["to"] = names[i + 1]
                segments[-1]["stations"] += 1
            else:
                segments.append({"line": e.line, "from": names[i], "to": names[i + 1], "stations": 1})
        return {"query": {"start": start, "end": end, "mode": config.mode},
                "path": names, "distance_m": dist, "distance_km": round(dist / 1000.0, 2),
                "fare": fare, "estimated_time": calculate_estimated_time(dist, transfers),
                "transfer_count": transfers, "lines": lines,
                "transfer_stations": tstations, "segments": segments}


def fmt_distance(m):
    if m < 1000:
        return "%d meters (%.2f km)" % (m, m / 1000.0)
    return "%.2f km (%d meters)" % (m / 1000.0, m)


def format_text(r):
    out = ["Route: %s -> %s" % (r["query"]["start"], r["query"]["end"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"]))]
    for s in r["segments"]:
        out.append("  Take %s from %s to %s (%d stops)" % (s["line"], s["from"], s["to"], s["stations"]))
    out.append("Total distance: " + fmt_distance(r["distance_m"]))
    out.append("Transfers: %d" % r["transfer_count"])
    for t in r["transfer_stations"]:
        out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Lines: " + ", ".join(r["lines"]))
    out.append("Estimated time: %.1f minutes" % r["estimated_time"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def render(r, fmt):
    if fmt == "json":
        return json.dumps(r, ensure_ascii=False, indent=2)
    return format_text(r)


def parse_input(line, system):
    """Return (start, end) or raise ValueError with a user message."""
    line = line.replace("；", ";")
    parts = [p.strip() for p in line.split(";")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Input format incorrect, please use 'Starting Station; Ending Station' format")
    a, b = parts
    if a not in system.station_to_number:
        raise ValueError("Starting station '%s' does not exist, please check the station name" % a)
    if b not in system.station_to_number:
        raise ValueError("Ending station '%s' does not exist, please check the station name" % b)
    if a == b:
        raise ValueError("Starting station cannot be the same as the ending station")
    return a, b


def write_output(path, text):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except OSError as e:
        print("Failed to write output file: %s" % e)


def main(argv=None):
    p = argparse.ArgumentParser(description="Beijing Subway fare calculator")
    p.add_argument("--output_file")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--mode", choices=["shortest_distance", "least_transfer", "comprehensive"],
                   default="shortest_distance")
    p.add_argument("--max_transfers", type=int)
    p.add_argument("--line_preference")
    p.add_argument("--check_data", action="store_true")
    args = p.parse_args(argv)

    try:
        data = data_loader.load_subway_data(data_loader.DATA_FILE_PATH)
    except (OSError, ValueError) as e:
        print("Failed to load data: %s" % e)
        return 1

    if args.check_data:
        problems = data_manager.check_data(data)
        print("Stations: %d, connections: %d" % (len(data["stations"]), len(data["connections"])))
        if problems:
            print("Data check found %d problem(s):" % len(problems))
            for x in problems:
                print(" - " + x)
        else:
            print("Data check passed.")
        return 0

    system = SubwaySystem(data)
    config = PathfindingConfig()
    config.mode = args.mode
    config.max_transfers = args.max_transfers
    if args.line_preference:
        config.preferred_lines = [args.line_preference]

    print("Beijing Subway Fare Calculator. Enter 'Starting Station; Ending Station' (or 'quit').")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if line.lower() in ("quit", "exit", "q"):
            break
        if not line:
            continue
        try:
            a, b = parse_input(line, system)
        except ValueError as e:
            print(e)
            continue
        try:
            result = system.query(a, b, config)
        except ArithmeticError as e:
            print(e)
            continue
        except Exception as e:
            print("Path calculation error: %s" % e)
            continue
        text = render(result, args.format)
        print(text)
        if args.output_file:
            write_output(args.output_file, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
