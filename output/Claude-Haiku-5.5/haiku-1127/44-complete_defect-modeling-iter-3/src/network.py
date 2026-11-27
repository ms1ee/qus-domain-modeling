"""Subway network data management.

``SubwayNetwork`` owns the station, line and connection data, builds the
weighted graph used by the path calculation module, supports data updates
(new lines, station modifications, distance updates) and performs data
integrity checks.
"""

from data_loader import DATA_FILE_PATH, load_subway_data
from models import DataIntegrityReport, Edge, Graph

MIN_DISTANCE_M = 1
MAX_DISTANCE_M = 10000

REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

# Representative stations used to verify coverage of main lines.
REPRESENTATIVE_STATIONS = {
    "Line 1": "Pingguoyuan",
    "Line 2": "Dongzhimen",
    "Line 4": "Xizhimen",
    "Line 5": "Songjiazhuang",
    "Line 6": "Chaoyangmen",
    "Line 8": "Shichahai",
    "Line 10": "Bagou",
    "Line 13": "Xi'erqi",
}


def _dedupe(values):
    """Return a list with duplicates removed and order preserved."""
    return list(dict.fromkeys(str(value) for value in values))


def _validate_distance(distance) -> None:
    """Raise ValueError if the distance is not a positive number."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError(f"Distance must be a number, got {distance!r}")
    if distance <= 0:
        raise ValueError(f"Distance must be positive, got {distance!r}")


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    Args:
        data: Parsed subway data dict. If None, ``subway_data.json`` is loaded.
        data_source: Human-readable description of the data source.
    """

    def __init__(self, data: dict = None, data_source: str = None):
        if data is None:
            data = load_subway_data(DATA_FILE_PATH)
        self.name = "Beijing Subway"
        self.data_source = data_source or DATA_FILE_PATH
        self._stations = {}      # station name -> list of line names
        self._connections = []   # list of dicts: source, dest, distance, line
        self._graph = None
        self._load(data)

    # ------------------------------------------------------------------ loading
    def _load(self, data) -> None:
        """Populate internal structures from the raw data dict."""
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a JSON object")
        stations = data.get("stations")
        connections = data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise ValueError("Subway data must contain 'stations' and 'connections' lists")

        for entry in stations:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise ValueError(f"Malformed station entry: {entry!r}")
            lines = entry.get("lines", [])
            if not isinstance(lines, list):
                raise ValueError(f"Station lines must be a list: {entry!r}")
            name = entry["name"]
            merged = self._stations.get(name, []) + [str(line) for line in lines]
            self._stations[name] = _dedupe(merged)

        for conn in connections:
            if not isinstance(conn, dict):
                raise ValueError(f"Malformed connection entry: {conn!r}")
            for key in ("source", "dest", "distance", "line"):
                if key not in conn:
                    raise ValueError(f"Connection missing field '{key}': {conn!r}")
            if not isinstance(conn["source"], str) or not isinstance(conn["dest"], str):
                raise ValueError(f"Connection endpoints must be strings: {conn!r}")
            if not isinstance(conn["distance"], (int, float)) or isinstance(conn["distance"], bool):
                raise ValueError(f"Connection distance must be numeric: {conn!r}")
            self._connections.append({
                "source": conn["source"],
                "dest": conn["dest"],
                "distance": conn["distance"],
                "line": str(conn["line"]),
            })

    def _invalidate(self) -> None:
        """Discard the cached graph after data changes."""
        self._graph = None

    # ------------------------------------------------------------ graph access
    def _ordered_station_names(self):
        names = list(self._stations)
        seen = set(names)
        for conn in self._connections:
            for key in ("source", "dest"):
                if conn[key] not in seen:
                    seen.add(conn[key])
                    names.append(conn[key])
        return names

    def build_graph(self) -> Graph:
        """Build a new ``Graph`` from the current data.

        Station numbers are assigned here (the caller), in order of first
        appearance in the station list.
        """
        graph = Graph()
        numbers = {}
        for index, name in enumerate(self._ordered_station_names()):
            graph.register_station(name, index)
            numbers[name] = index
            graph.set_station_lines(name, self._stations.get(name, []))
        for conn in self._connections:
            src = numbers[conn["source"]]
            dst = numbers[conn["dest"]]
            if src == dst:
                continue  # self-loops are reported by the integrity check
            graph.add_edge(Edge(src, dst, conn["distance"], conn["line"]))
        return graph

    @property
    def graph(self) -> Graph:
        """The cached weighted graph of the network (built on demand)."""
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    # ---------------------------------------------------------------- queries
    def station_names(self):
        """Return a sorted list of all station names."""
        return sorted(self._ordered_station_names())

    def has_station(self, name: str) -> bool:
        """Return True if the station exists in the network."""
        return name in self._stations or any(
            name in (c["source"], c["dest"]) for c in self._connections)

    def station_lines(self, name: str):
        """Return a copy of the list of lines serving a station."""
        return list(self._stations.get(name, []))

    def line_names(self):
        """Return a sorted list of all line names in the network."""
        lines = set()
        for station_lines in self._stations.values():
            lines.update(station_lines)
        lines.update(conn["line"] for conn in self._connections)
        return sorted(lines)

    def connections(self):
        """Return a copy of the connection records."""
        return [dict(conn) for conn in self._connections]

    # ----------------------------------------------------------- data updates
    def add_line(self, line_name: str, station_sequence, distances) -> None:
        """Add a new line described by its ordered stations and segment distances.

        Args:
            line_name: Name of the new line (must not already exist).
            station_sequence: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations.
        """
        if not line_name or not isinstance(line_name, str):
            raise ValueError("Line name must be a non-empty string")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        stations = list(station_sequence)
        distances = list(distances)
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        for distance in distances:
            _validate_distance(distance)
        for name in stations:
            current = self._stations.setdefault(name, [])
            if line_name not in current:
                current.append(line_name)
        for index, distance in enumerate(distances):
            self._connections.append({
                "source": stations[index],
                "dest": stations[index + 1],
                "distance": distance,
                "line": line_name,
            })
        self._invalidate()

    def modify_station(self, name: str, new_name: str = None, lines=None) -> str:
        """Rename a station and/or replace its list of lines.

        Returns:
            The (possibly new) station name.
        """
        if name not in self._stations and not self.has_station(name):
            raise KeyError(f"Station '{name}' does not exist")
        current = name
        if new_name and new_name != name:
            if self.has_station(new_name):
                raise ValueError(f"Station '{new_name}' already exists")
            self._stations[new_name] = self._stations.pop(name, [])
            for conn in self._connections:
                if conn["source"] == name:
                    conn["source"] = new_name
                if conn["dest"] == name:
                    conn["dest"] = new_name
            current = new_name
        if lines is not None:
            self._stations[current] = _dedupe(lines)
        self._invalidate()
        return current

    def update_distance(self, source: str, dest: str, distance, line: str = None) -> int:
        """Update the distance between two adjacent stations.

        Returns:
            The number of connection records updated.
        """
        _validate_distance(distance)
        updated = 0
        for conn in self._connections:
            pair = {conn["source"], conn["dest"]} == {source, dest}
            if pair and (line is None or conn["line"] == line):
                conn["distance"] = distance
                updated += 1
        if updated == 0:
            raise KeyError(f"No connection found between '{source}' and '{dest}'")
        self._invalidate()
        return updated

    # --------------------------------------------------------- integrity check
    def check_integrity(self) -> DataIntegrityReport:
        """Run data integrity checks and return a ``DataIntegrityReport``."""
        issues = []
        line_set = set(self.line_names())

        # Coverage of main lines and representative stations.
        for line in REQUIRED_MAIN_LINES:
            if line not in line_set:
                issues.append(f"Main line '{line}' has no connections in the network data")
        for line, station in REPRESENTATIVE_STATIONS.items():
            if station not in self._stations:
                issues.append(f"Representative station '{station}' of {line} is missing")
            elif line not in self._stations[station]:
                issues.append(f"Representative station '{station}' does not list {line}")

        # Connection integrity.
        seen_pairs = set()
        for conn in self._connections:
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            label = f"'{src}'-'{dst}' ({line})"
            if src not in self._stations:
                issues.append(f"Connection {label} references unknown station '{src}'")
            if dst not in self._stations:
                issues.append(f"Connection {label} references unknown station '{dst}'")
            if src == dst:
                issues.append(f"Connection {label} links a station to itself")
            for endpoint in (src, dst):
                if endpoint in self._stations and line not in self._stations[endpoint]:
                    issues.append(f"Station '{endpoint}' does not list line '{line}' used by {label}")
            key = (min(src, dst), max(src, dst), line)
            if key in seen_pairs:
                issues.append(f"Duplicate connection {label}")
            seen_pairs.add(key)

            # Distance accuracy.
            distance = conn["distance"]
            if not isinstance(distance, (int, float)) or distance < MIN_DISTANCE_M or distance > MAX_DISTANCE_M:
                issues.append(f"Distance {distance!r} of connection {label} is outside "
                              f"{MIN_DISTANCE_M}-{MAX_DISTANCE_M} meters")

        # Stations without any connection.
        connected = set()
        for conn in self._connections:
            connected.add(conn["source"])
            connected.add(conn["dest"])
        for name in self._stations:
            if name not in connected:
                issues.append(f"Station '{name}' has no connections")

        # Connectivity of the network.
        parent = {}

        def find(node):
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        for name in self._ordered_station_names():
            find(name)
        for conn in self._connections:
            root_a, root_b = find(conn["source"]), find(conn["dest"])
            if root_a != root_b:
                parent[root_a] = root_b
        components = {find(node) for node in parent}
        if len(components) > 1:
            issues.append(f"Network is split into {len(components)} disconnected components")

        return DataIntegrityReport(passed=not issues, issues=issues)
