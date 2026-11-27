"""
Data management: building the graph, station mapping, integrity checks and
data update mechanisms (adding lines, modifying stations, updating distances).
"""

import copy

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Xidan", "Guomao"],
    "Line 2": ["Xizhimen", "Dongzhimen"],
    "Line 4": ["Beijing South Railway Station", "Xidan"],
    "Line 5": ["Dongdan", "Yonghegong"],
    "Line 10": ["Guomao", "Haidian Huangzhuang"],
    "Line 13": ["Xizhimen", "Huilongguan"],
}


def normalize_name(name):
    """Normalize a station/line name for lookup (case/whitespace insensitive)."""
    if name is None:
        return ""
    return "".join(str(name).split()).lower()


def build_graph(data):
    """Build (graph, station_to_number, number_to_station) from raw data."""
    graph = Graph()
    station_to_number = {}
    number_to_station = {}
    for st in data.get("stations", []):
        name = st.get("name")
        if name is None or name in station_to_number:
            continue
        num = len(station_to_number)
        station_to_number[name] = num
        number_to_station[num] = name
        graph.add_vertex(num, name)
        graph.set_station_lines(name, st.get("lines", []))
    for c in data.get("connections", []):
        for key in ("source", "dest"):
            name = c.get(key)
            if name not in station_to_number:
                num = len(station_to_number)
                station_to_number[name] = num
                number_to_station[num] = name
                graph.add_vertex(num, name)
                graph.set_station_lines(name, [c.get("line")] if c.get("line") else [])
        dist = c.get("distance")
        if not isinstance(dist, (int, float)) or dist < 0:
            continue
        graph.add_edge(Edge(station_to_number[c["source"]], station_to_number[c["dest"]],
                            dist, c.get("line")))
    return graph, station_to_number, number_to_station


class SubwayDataManager:
    """Manages subway network data and the derived graph."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = copy.deepcopy(data) if data is not None else load_subway_data(path)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.rebuild()

    def rebuild(self):
        self.graph, self.station_to_number, self.number_to_station = build_graph(self.data)
        self._lookup = {normalize_name(n): n for n in self.station_to_number}
        self._line_lookup = {normalize_name(l): l for l in self.all_lines()}

    # ---- lookups ---------------------------------------------------------
    def resolve_station(self, name):
        """Return the official station name matching ``name`` or None."""
        if name in self.station_to_number:
            return name
        return self._lookup.get(normalize_name(name))

    def resolve_line(self, name):
        return self._line_lookup.get(normalize_name(name))

    def all_lines(self):
        lines = []
        seen = set()
        for st in self.data["stations"]:
            for l in st.get("lines", []):
                if l not in seen:
                    seen.add(l)
                    lines.append(l)
        for c in self.data["connections"]:
            l = c.get("line")
            if l and l not in seen:
                seen.add(l)
                lines.append(l)
        return lines

    def line_station_sequence(self, line):
        """Return the station sequence of a line, derived from connections."""
        adj = {}
        for c in self.data["connections"]:
            if c.get("line") == line:
                adj.setdefault(c["source"], []).append(c["dest"])
                adj.setdefault(c["dest"], []).append(c["source"])
        if not adj:
            return []
        ends = [s for s, n in adj.items() if len(set(n)) == 1]
        start = ends[0] if ends else next(iter(adj))
        order, seen, stack = [], set(), [start]
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            order.append(s)
            for n in reversed(adj[s]):
                if n not in seen:
                    stack.append(n)
        return order

    def lines_info(self):
        info = {}
        for line in self.all_lines():
            seq = self.line_station_sequence(line)
            transfers = [s for s in seq if self.graph.is_transfer_station(s)]
            info[line] = {"stations": seq, "transfer_stations": transfers}
        return info

    # ---- integrity check ---------------------------------------------------
    def check_integrity(self):
        errors, warnings = [], []
        stations = self.data["stations"]
        connections = self.data["connections"]
        names = [s.get("name") for s in stations]
        name_set = set(names)

        if not stations:
            errors.append("No station data found")
        if not connections:
            errors.append("No connection data found")

        seen = set()
        for n in names:
            if not n:
                errors.append("Station with empty name found")
            elif n in seen:
                errors.append(f"Duplicate station name: {n}")
            seen.add(n)

        # Line coverage
        line_norm = {normalize_name(l) for l in self.all_lines()}
        for line in MAIN_LINES:
            if normalize_name(line) not in line_norm:
                warnings.append(f"Main line missing from data: {line}")
        for line, reps in REPRESENTATIVE_STATIONS.items():
            for rep in reps:
                if self.resolve_station(rep) is None:
                    warnings.append(f"Representative station '{rep}' of {line} not found")

        # Connections
        pair_dist = {}
        connected = set()
        station_lines = {s.get("name"): set(s.get("lines", [])) for s in stations}
        for i, c in enumerate(connections):
            src, dst, dist, line = c.get("source"), c.get("dest"), c.get("distance"), c.get("line")
            label = f"Connection #{i} ({src} - {dst}, {line})"
            if src not in name_set:
                errors.append(f"{label}: unknown source station '{src}'")
            if dst not in name_set:
                errors.append(f"{label}: unknown destination station '{dst}'")
            if src == dst:
                errors.append(f"{label}: connects a station to itself")
            if not isinstance(dist, (int, float)) or isinstance(dist, bool):
                errors.append(f"{label}: invalid distance {dist!r}")
            elif dist <= 0:
                errors.append(f"{label}: non-positive distance {dist}")
            elif dist < 100:
                warnings.append(f"{label}: suspiciously short distance {dist} m")
            elif dist > 30000:
                warnings.append(f"{label}: suspiciously long distance {dist} m")
            if not line:
                errors.append(f"{label}: missing line")
            else:
                for s in (src, dst):
                    if s in station_lines and line not in station_lines[s]:
                        warnings.append(f"{label}: station '{s}' does not list line '{line}'")
            key = (frozenset((src, dst)), line)
            if key in pair_dist:
                if pair_dist[key] != dist:
                    errors.append(f"{label}: conflicting distances {pair_dist[key]} vs {dist}")
                else:
                    warnings.append(f"{label}: duplicate connection")
            else:
                pair_dist[key] = dist
            connected.add(src)
            connected.add(dst)

        for n in names:
            if n and n not in connected:
                warnings.append(f"Station '{n}' has no connections")

        # Connectivity
        components = 0
        visited = set()
        for v in self.graph.vertices():
            if v in visited or not self.graph.adj(v):
                continue
            components += 1
            stack = [v]
            while stack:
                x = stack.pop()
                if x in visited:
                    continue
                visited.add(x)
                for e in self.graph.adj(x):
                    if e.dest not in visited:
                        stack.append(e.dest)
        if components > 1:
            warnings.append(f"Network is not fully connected ({components} components)")

        stats = {
            "stations": len(stations),
            "connections": len(connections),
            "lines": len(self.all_lines()),
            "transfer_stations": sum(1 for s in stations if len(s.get("lines", [])) > 1),
            "components": components,
        }
        return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}

    @staticmethod
    def format_integrity_report(report):
        lines = ["Data Integrity Check", "=" * 40]
        for k, v in report["stats"].items():
            lines.append(f"{k.replace('_', ' ').capitalize()}: {v}")
        lines.append(f"Errors: {len(report['errors'])}")
        for e in report["errors"]:
            lines.append(f"  [ERROR] {e}")
        lines.append(f"Warnings: {len(report['warnings'])}")
        for w in report["warnings"]:
            lines.append(f"  [WARN] {w}")
        lines.append("Result: " + ("PASSED" if report["ok"] else "FAILED"))
        return "\n".join(lines)

    # ---- updates -----------------------------------------------------------
    def _station_entry(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_line(self, line_name, stations, distances):
        """Add a new line given its station sequence and inter-station distances."""
        if not line_name:
            raise ValueError("Line name required")
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 entries")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance: {d!r}")
        for s in stations:
            entry = self._station_entry(s)
            if entry is None:
                self.data["stations"].append({"name": s, "lines": [line_name]})
            elif line_name not in entry.setdefault("lines", []):
                entry["lines"].append(line_name)
        for a, b, d in zip(stations, stations[1:], distances):
            self.data["connections"].append({"source": a, "dest": b, "distance": d, "line": line_name})
        self.rebuild()

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its line list."""
        official = self.resolve_station(name)
        if official is None:
            raise KeyError(f"Station '{name}' does not exist")
        entry = self._station_entry(official)
        if entry is None:
            entry = {"name": official, "lines": []}
            self.data["stations"].append(entry)
        if lines is not None:
            entry["lines"] = list(lines)
        if new_name and new_name != official:
            if self._station_entry(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == official:
                    c["source"] = new_name
                if c.get("dest") == official:
                    c["dest"] = new_name
        self.rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations. Returns count updated."""
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance: {distance!r}")
        a, b = self.resolve_station(source), self.resolve_station(dest)
        if a is None or b is None:
            raise KeyError("Station does not exist")
        count = 0
        for c in self.data["connections"]:
            if {c.get("source"), c.get("dest")} == {a, b} and (line is None or c.get("line") == line):
                c["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        self.rebuild()
        return count

    def save(self, path=None):
        save_subway_data(self.data, path or self.path)
