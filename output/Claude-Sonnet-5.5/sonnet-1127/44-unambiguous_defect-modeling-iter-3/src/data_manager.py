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
        self.graph = None
        self.build_graph()

    def build_graph(self):
        g = Graph()
        for i, s in enumerate(self.data.get("stations", [])):
            g.add_station(s["name"], i)
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a = g.station_to_number.get(c["source"])
            b = g.station_to_number.get(c["dest"])
            if a is None or b is None:
                continue
            g.add_edge(Edge(a, b, c["distance"], c["line"]))
        self.graph = g

    @property
    def station_to_number(self):
        return self.graph.station_to_number

    def has_station(self, name):
        return name in self.graph.station_to_number

    def line_sequences(self):
        seqs = {}
        for c in self.data.get("connections", []):
            seq = seqs.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)
        return seqs

    def check_data(self):
        """Return (ok, messages)."""
        msgs = []
        ok = True
        stations = self.data.get("stations", [])
        names = {s["name"] for s in stations}
        all_lines = set()
        for s in stations:
            all_lines.update(s.get("lines", []))
        for c in self.data.get("connections", []):
            all_lines.add(c["line"])
        for ln in REQUIRED_LINES:
            if ln not in all_lines:
                ok = False
                msgs.append("Missing line: %s" % ln)
        for c in self.data.get("connections", []):
            if c["source"] not in names or c["dest"] not in names:
                ok = False
                msgs.append("Connection with unknown station: %s - %s" % (c["source"], c["dest"]))
            d = c.get("distance")
            if not isinstance(d, int) or d <= 0 or d > 30000:
                ok = False
                msgs.append("Suspicious distance %r: %s - %s" % (d, c["source"], c["dest"]))
        for name, num in self.graph.station_to_number.items():
            if not self.graph.neighbors(num):
                ok = False
                msgs.append("Isolated station: %s" % name)
        msgs.append("Stations: %d, connections: %d, lines: %d" % (
            len(stations), len(self.data.get("connections", [])), len(all_lines)))
        msgs.append("Data check passed" if ok else "Data check found problems")
        return ok, msgs

    # ----- update mechanisms -----
    def add_line(self, line_name, station_names, distances):
        """Add a line: consecutive stations with the given distances (len = n-1)."""
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        existing = {s["name"]: s for s in self.data["stations"]}
        for n in station_names:
            if n in existing:
                if line_name not in existing[n]["lines"]:
                    existing[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        for a, b, d in zip(station_names, station_names[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": int(d), "line": line_name})
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
        found = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b}:
                c["distance"] = int(distance)
                found = True
        if found:
            self.build_graph()
        return found
