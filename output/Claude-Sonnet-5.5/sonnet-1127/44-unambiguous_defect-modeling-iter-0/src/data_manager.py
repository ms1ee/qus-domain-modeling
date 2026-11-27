"""Data management: load, graph building, integrity checks and updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Graph, Edge

MAIN_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
              "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
              "Fangshan Line", "Airport Line"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = {"stations": [], "connections": []}
        self.graph = Graph()
        self.load()

    def load(self):
        self.data = load_subway_data(self.data_file)
        self.rebuild()

    def rebuild(self):
        g = Graph()
        n = 0
        for s in self.data.get("stations", []):
            if s["name"] not in g.station_to_number:
                g.add_station(s["name"], n)
                n += 1
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for nm in (c["source"], c["dest"]):
                if nm not in g.station_to_number:
                    g.add_station(nm, n)
                    n += 1
                    g.set_station_lines(nm, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g

    @property
    def station_to_number(self):
        return self.graph.station_to_number

    def has_station(self, name):
        return name in self.graph.station_to_number

    def lines(self):
        s = set()
        for ls in self.graph.station_lines.values():
            s.update(ls)
        return sorted(s)

    def suggest(self, name, limit=5):
        return [n for n in self.graph.station_to_number if name and (name in n or n in name)][:limit]

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """stations: ordered names; distances: meters between consecutive stations."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 entries")
        known = {s["name"]: s for s in self.data["stations"]}
        for nm in stations:
            if nm in known:
                if line_name not in known[nm]["lines"]:
                    known[nm]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": nm, "lines": [line_name]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

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
                self.rebuild()
                return True
        return False

    def update_distance(self, a, b, distance, line=None):
        if distance <= 0:
            raise ValueError("distance must be positive")
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found

    # ---- integrity ----
    def check_data(self):
        """Return (ok, list of messages)."""
        issues = []
        names = {s["name"] for s in self.data["stations"]}
        lines = set(self.lines())
        for l in MAIN_LINES:
            if l not in lines:
                issues.append("Missing main line: %s" % l)
        connected = set()
        for c in self.data["connections"]:
            for k in ("source", "dest"):
                if c[k] not in names:
                    issues.append("Connection references unknown station: %s" % c[k])
                connected.add(c[k])
            d = c["distance"]
            if not isinstance(d, (int, float)) or d <= 0:
                issues.append("Invalid distance %s-%s: %s" % (c["source"], c["dest"], d))
            elif d > 20000:
                issues.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], d))
            if c["source"] == c["dest"]:
                issues.append("Self loop at %s" % c["source"])
        for n in sorted(names - connected):
            issues.append("Station without connections: %s" % n)
        return (not issues), issues
