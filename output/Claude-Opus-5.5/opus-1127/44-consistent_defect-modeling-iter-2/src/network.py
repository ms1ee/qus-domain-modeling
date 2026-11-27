"""Subway network data management: building the graph, updates, integrity checks."""

import difflib
import json
from dataclasses import dataclass, field
from typing import List

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

MAIN_LINES = {
    "Line 1": ["Line 1", "1号线"],
    "Line 2": ["Line 2", "2号线"],
    "Line 4": ["Line 4", "4号线"],
    "Line 5": ["Line 5", "5号线"],
    "Line 6": ["Line 6", "6号线"],
    "Line 8": ["Line 8", "8号线"],
    "Line 10": ["Line 10", "10号线"],
    "Line 13": ["Line 13", "13号线"],
    "Line 14": ["Line 14", "14号线"],
    "Line 15": ["Line 15", "15号线"],
    "Changping Line": ["Changping", "昌平线"],
    "Yizhuang Line": ["Yizhuang", "亦庄线"],
    "Fangshan Line": ["Fangshan", "房山线"],
    "Airport Line": ["Airport", "机场线"],
}

MAX_REASONABLE_DISTANCE = 50000


@dataclass
class DataIntegrityCheck:
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    messages: List[str] = field(default_factory=list)

    @property
    def valid(self):
        return (self.station_coverage_valid and self.connection_integrity_valid
                and self.distance_accuracy_valid)


class SubwayNetwork:
    def __init__(self, data_source_file=DATA_FILE_PATH, data=None):
        self.data_source_file = data_source_file
        if data is None:
            data = load_subway_data(data_source_file)
        self.stations = []          # list of {"name", "lines"}
        self.connections = []       # list of {"source","dest","distance","line"}
        self.station_to_number = {}
        self.number_to_station = {}
        self._load(data)
        self.build_graph()

    # ---- loading ---------------------------------------------------------
    def _register_station(self, name, lines=None):
        if name not in self.station_to_number:
            num = len(self.station_to_number)
            self.station_to_number[name] = num
            self.number_to_station[num] = name
            self.stations.append({"name": name, "lines": list(lines or [])})
        elif lines:
            for st in self.stations:
                if st["name"] == name:
                    for ln in lines:
                        if ln not in st["lines"]:
                            st["lines"].append(ln)
                    break

    def _load(self, data):
        for st in data.get("stations", []):
            name = st.get("name")
            if name:
                self._register_station(name, st.get("lines", []))
        for c in data.get("connections", []):
            self.connections.append(dict(c))
            for key in ("source", "dest"):
                if c.get(key) is not None and c.get(key) not in self.station_to_number:
                    self._register_station(c[key], [c["line"]] if c.get("line") else [])

    def build_graph(self):
        g = Graph()
        for st in self.stations:
            g.add_vertex(self.station_to_number[st["name"]])
            g.set_station_lines(st["name"], st["lines"])
        for c in self.connections:
            try:
                s = self.station_to_number[c["source"]]
                d = self.station_to_number[c["dest"]]
                dist = c["distance"]
            except (KeyError, TypeError):
                continue
            g.add_edge(Edge(s, d, dist, c.get("line")))
        self.graph = g
        # adjacency dictionary representation (station number -> [(dest, distance, line)])
        self.graph_dict = {v: [(e.dest, e.distance, e.line) for e in g.adj(v)] for v in g.vertices()}
        return g

    # ---- lookup ----------------------------------------------------------
    def station_names(self):
        return list(self.station_to_number.keys())

    def resolve_station(self, name):
        """Return (resolved name or None, exact match flag)."""
        name = (name or "").strip()
        if not name:
            return None, False
        if name in self.station_to_number:
            return name, True
        lowered = {n.lower(): n for n in self.station_to_number}
        if name.lower() in lowered:
            return lowered[name.lower()], True
        for suffix in ("站", " Station", " station"):
            if name.endswith(suffix) and name[: -len(suffix)] in self.station_to_number:
                return name[: -len(suffix)], True
        matches = difflib.get_close_matches(name, self.station_names(), n=1, cutoff=0.6)
        if matches:
            return matches[0], False
        return None, False

    def all_lines(self):
        lines = []
        for st in self.stations:
            for ln in st["lines"]:
                if ln not in lines:
                    lines.append(ln)
        for c in self.connections:
            ln = c.get("line")
            if ln and ln not in lines:
                lines.append(ln)
        return lines

    # ---- updates ---------------------------------------------------------
    def add_line(self, line_name, station_sequence, distances, bidirectional=True):
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("distances must have exactly len(stations) - 1 entries")
        for name in station_sequence:
            self._register_station(name, [line_name])
        for a, b, d in zip(station_sequence, station_sequence[1:], distances):
            if d is None or d <= 0:
                raise ValueError(f"Invalid distance between {a} and {b}: {d}")
            self.connections.append({"source": a, "dest": b, "distance": d, "line": line_name})
            if bidirectional:
                self.connections.append({"source": b, "dest": a, "distance": d, "line": line_name})
        self.build_graph()

    def update_station(self, name, new_name=None, lines=None):
        if name not in self.station_to_number:
            raise KeyError(f"Station '{name}' does not exist")
        for st in self.stations:
            if st["name"] == name:
                if lines is not None:
                    st["lines"] = list(lines)
                if new_name and new_name != name:
                    if new_name in self.station_to_number:
                        raise ValueError(f"Station '{new_name}' already exists")
                    st["name"] = new_name
                    num = self.station_to_number.pop(name)
                    self.station_to_number[new_name] = num
                    self.number_to_station[num] = new_name
                    for c in self.connections:
                        if c.get("source") == name:
                            c["source"] = new_name
                        if c.get("dest") == name:
                            c["dest"] = new_name
                break
        self.build_graph()

    def update_distance(self, source, dest, distance, line=None, bidirectional=True):
        if distance is None or distance <= 0:
            raise ValueError(f"Invalid distance: {distance}")
        updated = 0
        for c in self.connections:
            match = (c.get("source") == source and c.get("dest") == dest) or \
                    (bidirectional and c.get("source") == dest and c.get("dest") == source)
            if match and (line is None or c.get("line") == line):
                c["distance"] = distance
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        self.build_graph()
        return updated

    def to_dict(self):
        return {"stations": [dict(s) for s in self.stations],
                "connections": [dict(c) for c in self.connections]}

    def save(self, path=None):
        path = path or self.data_source_file
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    # ---- integrity -------------------------------------------------------
    def check_integrity(self):
        result = DataIntegrityCheck()
        lines = self.all_lines()
        for main, aliases in MAIN_LINES.items():
            found = any(any(alias.lower() == ln.lower() or
                            (len(alias) > 6 and alias.lower() in ln.lower()) or
                            (alias.endswith("线") and alias in ln)
                            for alias in aliases) for ln in lines)
            if not found:
                result.station_coverage_valid = False
                result.messages.append(f"Main line missing: {main}")
        if not self.stations:
            result.station_coverage_valid = False
            result.messages.append("No station data")

        seen = set()
        for i, c in enumerate(self.connections):
            s, d = c.get("source"), c.get("dest")
            if s not in self.station_to_number or d not in self.station_to_number:
                result.connection_integrity_valid = False
                result.messages.append(f"Connection #{i} references unknown station")
            if s == d:
                result.connection_integrity_valid = False
                result.messages.append(f"Connection #{i} is a self-loop at '{s}'")
            key = (s, d, c.get("line"))
            if key in seen:
                result.messages.append(f"Duplicate connection {s} -> {d} ({c.get('line')})")
            seen.add(key)
            dist = c.get("distance")
            if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0 \
                    or dist > MAX_REASONABLE_DISTANCE:
                result.distance_accuracy_valid = False
                result.messages.append(f"Connection #{i} {s} -> {d} has invalid distance {dist!r}")
        connected = set()
        for c in self.connections:
            connected.add(c.get("source"))
            connected.add(c.get("dest"))
        for st in self.stations:
            if st["name"] not in connected:
                result.connection_integrity_valid = False
                result.messages.append(f"Station '{st['name']}' has no connections")
        return result
