"""
Subway network model and data management (loading, lookup, updates).
"""

import copy
import difflib
import json
import re

from data_loader import DATA_FILE_PATH, build_graph_dict, load_subway_data
from models import Edge, Graph, Line, Station


def normalize_name(name):
    """Normalise a station name for lenient lookup."""
    text = str(name).strip().lower()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def _compact(name):
    return re.sub(r"[\s'\-_.]", "", normalize_name(name))


def _strip_suffix(name):
    text = normalize_name(name)
    for suffix in (" station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)].strip()
    return text


class SubwayNetwork:
    """The Beijing Subway network: stations, lines, connections and graph.

    Attributes:
        data_source:        path of the data file (None if built from a dict)
        station_to_number:  station name -> station number
        number_to_station:  station number -> station name
        station_lines:      station name -> list of lines
        graph:              :class:`models.Graph`
        graph_dict:         number -> [(neighbor, distance, line), ...]
        lines:              line name -> ordered station list
    """

    def __init__(self, data=None, data_source=None):
        if data is None:
            data_source = data_source or DATA_FILE_PATH
            data = load_subway_data(data_source)
        self.data_source = data_source
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self._build()

    @classmethod
    def from_file(cls, path=None):
        return cls(data_source=path or DATA_FILE_PATH)

    # ------------------------------------------------------------- building
    def _build(self):
        self.station_lines = {}
        for st in self.data["stations"]:
            if not isinstance(st, dict):
                continue
            name = str(st.get("name", "")).strip()
            if not name:
                continue
            lines = self.station_lines.setdefault(name, [])
            for line in st.get("lines", []) or []:
                if line not in lines:
                    lines.append(line)
        for conn in self.data["connections"]:
            if not isinstance(conn, dict):
                continue
            for key in ("source", "dest"):
                name = str(conn.get(key, "")).strip()
                if not name:
                    continue
                lines = self.station_lines.setdefault(name, [])
                line = conn.get("line")
                if line and line not in lines:
                    lines.append(line)

        self.station_to_number = {name: i for i, name in enumerate(self.station_lines)}
        self.number_to_station = {i: name for name, i in self.station_to_number.items()}

        self.graph = Graph()
        for name, number in self.station_to_number.items():
            self.graph.add_vertex(number, name)
            self.graph.set_station_lines(name, self.station_lines[name])

        for conn in self.data["connections"]:
            if not isinstance(conn, dict):
                continue
            source = str(conn.get("source", "")).strip()
            dest = str(conn.get("dest", "")).strip()
            if source not in self.station_to_number or dest not in self.station_to_number:
                continue
            if source == dest:
                continue
            try:
                distance = int(conn.get("distance"))
            except (TypeError, ValueError):
                continue
            if distance < 0:
                continue
            self.graph.add_edge(Edge(self.station_to_number[source], self.station_to_number[dest],
                                     distance, conn.get("line")))

        self.graph_dict = build_graph_dict(self.data, self.station_to_number)
        self.lines = self._build_line_sequences()
        self._lookup = {}
        self._compact_lookup = {}
        self._suffix_lookup = {}
        for name in self.station_to_number:
            self._lookup.setdefault(normalize_name(name), name)
            self._compact_lookup.setdefault(_compact(name), name)
            self._suffix_lookup.setdefault(_strip_suffix(name), name)

    def _build_line_sequences(self):
        """Derive ordered station sequences of each line from the connections."""
        order = []
        adjacency = {}
        for name, lines in self.station_lines.items():
            for line in lines:
                if line not in adjacency:
                    adjacency[line] = {}
                    order.append(line)
        first_seen = {}
        for conn in self.data["connections"]:
            if not isinstance(conn, dict):
                continue
            line = conn.get("line")
            s = str(conn.get("source", "")).strip()
            d = str(conn.get("dest", "")).strip()
            if not line or not s or not d or s == d:
                continue
            if line not in adjacency:
                adjacency[line] = {}
                order.append(line)
            adj = adjacency[line]
            adj.setdefault(s, [])
            adj.setdefault(d, [])
            if d not in adj[s]:
                adj[s].append(d)
            if s not in adj[d]:
                adj[d].append(s)
            seen = first_seen.setdefault(line, [])
            for n in (s, d):
                if n not in seen:
                    seen.append(n)

        sequences = {}
        for line in order:
            adj = adjacency[line]
            seen = first_seen.get(line, [])
            if not seen:
                sequences[line] = [n for n, ls in self.station_lines.items() if line in ls]
                continue
            ends = [n for n in seen if len(adj[n]) == 1]
            start = ends[0] if ends else seen[0]
            visited = []
            visited_set = set()
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited_set:
                    continue
                visited.append(node)
                visited_set.add(node)
                for nb in reversed(adj[node]):
                    if nb not in visited_set:
                        stack.append(nb)
            for n in seen:
                if n not in visited_set:
                    visited.append(n)
                    visited_set.add(n)
            sequences[line] = visited
        return sequences

    # --------------------------------------------------------------- lookups
    @property
    def line_names(self):
        return list(self.lines.keys())

    def get_line(self, name):
        if name not in self.lines:
            return None
        return Line(name=name, station_sequence=list(self.lines[name]))

    def get_station(self, name):
        canonical = self.resolve_station(name)
        if canonical is None:
            return None
        return Station(name=canonical, number=self.station_to_number[canonical],
                       lines=list(self.station_lines[canonical]))

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer_station(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def transfer_stations(self):
        return [n for n, lines in self.station_lines.items() if len(lines) > 1]

    def resolve_station(self, name):
        """Map user input to the official station name, or return None."""
        if name is None:
            return None
        raw = str(name).strip()
        if not raw:
            return None
        if raw in self.station_to_number:
            return raw
        key = normalize_name(raw)
        if key in self._lookup:
            return self._lookup[key]
        compact = _compact(raw)
        if compact in self._compact_lookup:
            return self._compact_lookup[compact]
        stripped = _strip_suffix(raw)
        if stripped in self._lookup:
            return self._lookup[stripped]
        if stripped in self._suffix_lookup:
            return self._suffix_lookup[stripped]
        return None

    def suggest_stations(self, name, limit=3):
        """Return close matches to a possibly misspelt station name."""
        key = normalize_name(name)
        matches = difflib.get_close_matches(key, list(self._lookup.keys()), n=limit, cutoff=0.6)
        return [self._lookup[m] for m in matches]

    def resolve_line(self, name):
        """Map a user supplied line name to an existing line name (or None)."""
        if name in self.lines:
            return name
        key = normalize_name(name)
        for line in self.lines:
            if normalize_name(line) == key or _compact(line) == _compact(name):
                return line
        return None

    # ---------------------------------------------------------- data updates
    def _ensure_station(self, name, line=None):
        for st in self.data["stations"]:
            if isinstance(st, dict) and str(st.get("name", "")).strip() == name:
                if line:
                    lines = st.setdefault("lines", [])
                    if line not in lines:
                        lines.append(line)
                return
        self.data["stations"].append({"name": name, "lines": [line] if line else []})

    def add_station(self, name, lines=None):
        """Add a new station (or extend its lines)."""
        name = str(name).strip()
        if not name:
            raise ValueError("Station name cannot be empty")
        if not lines:
            self._ensure_station(name)
        for line in lines or []:
            self._ensure_station(name, line)
        self._build()

    def add_connection(self, source, dest, distance, line):
        """Add a new bidirectional connection between two stations."""
        self._validate_distance(distance)
        source, dest = str(source).strip(), str(dest).strip()
        if source == dest:
            raise ValueError("A connection cannot link a station to itself")
        self._ensure_station(source, line)
        self._ensure_station(dest, line)
        self.data["connections"].append(
            {"source": source, "dest": dest, "distance": int(distance), "line": line})
        self._build()

    def add_line(self, line_name, station_names, distances):
        """Add a new line given its station sequence and inter-station distances."""
        if not line_name:
            raise ValueError("Line name cannot be empty")
        station_names = [str(s).strip() for s in station_names]
        if len(station_names) < 2:
            raise ValueError("A line requires at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            self._validate_distance(d)
        for name in station_names:
            if not name:
                raise ValueError("Station name cannot be empty")
            self._ensure_station(name, line_name)
        for a, b, d in zip(station_names, station_names[1:], distances):
            if a == b:
                raise ValueError("Consecutive stations must differ")
            self.data["connections"].append({"source": a, "dest": b, "distance": int(d), "line": line_name})
        self._build()

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        canonical = self.resolve_station(name)
        if canonical is None:
            raise LookupError(f"Station '{name}' does not exist")
        if new_name is not None:
            new_name = str(new_name).strip()
            if not new_name:
                raise ValueError("New station name cannot be empty")
            if new_name != canonical and new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
        for st in self.data["stations"]:
            if isinstance(st, dict) and str(st.get("name", "")).strip() == canonical:
                if new_name:
                    st["name"] = new_name
                if lines is not None:
                    st["lines"] = list(lines)
        if new_name:
            for conn in self.data["connections"]:
                if not isinstance(conn, dict):
                    continue
                for key in ("source", "dest"):
                    if str(conn.get(key, "")).strip() == canonical:
                        conn[key] = new_name
        self._build()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        :returns: number of updated connections
        """
        self._validate_distance(distance)
        a, b = self.resolve_station(source), self.resolve_station(dest)
        if a is None or b is None:
            raise LookupError("Both stations must exist to update a distance")
        updated = 0
        for conn in self.data["connections"]:
            if not isinstance(conn, dict):
                continue
            s, d = str(conn.get("source", "")).strip(), str(conn.get("dest", "")).strip()
            if {s, d} == {a, b} and (line is None or conn.get("line") == line):
                conn["distance"] = int(distance)
                updated += 1
        if not updated:
            raise LookupError(f"No connection between '{a}' and '{b}'")
        self._build()
        return updated

    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Distance must be a positive number of meters, got {distance!r}")

    def save(self, path=None):
        """Write the (possibly updated) network data back to a JSON file."""
        target = path or self.data_source or DATA_FILE_PATH
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
        return target
