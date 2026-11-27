"""Data management: build graph, validate, update."""
from data_loader import load_subway_data, DATA_FILE_PATH
from models import Graph, Edge
from pathfinding import ShortestPath

REPRESENTATIVE = {
    "Line 1": "Tian'anmen East", "Line 2": "Xizhimen", "Line 4": "Xidan",
    "Line 10": "Guomao", "Line 13": "Wudaokou",
}


class SubwaySystem:
    def __init__(self, path=DATA_FILE_PATH):
        self.data = load_subway_data(path)
        self.build()

    def build(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        for s in self.data.get("stations", []):
            self._ensure(s["name"])
            self.graph.set_station_lines(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            a, b = self._ensure(c["source"]), self._ensure(c["dest"])
            self.graph.add_edge(Edge(a, b, c["distance"], c["line"]))

    def _ensure(self, name):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
            self.graph.station_lines.setdefault(name, [])
        return self.station_to_number[name]

    def lines(self):
        return sorted({c["line"] for c in self.data.get("connections", [])})

    def find_route(self, start, end, config=None):
        sp = ShortestPath(self.graph, self.station_to_number[start], config)
        t = self.station_to_number[end]
        if t not in sp.dist_to:
            return None
        nodes, edges = sp.path_with_edges(t)
        return {"nodes": nodes, "edges": edges, "distance": sp.dist_to[t],
                "transfers": sp.get_transfer_count(t)}

    # ---- updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: list of len(stations)-1."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances length mismatch")
        known = {s["name"]: s for s in self.data["stations"]}
        for n in stations:
            if n in known:
                if line not in known[n]["lines"]:
                    known[n]["lines"].append(line)
            else:
                self.data["stations"].append({"name": n, "lines": [line]})
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": d, "line": line})
        self.build()

    def update_station(self, name, lines):
        for s in self.data["stations"]:
            if s["name"] == name:
                s["lines"] = list(lines)
                self.build()
                return True
        return False

    def update_distance(self, a, b, distance, line=None):
        ok = False
        for c in self.data["connections"]:
            if {c["source"], c["dest"]} == {a, b} and (line is None or c["line"] == line):
                c["distance"] = distance
                ok = True
        if ok:
            self.build()
        return ok

    # ---- checks ----
    def check_data(self):
        problems = []
        names = {s["name"] for s in self.data["stations"]}
        lines = set(self.lines())
        for ln, st in REPRESENTATIVE.items():
            if ln in lines and st not in names:
                problems.append("Representative station '%s' of %s missing" % (st, ln))
        for c in self.data["connections"]:
            for k in ("source", "dest"):
                if c[k] not in names:
                    problems.append("Connection references unknown station '%s'" % c[k])
            d = c.get("distance")
            if not isinstance(d, (int, float)) or d <= 0 or d > 20000:
                problems.append("Suspicious distance %s between %s and %s" % (d, c["source"], c["dest"]))
        connected = set()
        for c in self.data["connections"]:
            connected.add(c["source"]); connected.add(c["dest"])
        for n in names - connected:
            problems.append("Station '%s' has no connections" % n)
        return problems
