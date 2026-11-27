"""Data management for the Beijing Subway network.

Responsibilities:
  * load the dataset from subway_data.json and build the Graph,
  * resolve user-entered station and line names to official names,
  * run data integrity checks (coverage, connections, distances),
  * update data (add lines, modify stations, update distances).
"""

import re

from data_loader import load_subway_data, save_subway_data, DATA_FILE_PATH
from models import Graph, Edge, SubwayError, StationNotFoundError

# Lines that must be represented in the network.
REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Tiananmen West", "Guomao"],
    "Line 2": ["Xizhimen", "Jianguomen", "Dongzhimen"],
    "Line 5": ["Dongdan"],
    "Line 10": ["Sanyuanqiao"],
    "Line 13": ["Huilongguan"],
}

# Plausible range of distances between adjacent stations (meters).
MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _normalize(text):
    """Normalize a name for lenient matching (case, spaces, hyphens ignored)."""
    return re.sub(r"[\s\-_'.]", "", str(text)).lower()


class DataManager:
    """Owns the subway dataset and the Graph built from it."""

    def __init__(self, data_file=DATA_FILE_PATH):
        self.data_file = data_file
        self.data = load_subway_data(data_file)
        self.last_check_passed = False
        self.graph = None
        self._name_index = {}
        self.build_graph()

    # -- graph construction -------------------------------------------------

    def build_graph(self):
        """(Re)build the Graph from the current dataset and return it."""
        station_lines = {}
        for entry in self.data["stations"]:
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            lines = station_lines.setdefault(name, [])
            for line in entry.get("lines", []):
                if line not in lines:
                    lines.append(line)

        for conn in self.data["connections"]:
            for key in ("source", "dest"):
                station_lines.setdefault(conn[key], [])
            lines = station_lines[conn["source"]]
            if conn["line"] not in lines:
                lines.append(conn["line"])
            lines = station_lines[conn["dest"]]
            if conn["line"] not in lines:
                lines.append(conn["line"])

        graph = Graph()
        for number, name in enumerate(station_lines):
            graph.add_station(name, number)
        for name, lines in station_lines.items():
            graph.set_station_lines(name, lines)
        for conn in self.data["connections"]:
            source = graph.number_of(conn["source"])
            dest = graph.number_of(conn["dest"])
            graph.add_edge(Edge(source, dest, float(conn["distance"]), conn["line"]))

        self.graph = graph
        self._name_index = {_normalize(name): name for name in station_lines}
        return graph

    # -- name resolution ----------------------------------------------------

    def stations(self):
        """Return all official station names in numbering order."""
        return [self.graph.name_of(n) for n in sorted(self.graph.number_to_station)]

    def lines(self):
        """Return all line names in order of first appearance."""
        result = []
        for name in self.stations():
            for line in self.graph.station_lines.get(name, []):
                if line not in result:
                    result.append(line)
        return result

    def resolve_station(self, text):
        """Return the official station name matching ``text``, or None."""
        if not text:
            return None
        return self._name_index.get(_normalize(text))

    def canonical_line(self, text):
        """Return the official line name matching ``text`` (e.g. '1' -> 'Line 1'), or None."""
        if not text:
            return None
        key = _normalize(text)
        candidates = [key]
        if key.isdigit():
            candidates.append(_normalize(f"Line {key}"))
        for line in self.lines():
            if _normalize(line) in candidates:
                return line
        return None

    # -- data helpers -------------------------------------------------------

    def _find_station_entry(self, name):
        for entry in self.data["stations"]:
            if entry.get("name") == name:
                return entry
        return None

    def _ensure_station_entry(self, name):
        entry = self._find_station_entry(name)
        if entry is None:
            entry = {"name": name, "lines": []}
            self.data["stations"].append(entry)
        return entry

    # -- data updates -------------------------------------------------------

    def add_line(self, line_name, station_names, distances):
        """Add a new line. ``distances`` has one entry per adjacent station pair (meters)."""
        name = (line_name or "").strip()
        if not name:
            raise SubwayError("Line name cannot be empty")
        if self.canonical_line(name) is not None:
            raise SubwayError(f"Line '{name}' already exists")

        stations = [s.strip() for s in station_names if s and str(s).strip()]
        if len(stations) < 2:
            raise SubwayError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise SubwayError("Number of distances must be one less than the number of stations")

        clean_distances = []
        for value in distances:
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise SubwayError(f"Invalid distance: {value!r}") from exc
            if number <= 0:
                raise SubwayError("Distances must be positive")
            clean_distances.append(int(round(number)))

        resolved = []
        for station in stations:
            existing = self.resolve_station(station)
            resolved.append(existing if existing else station)

        for station in resolved:
            entry = self._ensure_station_entry(station)
            if name not in entry["lines"]:
                entry["lines"].append(name)
        for idx in range(len(resolved) - 1):
            self.data["connections"].append({
                "source": resolved[idx],
                "dest": resolved[idx + 1],
                "distance": clean_distances[idx],
                "line": name,
            })
        self.build_graph()

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its lines."""
        canonical = self.resolve_station(name)
        if canonical is None:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        entry = self._ensure_station_entry(canonical)

        if lines is not None:
            cleaned = [str(l).strip() for l in lines if str(l).strip()]
            if not cleaned:
                raise SubwayError("A station must belong to at least one line")
            entry["lines"] = cleaned

        if new_name is not None and new_name.strip() and new_name.strip() != canonical:
            target = new_name.strip()
            existing = self.resolve_station(target)
            if existing is not None and existing != canonical:
                raise SubwayError(f"Station '{existing}' already exists")
            entry["name"] = target
            for conn in self.data["connections"]:
                if conn["source"] == canonical:
                    conn["source"] = target
                if conn["dest"] == canonical:
                    conn["dest"] = target
        self.build_graph()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations; returns the number of connections changed."""
        a = self.resolve_station(source)
        b = self.resolve_station(dest)
        if a is None:
            raise StationNotFoundError(f"Station '{source}' does not exist")
        if b is None:
            raise StationNotFoundError(f"Station '{dest}' does not exist")
        try:
            value = float(distance)
        except (TypeError, ValueError) as exc:
            raise SubwayError(f"Invalid distance: {distance!r}") from exc
        if value <= 0:
            raise SubwayError("Distance must be positive")

        canonical_line = None
        if line is not None:
            canonical_line = self.canonical_line(line)
            if canonical_line is None:
                raise SubwayError(f"Line '{line}' does not exist")

        matches = [
            conn for conn in self.data["connections"]
            if {conn["source"], conn["dest"]} == {a, b}
            and (canonical_line is None or conn["line"] == canonical_line)
        ]
        if not matches:
            raise SubwayError(f"No connection between '{a}' and '{b}'")
        for conn in matches:
            conn["distance"] = int(round(value))
        self.build_graph()
        return len(matches)

    def save(self, path=None):
        """Write the current dataset to ``path`` (default: the original data file)."""
        save_subway_data(self.data, path or self.data_file)

    # -- integrity checks ---------------------------------------------------

    def check_integrity(self):
        """Run data integrity checks.

        Returns (passed, issues) where issues is a list of strings prefixed with
        'ERROR:' or 'WARNING:'. Only errors make the check fail.
        """
        errors = []
        warnings = []
        stations = self.data["stations"]
        connections = self.data["connections"]

        # Station data validity.
        station_lines = {}
        for idx, entry in enumerate(stations):
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"ERROR: station entry #{idx} has no valid name")
                continue
            if name in station_lines:
                errors.append(f"ERROR: duplicate station '{name}'")
            lines = entry.get("lines", [])
            if not lines:
                errors.append(f"ERROR: station '{name}' has no lines")
            station_lines[name] = set(lines)

        # Coverage of main lines and representative stations.
        all_lines = set()
        for lines in station_lines.values():
            all_lines.update(lines)
        for line in REQUIRED_LINES:
            if line not in all_lines:
                warnings.append(f"WARNING: required line '{line}' is not present in the data")
        normalized_names = {_normalize(n) for n in station_lines}
        for line, reps in REPRESENTATIVE_STATIONS.items():
            for rep in reps:
                if _normalize(rep) not in normalized_names:
                    warnings.append(f"WARNING: representative station '{rep}' of {line} is missing")

        # Connection integrity and distance accuracy.
        seen = set()
        adjacency = {name: set() for name in station_lines}
        for idx, conn in enumerate(connections):
            src = conn.get("source")
            dst = conn.get("dest")
            dist = conn.get("distance")
            line = conn.get("line")
            label = f"connection #{idx} ({src} - {dst}, {line})"

            if src not in station_lines:
                errors.append(f"ERROR: {label}: source station is not defined")
            if dst not in station_lines:
                errors.append(f"ERROR: {label}: destination station is not defined")
            if src == dst:
                errors.append(f"ERROR: {label}: station connects to itself")
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                errors.append(f"ERROR: {label}: distance is not numeric")
            elif dist <= 0:
                errors.append(f"ERROR: {label}: distance must be positive")
            elif dist < MIN_PLAUSIBLE_DISTANCE_M or dist > MAX_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"WARNING: {label}: distance {dist} m is outside the plausible range")

            if src in station_lines and line not in station_lines[src]:
                errors.append(f"ERROR: {label}: line is not served by '{src}'")
            if dst in station_lines and line not in station_lines[dst]:
                errors.append(f"ERROR: {label}: line is not served by '{dst}'")

            key = (frozenset((src, dst)), line)
            if key in seen:
                errors.append(f"ERROR: {label}: duplicate connection")
            seen.add(key)

            if src in adjacency and dst in adjacency:
                adjacency[src].add(dst)
                adjacency[dst].add(src)

        # Connectivity.
        for name, neighbours in adjacency.items():
            if not neighbours:
                warnings.append(f"WARNING: station '{name}' has no connections")
        visited = set()
        components = 0
        for name in adjacency:
            if name in visited:
                continue
            components += 1
            stack = [name]
            visited.add(name)
            while stack:
                current = stack.pop()
                for nxt in adjacency[current]:
                    if nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
        if components > 1:
            warnings.append(f"WARNING: network has {components} disconnected components")

        issues = errors + warnings
        passed = not errors
        self.last_check_passed = passed
        return passed, issues
