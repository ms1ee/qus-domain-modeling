"""
Subway network management.

Builds the weighted directed graph from the dataset, maintains the
station-name <-> station-number mapping, provides station name resolution,
data update operations (adding lines, modifying stations and distances) and
the data integrity checks used by ``--check_data``.
"""

import difflib

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Main lines that must be represented in the dataset.
REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range of distances between adjacent stations (meters).
MIN_REASONABLE_DISTANCE = 100
MAX_REASONABLE_DISTANCE = 10000

# Minimum similarity ratio for fuzzy station name matching.
FUZZY_MATCH_CUTOFF = 0.3


class StationNotFoundError(ValueError):
    """Raised when a station name cannot be resolved."""


def normalize_name(name):
    """Normalize a station name for comparison (ignore case, spaces and the suffix '站')."""
    text = "".join(str(name).split()).lower()
    if text.endswith("站"):
        text = text[:-1]
    return text


class SubwayNetwork:
    """
    In-memory model of the Beijing Subway network.

    Attributes:
        graph: The Graph instance holding edges and station lines.
        station_to_number: dict mapping station name -> station number.
        number_to_station: list mapping station number -> station name.
    """

    def __init__(self, data=None, data_path=DATA_FILE_PATH):
        if data is None:
            data = load_subway_data(data_path)
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = []
        self._undeclared = set()  # stations referenced only by connections
        self._build(data)

    # ----- construction ------------------------------------------------------
    def _build(self, data):
        """Populate the graph from the dataset dictionary."""
        stations = data.get("stations")
        connections = data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise ValueError("Invalid dataset: 'stations' and 'connections' must be lists")

        for record in stations:
            name = str(record["name"]).strip()
            self._declare(name, record.get("lines", []))

        for record in connections:
            source_name = str(record["source"]).strip()
            dest_name = str(record["dest"]).strip()
            line = str(record["line"]).strip()
            distance = int(record["distance"])
            source = self._ensure(source_name)
            dest = self._ensure(dest_name)
            self.graph.add_edge(Edge(source, dest, distance, line))

    def _declare(self, name, lines=()):
        """Register a station (creating it if needed) and merge its lines."""
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station.append(name)
            self.graph.add_vertex(number)
        existing = self.graph.get_station_lines(name)
        for line in lines:
            line = str(line).strip()
            if line and line not in existing:
                existing.append(line)
        self.graph.set_station_lines(name, existing)
        return self.station_to_number[name]

    def _ensure(self, name):
        """Return the number of a station, registering it as undeclared if unknown."""
        if name not in self.station_to_number:
            self._declare(name)
            self._undeclared.add(name)
        return self.station_to_number[name]

    # ----- lookups -----------------------------------------------------------
    def has_station(self, name):
        """Return True if the exact station name exists."""
        return name in self.station_to_number

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def number_of(self, name):
        """Return the station number for an exact station name."""
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(name)

    def all_lines(self):
        """Return a sorted list of all line names appearing in the network."""
        return sorted({edge.line for edge in self.graph.edges()})

    def resolve_station(self, query):
        """
        Resolve a user-supplied station name to an official station name.

        Returns:
            (official_name, exact_match) where exact_match is False when the
            name was matched to the nearest official station by similarity.

        Raises:
            StationNotFoundError: If no station is similar enough.
        """
        normalized = normalize_name(query)
        if not normalized:
            raise StationNotFoundError("Station name is empty")

        norm_map = {}
        for official in self.station_to_number:
            norm_map.setdefault(normalize_name(official), official)

        if normalized in norm_map:
            return norm_map[normalized], True

        matches = difflib.get_close_matches(normalized, list(norm_map), n=1, cutoff=FUZZY_MATCH_CUTOFF)
        if matches:
            return norm_map[matches[0]], False
        raise StationNotFoundError(f"Station '{query}' does not exist")

    # ----- data updates ------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """
        Add a new line through an ordered list of existing stations.

        Consecutive stations are connected in both directions, because a
        physical subway line can be travelled either way.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of existing station names.
            distances: List of distances (meters) between consecutive stations.

        Returns:
            int: Number of directed edges added.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")

        numbers = [self.number_of(name) for name in station_names]
        values = []
        for d in distances:
            d = int(d)
            if d <= 0:
                raise ValueError("Distances must be positive")
            values.append(d)

        added = 0
        for i, distance in enumerate(values):
            a, b = numbers[i], numbers[i + 1]
            self.graph.add_edge(Edge(a, b, distance, line_name))
            self.graph.add_edge(Edge(b, a, distance, line_name))
            added += 2
        for name in station_names:
            self._declare(name, [line_name])
        return added

    def update_station(self, name, new_name=None, lines=None):
        """
        Modify a station's name and/or line list.

        Args:
            name: Current official station name.
            new_name: Optional new station name.
            lines: Optional new list of lines serving the station.
        """
        number = self.number_of(name)
        if lines is not None:
            self.graph.set_station_lines(name, [str(l).strip() for l in lines])
        if new_name and new_name != name:
            new_name = str(new_name).strip()
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            self.graph.station_lines[new_name] = self.graph.station_lines.pop(name, [])
            del self.station_to_number[name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            if name in self._undeclared:
                self._undeclared.discard(name)
                self._undeclared.add(new_name)

    def update_distance(self, source, dest, distance, both_directions=True):
        """
        Update the distance of the connection between two adjacent stations.

        Returns:
            int: Number of edges updated.

        Raises:
            ValueError: If the distance is not positive or no connection exists.
        """
        distance = int(distance)
        if distance <= 0:
            raise ValueError("Distance must be positive")
        s = self.number_of(source)
        d = self.number_of(dest)
        updated = 0
        for edge in self.graph.adj(s):
            if edge.dest == d:
                edge.distance = distance
                updated += 1
        if both_directions:
            for edge in self.graph.adj(d):
                if edge.dest == s:
                    edge.distance = distance
                    updated += 1
        if updated == 0:
            raise ValueError(f"No connection exists between '{source}' and '{dest}'")
        return updated

    # ----- integrity checks --------------------------------------------------
    def check_integrity(self):
        """
        Run data integrity checks.

        Returns:
            list[tuple[str, str]]: (level, message) pairs where level is
            "ERROR" or "WARNING". An empty list means no problems were found.
        """
        issues = []

        def add(level, message):
            issues.append((level, message))

        if not self.station_to_number:
            add("ERROR", "No stations are loaded")

        # Coverage of main lines.
        declared_lines = set()
        for name in self.station_to_number:
            declared_lines.update(self.lines_of(name))
        edge_lines = set(self.all_lines())
        for line in REQUIRED_LINES:
            if line not in declared_lines and line not in edge_lines:
                add("WARNING", f"Representative line '{line}' has no stations in the dataset")

        for name in sorted(self._undeclared):
            add("WARNING", f"Station '{name}' appears in connections but not in the station list")
        for name in self.station_names():
            if not self.lines_of(name):
                add("WARNING", f"Station '{name}' has no line information")

        # Accuracy and consistency of connections.
        seen = set()
        directed = set()
        for edge in self.graph.edges():
            src_name = self.name_of(edge.source)
            dst_name = self.name_of(edge.dest)
            label = f"{src_name} -> {dst_name} ({edge.line})"
            if isinstance(edge.distance, bool) or not isinstance(edge.distance, int) or edge.distance <= 0:
                add("ERROR", f"Connection {label} has invalid distance {edge.distance!r}")
            elif not (MIN_REASONABLE_DISTANCE <= edge.distance <= MAX_REASONABLE_DISTANCE):
                add("WARNING", f"Connection {label} has suspicious distance {edge.distance} m")
            key = (edge.source, edge.dest, edge.line)
            if key in seen:
                add("WARNING", f"Duplicate connection {label}")
            seen.add(key)
            directed.add((edge.source, edge.dest))
            if edge.line not in self.lines_of(src_name) and edge.line not in self.lines_of(dst_name):
                add("WARNING", f"Connection {label} uses a line not serving either station")

        for s, d in sorted(directed):
            if (d, s) not in directed:
                add("WARNING", f"One-directional connection {self.name_of(s)} -> {self.name_of(d)}")

        # Isolated stations.
        incoming = {d for _, d in directed}
        outgoing = {s for s, _ in directed}
        for number, name in enumerate(self.number_to_station):
            if number not in incoming and number not in outgoing:
                add("WARNING", f"Station '{name}' has no connections")

        # Connectivity (weakly connected components).
        undirected = {}
        for s, d in directed:
            undirected.setdefault(s, set()).add(d)
            undirected.setdefault(d, set()).add(s)
        if undirected:
            remaining = set(undirected)
            components = 0
            while remaining:
                components += 1
                start = remaining.pop()
                stack = [start]
                while stack:
                    node = stack.pop()
                    for nxt in undirected.get(node, ()):
                        if nxt in remaining:
                            remaining.discard(nxt)
                            stack.append(nxt)
            if components > 1:
                add("WARNING", f"Network is split into {components} disconnected parts")

        return issues
