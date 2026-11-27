"""Data management and integrity checks."""
import difflib

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Graph, Edge


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self.build()

    def build(self):
        g = Graph()
        for s in self.data.get("stations", []):
            if s["name"] not in g.station_to_number:
                g.add_station(s["name"], len(g.station_to_number))
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(n, len(g.station_to_number))
                    g.station_lines.setdefault(n, [c.get("line")])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c.get("line")))
        self.graph = g

    def lines(self):
        result = {}
        for s, ls in self.graph.station_lines.items():
            for l in ls:
                result.setdefault(l, []).append(s)
        return result

    def match_station(self, name):
        """Return (station, exact) or (None, False)."""
        if name in self.graph.station_to_number:
            return name, True
        m = difflib.get_close_matches(name, list(self.graph.station_to_number), n=1, cutoff=0.5)
        return (m[0], False) if m else (None, False)

    # updates
    def add_line(self, line_name, stations, distances):
        if len(distances) != len(stations) - 1:
            raise ValueError("need len(stations)-1 distances")
        for s in stations:
            lines = self.data["stations"]
            ex = next((x for x in lines if x["name"] == s), None)
            if ex is None:
                self.data["stations"].append({"name": s, "lines": [line_name]})
            elif line_name not in ex["lines"]:
                ex["lines"].append(line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
            self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line_name})
        self.build()

    def update_station(self, old_name, new_name=None, lines=None):
        found = False
        for s in self.data["stations"]:
            if s["name"] == old_name:
                found = True
                if lines is not None:
                    s["lines"] = list(lines)
                if new_name:
                    s["name"] = new_name
        if not found:
            raise KeyError(old_name)
        if new_name:
            for c in self.data["connections"]:
                if c["source"] == old_name:
                    c["source"] = new_name
                if c["dest"] == old_name:
                    c["dest"] = new_name
        self.build()

    def update_distance(self, a, b, distance):
        if distance <= 0:
            raise ValueError("distance must be positive")
        n = 0
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                n += 1
        if not n:
            raise KeyError((a, b))
        self.build()


REPRESENTATIVE = ["西直门", "国贸", "天安门东", "北京站", "西单"]


class DataChecker:
    def __init__(self, manager):
        self.manager = manager

    def check(self):
        g = self.manager.graph
        issues = []
        lines = self.manager.lines()
        if len(g.station_to_number) == 0:
            issues.append("No stations loaded")
        for name in REPRESENTATIVE:
            if name not in g.station_to_number:
                issues.append("Representative station missing: %s" % name)
        names = set(g.station_to_number)
        for c in self.manager.data.get("connections", []):
            if c["source"] not in names or c["dest"] not in names:
                issues.append("Connection references unknown station: %s-%s" % (c["source"], c["dest"]))
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                issues.append("Bad distance %s-%s: %s" % (c["source"], c["dest"], d))
        for s in names:
            if not g.adjacency.get(g.station_to_number[s]):
                issues.append("Station without outgoing connection: %s" % s)
        return {"ok": not issues, "issues": issues, "stations": len(names),
                "lines": len(lines)}
