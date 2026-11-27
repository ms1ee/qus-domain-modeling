"""Network building, integrity checks and data updates."""
import difflib

from models import Edge, Graph


class SubwayNetwork:
    def __init__(self, data):
        self.data = data
        self.rebuild()

    def rebuild(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for s in self.data.get("stations", []):
            self._add_station(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            for n in (c["source"], c["dest"]):
                if n not in self.station_to_number:
                    self._add_station(n, [c["line"]])
            self.graph.add_edge(Edge(self.station_to_number[c["source"]],
                                     self.station_to_number[c["dest"]],
                                     c["distance"], c["line"]))

    def _add_station(self, name, lines):
        if name in self.station_to_number:
            return
        num = len(self.station_to_number)
        self.station_to_number[name] = num
        self.number_to_station[num] = name
        self.graph.add_node(num)
        self.graph.set_station_lines(name, lines)

    def match_station(self, name):
        """Return (station, exact) with nearest-name matching, or (None, False)."""
        name = name.strip()
        if name in self.station_to_number:
            return name, True
        if name.endswith("站") and name[:-1] in self.station_to_number:
            return name[:-1], True
        m = difflib.get_close_matches(name, list(self.station_to_number), n=1, cutoff=0.5)
        return (m[0], False) if m else (None, False)

    # ---- updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters; bidirectional."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distance count mismatch")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line not in known[n]["lines"]:
                    known[n]["lines"].append(line)
            else:
                self.data["stations"].append({"name": n, "lines": [line]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line})
            self.data["connections"].append({"source": b, "dest": a, "distance": d, "line": line})
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

    def update_distance(self, source, dest, distance, line=None):
        found = False
        for c in self.data["connections"]:
            if c["source"] == source and c["dest"] == dest and (line is None or c["line"] == line):
                c["distance"] = distance
                found = True
        if found:
            self.rebuild()
        return found

    # ---- check ----
    def check_data(self):
        problems = []
        names = set(s["name"] for s in self.data.get("stations", []))
        if not names:
            problems.append("No stations loaded")
        for c in self.data.get("connections", []):
            if c["source"] not in names or c["dest"] not in names:
                problems.append("Connection refers to unknown station: %s -> %s" % (c["source"], c["dest"]))
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                problems.append("Invalid distance: %s -> %s (%r)" % (c["source"], c["dest"], d))
            elif d > 30000:
                problems.append("Suspicious distance: %s -> %s (%r)" % (c["source"], c["dest"], d))
        connected = set()
        for c in self.data.get("connections", []):
            connected.add(c["source"])
            connected.add(c["dest"])
        for n in sorted(names - connected):
            problems.append("Station has no connections: %s" % n)
        lines = set()
        for s in self.data.get("stations", []):
            lines.update(s.get("lines", []))
        return problems, len(names), len(self.data.get("connections", [])), sorted(lines)
