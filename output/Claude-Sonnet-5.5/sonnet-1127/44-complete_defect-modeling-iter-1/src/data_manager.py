"""Network construction, integrity checks and data updates."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge

REQUIRED_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8",
                  "Line 10", "Line 13", "Line 14", "Line 15"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.build()

    def build(self):
        names = {s["name"] for s in self.data.get("stations", [])}
        for c in self.data.get("connections", []):
            names.add(c["source"])
            names.add(c["dest"])
        self.station_to_number = {n: i for i, n in enumerate(sorted(names))}
        self.number_to_station = {i: n for n, i in self.station_to_number.items()}
        self.graph = Graph()
        for n in self.station_to_number.values():
            self.graph.add_node(n)
        for s in self.data.get("stations", []):
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c["line"]))

    def lines_of(self, name):
        return self.graph.station_lines.get(name, [])

    def is_transfer(self, name):
        return len(self.lines_of(name)) > 1

    def check_data(self):
        """Return list of problem strings (empty if ok)."""
        problems = []
        known = {s["name"] for s in self.data.get("stations", [])}
        lines = {l for s in self.data.get("stations", []) for l in s.get("lines", [])}
        for l in REQUIRED_LINES:
            if l not in lines:
                problems.append(f"Missing line: {l}")
        connected = set()
        for c in self.data.get("connections", []):
            connected.add(c["source"])
            connected.add(c["dest"])
            for k in ("source", "dest"):
                if c[k] not in known:
                    problems.append(f"Connection references unknown station: {c[k]}")
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                problems.append(f"Invalid distance {d} between {c['source']} and {c['dest']}")
        for n in known - connected:
            problems.append(f"Station without connections: {n}")
        return problems

    # ---- update mechanisms ----
    def add_station_line(self, name, line):
        for s in self.data["stations"]:
            if s["name"] == name:
                if line not in s["lines"]:
                    s["lines"].append(line)
                break
        else:
            self.data["stations"].append({"name": name, "lines": [line]})
        self.build()

    def add_line(self, line, stations, distances):
        """Add a line from a station sequence and len(stations)-1 distances."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        for s in stations:
            self.add_station_line(s, line)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line})
        self.build()

    def rename_station(self, old, new):
        for s in self.data["stations"]:
            if s["name"] == old:
                s["name"] = new
        for c in self.data["connections"]:
            if c["source"] == old:
                c["source"] = new
            if c["dest"] == old:
                c["dest"] = new
        self.build()

    def update_distance(self, a, b, distance):
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if not found:
            raise KeyError(f"No connection between {a} and {b}")
        self.build()
