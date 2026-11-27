"""Subway network data management: graph building, integrity checks, updates."""

from models import Edge, Graph

REPRESENTATIVE_STATIONS = [
    "Xidan", "Guomao", "Dongzhimen", "Xizhimen", "Beijing Railway Station",
    "Haidian Huangzhuang", "Songjiazhuang", "Zhichunlu",
]

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]


class SubwayNetwork:
    """Holds station mapping (station_to_number) and graph."""

    def __init__(self, data=None):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.lines = {}
        if data:
            self.load(data)

    def _ensure_station(self, name, lines=None):
        if name not in self.station_to_number:
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            self.graph.add_vertex(num)
            self.graph.set_station_lines(name, lines or [])
        elif lines:
            existing = self.graph.station_lines.get(name, [])
            for ln in lines:
                if ln not in existing:
                    existing.append(ln)
            self.graph.set_station_lines(name, existing)
        return self.station_to_number[name]

    def load(self, data):
        for st in data.get("stations", []):
            self._ensure_station(st["name"], st.get("lines", []))
            for ln in st.get("lines", []):
                self.lines.setdefault(ln, [])
                if st["name"] not in self.lines[ln]:
                    self.lines[ln].append(st["name"])
        for c in data.get("connections", []):
            self.add_connection(c["source"], c["dest"], c["distance"], c.get("line", ""))

    def add_connection(self, source, dest, distance, line):
        s = self._ensure_station(source, [line] if line else None)
        d = self._ensure_station(dest, [line] if line else None)
        self.graph.add_edge(Edge(s, d, distance, line))
        if line:
            seq = self.lines.setdefault(line, [])
            for n in (source, dest):
                if n not in seq:
                    seq.append(n)

    # ---- data update mechanisms ----
    def add_line(self, line_name, stations, distances, bidirectional=True):
        """Add a new line: stations in order and distances between consecutive ones."""
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have exactly len(stations)-1 entries")
        for a, b, dist in zip(stations, stations[1:], distances):
            self.add_connection(a, b, dist, line_name)
            if bidirectional:
                self.add_connection(b, a, dist, line_name)

    def modify_station(self, old_name, new_name=None, lines=None):
        if old_name not in self.station_to_number:
            raise KeyError(f"Station '{old_name}' does not exist")
        num = self.station_to_number[old_name]
        cur_lines = self.graph.station_lines.pop(old_name, [])
        if new_name and new_name != old_name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            del self.station_to_number[old_name]
            self.station_to_number[new_name] = num
            self.number_to_station[num] = new_name
            for seq in self.lines.values():
                for i, n in enumerate(seq):
                    if n == old_name:
                        seq[i] = new_name
        name = self.number_to_station[num]
        self.graph.set_station_lines(name, lines if lines is not None else cur_lines)

    def update_distance(self, source, dest, distance, line=None):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        s = self.station_to_number.get(source)
        d = self.station_to_number.get(dest)
        if s is None or d is None:
            raise KeyError("Unknown station")
        updated = 0
        for e in self.graph.adj.get(s, []):
            if e.dest == d and (line is None or e.line == line):
                e.distance = distance
                e.weight = distance
                updated += 1
        if updated == 0:
            raise KeyError(f"No connection from '{source}' to '{dest}'")
        return updated

    # ---- integrity check ----
    def check_integrity(self, data=None):
        """Return (ok, list of messages)."""
        msgs = []
        ok = True
        names = set(self.station_to_number)
        present_lines = set(self.lines)
        missing_lines = [ln for ln in MAIN_LINES if ln not in present_lines]
        if missing_lines:
            msgs.append("Warning: main lines missing: " + ", ".join(missing_lines))
        missing_st = [s for s in REPRESENTATIVE_STATIONS if s not in names]
        if missing_st:
            msgs.append("Warning: representative stations missing: " + ", ".join(missing_st))
        else:
            msgs.append("Representative station coverage: OK")
        if data is not None:
            declared = {s["name"] for s in data.get("stations", [])}
            for c in data.get("connections", []):
                for key in ("source", "dest"):
                    if c.get(key) not in declared:
                        ok = False
                        msgs.append(f"Error: connection references undeclared station '{c.get(key)}'")
                dist = c.get("distance")
                if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
                    ok = False
                    msgs.append(f"Error: invalid distance {dist!r} for {c.get('source')} -> {c.get('dest')}")
                elif dist > 30000:
                    msgs.append(f"Warning: unusually long distance {dist} m for {c.get('source')} -> {c.get('dest')}")
        isolated = [self.number_to_station[v] for v in self.graph.vertices()
                    if not self.graph.adj[v] and not any(e.dest == v for e in self.graph.edges)]
        if isolated:
            ok = False
            msgs.append("Error: isolated stations: " + ", ".join(sorted(isolated)))
        else:
            msgs.append("Connection integrity: OK")
        msgs.append(f"Stations: {len(names)}, connections: {self.graph.E}, lines: {len(present_lines)}")
        return ok, msgs
