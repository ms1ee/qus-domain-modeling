"""Data management: building the graph, integrity check, updates."""
import json

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REQUIRED_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
                  "Line 13", "Line 14", "Line 15", "Changping", "Yizhuang", "Fangshan", "Airport"]
ALT_NAMES = {"Line 1": ["1号线"], "Line 2": ["2号线"], "Line 4": ["4号线"], "Line 5": ["5号线"],
             "Line 6": ["6号线"], "Line 8": ["8号线"], "Line 10": ["10号线"], "Line 13": ["13号线"],
             "Line 14": ["14号线"], "Line 15": ["15号线"], "Changping": ["昌平"],
             "Yizhuang": ["亦庄"], "Fangshan": ["房山"], "Airport": ["机场"]}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = None
        self.build_graph()

    def build_graph(self):
        g = Graph()
        for i, st in enumerate(self.data.get("stations", [])):
            g.add_station(st["name"], i)
            g.set_station_lines(st["name"], st.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(n, len(g.station_to_number))
                    g.set_station_lines(n, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g
        return g

    def line_names(self):
        names = set()
        for st in self.data.get("stations", []):
            names.update(st.get("lines", []))
        for c in self.data.get("connections", []):
            names.add(c["line"])
        return names

    def check_data(self):
        """Return list of problem strings (empty if data is fine)."""
        problems = []
        names = self.line_names()
        for req in REQUIRED_LINES:
            keys = [req.casefold()] + [a.casefold() for a in ALT_NAMES.get(req, [])]
            if not any(any(k in n.casefold() for k in keys) for n in names):
                problems.append("Missing line: %s" % req)
        known = {s["name"] for s in self.data.get("stations", [])}
        connected = set()
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                connected.add(n)
                if n not in known:
                    problems.append("Connection references unknown station: %s" % n)
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                problems.append("Bad distance %r between %s and %s" % (d, c["source"], c["dest"]))
        for n in sorted(known - connected):
            problems.append("Station without connection: %s" % n)
        return problems

    def save(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)

    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        existing = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in existing:
                if line_name not in existing[n]["lines"]:
                    existing[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.build_graph()

    def update_station(self, name, new_name=None, lines=None):
        for s in self.data["stations"]:
            if s["name"] == name:
                if lines is not None:
                    s["lines"] = list(lines)
                if new_name:
                    s["name"] = new_name
                    for c in self.data["connections"]:
                        if c["source"] == name:
                            c["source"] = new_name
                        if c["dest"] == name:
                            c["dest"] = new_name
                self.build_graph()
                return True
        return False

    def update_distance(self, a, b, distance):
        ok = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                ok = True
        if ok:
            self.build_graph()
        return ok
