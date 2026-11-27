"""Data loading and data management for the Beijing Subway fare system.

The data file ``subway_data.json`` has the structure::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

from models import Edge, Graph

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

MIN_REASONABLE_DISTANCE = 100       # meters
MAX_REASONABLE_DISTANCE = 30000     # meters


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def build_network(data):
    """Build the network graph.

    Returns (graph, station_to_number, number_to_station).
    Each connection is added as a directed edge in its listed direction.
    """
    graph = Graph()
    station_to_number = {}
    number_to_station = {}

    def number_of(name):
        if name not in station_to_number:
            n = len(station_to_number)
            station_to_number[name] = n
            number_to_station[n] = name
            graph.add_vertex(n)
        return station_to_number[name]

    for st in data.get("stations", []):
        name = st.get("name")
        if not name:
            continue
        number_of(name)
        graph.set_station_lines(name, list(st.get("lines", [])))

    for c in data.get("connections", []):
        src = c.get("source")
        dst = c.get("dest")
        if not src or not dst:
            continue
        s = number_of(src)
        d = number_of(dst)
        line = c.get("line", "")
        if src not in graph.station_lines:
            graph.set_station_lines(src, [line] if line else [])
        if dst not in graph.station_lines:
            graph.set_station_lines(dst, [line] if line else [])
        graph.add_edge(Edge(s, d, c.get("distance", 0), line))

    return graph, station_to_number, number_to_station


def check_data_integrity(data):
    """Check data integrity. Returns dict with keys ok, errors, warnings, stats."""
    errors = []
    warnings = []
    stations = data.get("stations", [])
    connections = data.get("connections", [])

    names = set()
    all_lines = set()
    for i, st in enumerate(stations):
        name = st.get("name") if isinstance(st, dict) else None
        if not name:
            errors.append(f"Station #{i} has no name")
            continue
        if name in names:
            warnings.append(f"Duplicate station entry: '{name}'")
        names.add(name)
        lines = st.get("lines", [])
        if not lines:
            warnings.append(f"Station '{name}' has no line affiliation")
        all_lines.update(lines)

    # Coverage of main lines
    for line in MAIN_LINES:
        if line not in all_lines:
            warnings.append(f"Main line '{line}' is not covered by station data")

    connected = set()
    seen = set()
    for i, c in enumerate(connections):
        src, dst = c.get("source"), c.get("dest")
        dist = c.get("distance")
        line = c.get("line")
        if src not in names:
            errors.append(f"Connection #{i}: source station '{src}' does not exist")
        if dst not in names:
            errors.append(f"Connection #{i}: destination station '{dst}' does not exist")
        if src == dst:
            errors.append(f"Connection #{i}: self loop at '{src}'")
        if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist <= 0:
            errors.append(f"Connection #{i} ({src}->{dst}): invalid distance {dist!r}")
        elif dist < MIN_REASONABLE_DISTANCE or dist > MAX_REASONABLE_DISTANCE:
            warnings.append(f"Connection #{i} ({src}->{dst}): suspicious distance {dist} m")
        if not line:
            warnings.append(f"Connection #{i} ({src}->{dst}): missing line")
        key = (src, dst, line)
        if key in seen:
            warnings.append(f"Duplicate connection {src}->{dst} on {line}")
        seen.add(key)
        connected.add(src)
        connected.add(dst)

    for name in sorted(names - connected):
        warnings.append(f"Station '{name}' has no connections")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "stations": len(names),
            "connections": len(connections),
            "lines": len(all_lines),
        },
    }


class DataManager:
    """Data update mechanisms: add lines, modify stations, update distances."""

    def __init__(self, data=None, path=DATA_FILE_PATH):
        self.path = path
        self.data = data if data is not None else load_subway_data(path)

    def _station(self, name):
        for st in self.data["stations"]:
            if st.get("name") == name:
                return st
        return None

    def add_station(self, name, lines):
        st = self._station(name)
        if st is None:
            self.data["stations"].append({"name": name, "lines": list(lines)})
        else:
            for line in lines:
                if line not in st["lines"]:
                    st["lines"].append(line)

    def add_line(self, line_name, station_sequence, distances, bidirectional=True):
        if len(distances) != len(station_sequence) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for name in station_sequence:
            self.add_station(name, [line_name])
        for i, d in enumerate(distances):
            a, b = station_sequence[i], station_sequence[i + 1]
            self.data["connections"].append({"source": a, "dest": b, "distance": int(d), "line": line_name})
            if bidirectional:
                self.data["connections"].append({"source": b, "dest": a, "distance": int(d), "line": line_name})

    def update_station(self, name, new_name=None, lines=None):
        st = self._station(name)
        if st is None:
            raise KeyError(f"Station '{name}' does not exist")
        if lines is not None:
            st["lines"] = list(lines)
        if new_name and new_name != name:
            st["name"] = new_name
            for c in self.data["connections"]:
                if c.get("source") == name:
                    c["source"] = new_name
                if c.get("dest") == name:
                    c["dest"] = new_name

    def update_distance(self, source, dest, distance, line=None, both_directions=True):
        if distance <= 0:
            raise ValueError("Distance must be positive")
        updated = 0
        for c in self.data["connections"]:
            match = (c.get("source") == source and c.get("dest") == dest) or (
                both_directions and c.get("source") == dest and c.get("dest") == source)
            if match and (line is None or c.get("line") == line):
                c["distance"] = int(distance)
                updated += 1
        if not updated:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return updated

    def save(self, path=None):
        with open(path or self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
