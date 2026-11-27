"""Data management: building the graph, integrity checks, updates."""
from data_loader import DATA_FILE_PATH, load_subway_data
from models import Graph, Edge

REQUIRED_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
                  "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
                  "Fangshan Line", "Airport Line"]


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self._build()

    def _build(self):
        self.graph = Graph()
        g = self.graph
        for s in self.data.get("stations", []):
            if s["name"] not in g.station_to_number:
                g.add_station(s["name"], len(g.station_to_number))
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(n, len(g.station_to_number))
                    g.set_station_lines(n, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))

    def get_lines(self):
        """line name -> station sequence (by connection order)."""
        lines = {}
        for c in self.data.get("connections", []):
            seq = lines.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)
        return lines

    # ---- integrity check ----
    def check_data(self):
        """Return (ok, messages)."""
        msgs, ok = [], True
        g = self.graph
        names = {l for ls in g.station_lines.values() for l in ls}
        names |= {c["line"] for c in self.data.get("connections", [])}
        msgs.append("Stations: %d, connections: %d, lines: %d" % (
            len(g.station_to_number), len(self.data.get("connections", [])), len(names)))
        for line in REQUIRED_LINES:
            if line not in names:
                msgs.append("Warning: line '%s' not found in data" % line)
        station_names = {s["name"] for s in self.data.get("stations", [])}
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in station_names:
                    ok = False
                    msgs.append("Error: connection references unknown station '%s'" % n)
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                ok = False
                msgs.append("Error: invalid distance %r between %s and %s" % (d, c["source"], c["dest"]))
            elif d > 20000:
                msgs.append("Warning: unusually long distance %s between %s and %s" % (d, c["source"], c["dest"]))
        for name, num in g.station_to_number.items():
            if not g.neighbors(num):
                ok = False
                msgs.append("Error: station '%s' has no connections" % name)
        for num, edges in g.adjacency.items():
            for e in edges:
                if not any(r.dest == num and r.distance == e.distance for r in g.adjacency[e.dest]):
                    ok = False
                    msgs.append("Error: asymmetric connection %s-%s" % (e.source, e.dest))
        msgs.append("Data check passed." if ok else "Data check found errors.")
        return ok, msgs

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """Add a line: stations list and distances between consecutive stations."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 entries")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self._build()

    def update_station(self, name, new_name=None, lines=None):
        target = next((s for s in self.data["stations"] if s["name"] == name), None)
        if target is None:
            raise KeyError(name)
        if lines is not None:
            target["lines"] = list(lines)
        if new_name:
            target["name"] = new_name
            for c in self.data["connections"]:
                if c["source"] == name:
                    c["source"] = new_name
                if c["dest"] == name:
                    c["dest"] = new_name
        self._build()

    def update_distance(self, a, b, distance):
        if distance <= 0:
            raise ValueError("distance must be positive")
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = distance
                found = True
        if not found:
            raise KeyError("no connection between %s and %s" % (a, b))
        self._build()
