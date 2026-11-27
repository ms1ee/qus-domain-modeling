"""Network building, data checks and data updates."""
import difflib

from models import Edge, Graph


class SubwayNetwork:
    def __init__(self, data):
        self.data = data
        self.build()

    def build(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        for s in self.data.get("stations", []):
            self._ensure(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a = self._ensure(c["source"])
            b = self._ensure(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))

    def _ensure(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number) + 1
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
        return self.station_to_number[name]

    def match_station(self, name):
        """Return (matched_name, exact)."""
        if name in self.station_to_number:
            return name, True
        m = difflib.get_close_matches(name, list(self.station_to_number), n=1, cutoff=0.5)
        if not m:
            m = [k for k in self.station_to_number if name and (name in k or k in name)][:1]
        return (m[0] if m else None), False

    def lines(self):
        return sorted({c["line"] for c in self.data.get("connections", [])})

    # ---- data updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: meters between consecutive stations (bidirectional)."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances length must be len(stations)-1")
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
        self.build()

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
                self.build()
                return True
        return False

    def update_distance(self, a, b, distance, line=None):
        ok = False
        for c in self.data["connections"]:
            if c["source"] == a and c["dest"] == b and (line is None or c["line"] == line):
                c["distance"] = distance
                ok = True
        if ok:
            self.build()
        return ok

    # ---- integrity ----
    def check_data(self):
        problems = []
        names = {s["name"] for s in self.data.get("stations", [])}
        if not names:
            problems.append("No station data")
        conns = self.data.get("connections", [])
        if not conns:
            problems.append("No connection data")
        for s in self.data.get("stations", []):
            if not s.get("lines"):
                problems.append("Station without lines: %s" % s["name"])
        for c in conns:
            for k in ("source", "dest"):
                if c[k] not in names:
                    problems.append("Connection references unknown station: %s" % c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0:
                problems.append("Invalid distance %s-%s: %r" % (c["source"], c["dest"], d))
            elif d > 20000:
                problems.append("Suspicious distance %s-%s: %s" % (c["source"], c["dest"], d))
        connected = {c["source"] for c in conns} | {c["dest"] for c in conns}
        for n in sorted(names - connected):
            problems.append("Station without connections: %s" % n)
        return problems
