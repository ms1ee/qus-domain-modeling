"""Network building, integrity check and data updates."""
from models import Edge, Graph

REPRESENTATIVE = {
    "1号线": [], "2号线": [], "4号线": [], "5号线": [],
}
MAIN_LINES = ["Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
              "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
              "Fangshan Line", "Airport Line"]


class SubwayNetwork:
    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.connections = []
        for s in data.get("stations", []):
            self.add_station(s["name"], s.get("lines", []))
        for c in data.get("connections", []):
            self.add_connection(c["source"], c["dest"], c["distance"], c.get("line", ""))

    def add_station(self, name, lines):
        if name not in self.station_to_number:
            n = len(self.station_to_number)
            self.station_to_number[name] = n
            self.number_to_station[n] = name
            self.graph.add_node(n)
        self.graph.set_station_lines(name, lines)

    def add_connection(self, a, b, dist, line):
        for nm in (a, b):
            if nm not in self.station_to_number:
                self.add_station(nm, [line] if line else [])
        for nm in (a, b):
            ls = self.graph.station_lines.setdefault(nm, [])
            if line and line not in ls:
                ls.append(line)
        self.graph.add_edge(Edge(self.station_to_number[a], self.station_to_number[b], dist, line))
        self.connections.append((a, b, dist, line))

    # ---- updates ----
    def add_line(self, line, stations, distances):
        """stations: ordered names; distances: len(stations)-1 meters."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have len(stations)-1 items")
        for nm in stations:
            self.add_station(nm, list(self.graph.station_lines.get(nm, [])))
        for i, dist in enumerate(distances):
            self.add_connection(stations[i], stations[i + 1], dist, line)

    def modify_station(self, name, lines):
        if name not in self.station_to_number:
            raise KeyError(name)
        self.graph.set_station_lines(name, lines)

    def update_distance(self, a, b, distance, line=None):
        if a not in self.station_to_number or b not in self.station_to_number:
            raise KeyError("unknown station")
        return self.graph.update_distance(self.station_to_number[a],
                                          self.station_to_number[b], distance, line)

    # ---- check ----
    def check_data(self):
        """Return list of problem strings (empty if OK)."""
        problems = []
        lines_present = set()
        for ls in self.graph.station_lines.values():
            lines_present.update(ls)
        for l in MAIN_LINES:
            if l not in lines_present:
                problems.append("Line missing: %s" % l)
        for nm, n in self.station_to_number.items():
            if not self.graph.neighbors(n):
                problems.append("Station without connections: %s" % nm)
        for a, b, d, l in self.connections:
            if not isinstance(d, (int, float)) or d <= 0 or d > 30000:
                problems.append("Suspicious distance %s-%s (%s): %r" % (a, b, l, d))
            if a == b:
                problems.append("Self loop at %s" % a)
        # connectivity
        if self.graph.nodes():
            seen = {self.graph.nodes()[0]}
            stack = list(seen)
            while stack:
                x = stack.pop()
                for e in self.graph.neighbors(x):
                    if e.dest not in seen:
                        seen.add(e.dest)
                        stack.append(e.dest)
            if len(seen) != self.graph.V():
                problems.append("Network not fully connected: %d of %d stations reachable"
                                % (len(seen), self.graph.V()))
        return problems
