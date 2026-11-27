"""Network data management and integrity checks."""
import difflib

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

REPRESENTATIVE = {
    "Line 1": "Tiananmen East",
}


class DataManager:
    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.graph = Graph()
        self.lines = {}
        self._build()

    def _build(self):
        g = Graph()
        for i, s in enumerate(self.data.get("stations", [])):
            g.add_station(i, s["name"])
            g.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in g.station_to_number:
                    g.add_station(len(g.station_to_number), n)
                    g.set_station_lines(n, [c["line"]])
            g.add_edge(Edge(g.station_to_number[c["source"]], g.station_to_number[c["dest"]],
                            c["distance"], c["line"]))
        self.graph = g
        lines = {}
        for c in self.data.get("connections", []):
            seq = lines.setdefault(c["line"], [])
            for n in (c["source"], c["dest"]):
                if n not in seq:
                    seq.append(n)
        self.lines = lines

    @property
    def station_names(self):
        return list(self.graph.station_to_number)

    def find_station(self, name):
        """Return (matched_name or None, exact)."""
        name = name.strip()
        if name in self.graph.station_to_number:
            return name, True
        m = difflib.get_close_matches(name, self.station_names, n=1, cutoff=0.5)
        return (m[0] if m else None), False

    # ---- updates ----
    def add_line(self, line_name, stations, distances):
        """Add a bidirectional line; distances has len(stations)-1 items."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
            self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line_name})
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line_name not in known[n]["lines"]:
                    known[n]["lines"].append(line_name)
            else:
                self.data["stations"].append({"name": n, "lines": [line_name]})
        self._build()

    def update_station(self, old_name, new_name):
        for s in self.data["stations"]:
            if s["name"] == old_name:
                s["name"] = new_name
        for c in self.data["connections"]:
            if c["source"] == old_name:
                c["source"] = new_name
            if c["dest"] == old_name:
                c["dest"] = new_name
        self._build()

    def update_distance(self, a, b, distance, line=None):
        hit = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                hit = True
        if hit:
            self._build()
        return hit

    # ---- checks ----
    def check_data(self):
        """Return (ok, list of messages)."""
        issues = []
        names = set(self.graph.station_to_number)
        for line in ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
                     "Line 13", "Line 14", "Line 15"]:
            if line not in self.lines:
                issues.append("Missing line: %s" % line)
        for s in self.data["stations"]:
            if not s.get("lines"):
                issues.append("Station without line: %s" % s["name"])
        for c in self.data["connections"]:
            if c["source"] not in names or c["dest"] not in names:
                issues.append("Connection with unknown station: %s-%s" % (c["source"], c["dest"]))
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                issues.append("Bad distance: %s-%s" % (c["source"], c["dest"]))
            if c["source"] == c["dest"]:
                issues.append("Self loop at %s" % c["source"])
        for n, num in self.graph.station_to_number.items():
            has_in = any(e.dest == num for e in self.graph.edges())
            if not self.graph.neighbors(num) and not has_in:
                issues.append("Isolated station: %s" % n)
        return not issues, issues
