"""Network construction, integrity checks and updates."""
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": [], "2号线": [], "4号线": [], "5号线": [], "6号线": [], "8号线": [],
    "10号线": [], "13号线": [], "14号线": [], "15号线": [],
}


class SubwayNetwork:
    def __init__(self, data):
        self.data = data
        self.build()

    def build(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        for s in self.data.get("stations", []):
            self.add_station(s["name"], s.get("lines", []))
        for c in self.data.get("connections", []):
            self._connect(c["source"], c["dest"], c["distance"], c["line"])

    def add_station(self, name, lines):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
        self.graph.set_station_lines(name, lines)

    def _connect(self, a, b, d, line):
        if a not in self.station_to_number or b not in self.station_to_number:
            return False
        self.graph.add_edge(Edge(self.station_to_number[a], self.station_to_number[b], d, line))
        return True

    # --- update mechanisms ---
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distance count mismatch")
        for s in stations:
            lines = list(self.graph.station_lines.get(s, []))
            if line not in lines:
                lines.append(line)
            self.add_station(s, lines)
        for a, b, d in zip(stations, stations[1:], distances):
            self._connect(a, b, d, line)

    def modify_station(self, name, lines):
        if name not in self.station_to_number:
            raise KeyError(name)
        self.graph.set_station_lines(name, lines)

    def update_distance(self, a, b, distance, line=None):
        if distance <= 0:
            raise ValueError("distance must be positive")
        na, nb = self.station_to_number[a], self.station_to_number[b]
        found = False
        for u, v in ((na, nb), (nb, na)):
            for e in self.graph.adj[u]:
                if e.dest == v and (line is None or e.line == line):
                    e.distance = e.weight = distance
                    found = True
        if not found:
            raise KeyError("no such connection")

    # --- integrity ---
    def check_integrity(self):
        problems = []
        lines = set()
        for ls in self.graph.station_lines.values():
            lines.update(ls)
        for ln in REPRESENTATIVE:
            if ln not in lines:
                problems.append(f"Line missing: {ln}")
        names = set(self.station_to_number)
        for c in self.data.get("connections", []):
            if c["source"] not in names or c["dest"] not in names:
                problems.append(f"Connection with unknown station: {c['source']} - {c['dest']}")
            if not isinstance(c["distance"], (int, float)) or c["distance"] <= 0:
                problems.append(f"Bad distance: {c['source']} - {c['dest']}")
        for name, n in self.station_to_number.items():
            if not self.graph.adj.get(n):
                problems.append(f"Isolated station: {name}")
        return problems
