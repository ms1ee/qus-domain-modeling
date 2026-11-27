"""Subway network management.

Responsibilities:
    * station registry (station names <-> station numbers)
    * construction of the weighted directed graph from the dataset
    * station name standardisation (nearest-match resolution)
    * data update mechanisms (add lines, modify stations, update distances)
    * data integrity checks
"""

import difflib
import re
from collections import deque

from models import Edge, Graph

# Main lines that must be present in the network for coverage checks.
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

MIN_REASONABLE_DISTANCE_M = 100
MAX_REASONABLE_DISTANCE_M = 5000


def _normalize(name):
    """Normalise a station name for lenient comparison."""
    return re.sub(r"[\s\-_'\u2019]", "", name).lower()


class SubwayNetwork:
    """In-memory subway network built from the subway dataset.

    Attributes:
        station_to_number: dict station name -> station number.
        number_to_name: dict station number -> station name.
        graph: models.Graph holding the directed weighted edges and station lines.
    """

    def __init__(self, data):
        """Build the network from a dataset dict (see data_loader.load_subway_data).

        Raises:
            ValueError: if the data is not a dict or contains invalid entries.
        """
        if not isinstance(data, dict):
            raise ValueError("subway data must be a dict")
        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        self._build(data)

    # ----- construction -----
    def _build(self, data):
        """Populate stations, lines and edges from the dataset."""
        for station in data.get("stations", []):
            self._ensure_station(station["name"], station.get("lines", []))
        for conn in data.get("connections", []):
            line = str(conn["line"]).strip()
            src = self._ensure_station(conn["source"], [line])
            dst = self._ensure_station(conn["dest"], [line])
            self.graph.add_edge(Edge(src, dst, int(conn["distance"]), line))

    def _ensure_station(self, name, lines=()):
        """Return the number of a station, creating it if it does not exist."""
        name = str(name).strip()
        if not name:
            raise ValueError("station name cannot be empty")
        number = self.station_to_number.get(name)
        if number is None:
            number = len(self.number_to_name)
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.add_node(number)
            self.graph.set_station_lines(name, [])
        for line in lines:
            self._attach_line(name, str(line).strip())
        return number

    def _attach_line(self, name, line):
        """Add a line to a station's line list if it is not already present."""
        if not line:
            return
        current = self.graph.get_station_lines(name)
        if line not in current:
            current.append(line)
            self.graph.set_station_lines(name, current)

    # ----- queries -----
    def stations(self):
        """Return a sorted list of all official station names."""
        return sorted(self.station_to_number)

    @property
    def station_count(self):
        """Number of stations in the network."""
        return len(self.station_to_number)

    def station_lines(self, name):
        """Return the lines of a station by official name (empty if unknown)."""
        return self.graph.get_station_lines(name)

    def lines(self):
        """Return a sorted list of all line names known to the network."""
        result = set()
        for station_line_list in self.graph.station_lines.values():
            result.update(station_line_list)
        return sorted(result)

    def line_stations(self):
        """Return dict line name -> sorted list of station names served by that line."""
        index = {}
        for edge in self.graph.edges():
            bucket = index.setdefault(edge.line, set())
            bucket.add(self.number_to_name[edge.source])
            bucket.add(self.number_to_name[edge.dest])
        return {line: sorted(names) for line, names in index.items()}

    def transfer_stations(self):
        """Return sorted names of stations served by more than one line."""
        return [name for name in self.stations() if len(self.station_lines(name)) > 1]

    def resolve_station(self, query):
        """Standardise a user-supplied station name.

        Returns:
            (station number, official station name, exact_match flag).
            Unknown names are matched to the most similar official name.

        Raises:
            ValueError: if the query is empty or the network has no stations.
        """
        if query is None or not str(query).strip():
            raise ValueError("station name cannot be empty")
        text = str(query).strip()
        if text in self.station_to_number:
            return self.station_to_number[text], text, True

        index = {}
        for official in self.station_to_number:
            index.setdefault(_normalize(official), official)
        if not index:
            raise ValueError("the network contains no stations")

        normalized = _normalize(text)
        if normalized in index:
            official = index[normalized]
            return self.station_to_number[official], official, True

        best_key = max(
            index,
            key=lambda key: difflib.SequenceMatcher(None, normalized, key).ratio(),
        )
        official = index[best_key]
        return self.station_to_number[official], official, False

    # ----- data updates -----
    def _require_number(self, name):
        """Return the number of an official station name or raise ValueError."""
        if name not in self.station_to_number:
            raise ValueError(f"station '{name}' does not exist")
        return self.station_to_number[name]

    def add_line(self, line_name, stations, distances, bidirectional=True):
        """Add a new line described by an ordered list of stations.

        Args:
            line_name: name of the new line; must not already exist.
            stations: ordered station names along the line (at least two).
            distances: distances in meters between consecutive stations.
            bidirectional: if True, add the reverse direction as well.

        Returns:
            Number of directed edges added.

        Raises:
            ValueError: on invalid input.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("line name cannot be empty")
        if line_name in self.lines():
            raise ValueError(f"line '{line_name}' already exists")
        names = [str(s).strip() for s in stations]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("a line cannot contain duplicate stations")
        if len(distances) != len(names) - 1:
            raise ValueError("number of distances must equal stations minus one")
        for distance in distances:
            if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
                raise ValueError("distances must be positive integers (meters)")

        numbers = [self._ensure_station(name, [line_name]) for name in names]
        added = 0
        for src, dst, distance in zip(numbers, numbers[1:], distances):
            self.graph.add_edge(Edge(src, dst, distance, line_name))
            added += 1
            if bidirectional:
                self.graph.add_edge(Edge(dst, src, distance, line_name))
                added += 1
        return added

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's line list and/or rename it.

        Returns:
            The (possibly new) official name of the station.

        Raises:
            ValueError: if the station does not exist or the new name is taken.
        """
        number = self._require_number(name)
        official = name
        if lines is not None:
            cleaned = [str(line).strip() for line in lines if str(line).strip()]
            self.graph.set_station_lines(official, cleaned)
        if new_name is not None and str(new_name).strip() and new_name.strip() != official:
            target = new_name.strip()
            if target in self.station_to_number:
                raise ValueError(f"station '{target}' already exists")
            self.graph.station_lines[target] = self.graph.station_lines.pop(official)
            del self.station_to_number[official]
            self.station_to_number[target] = number
            self.number_to_name[number] = target
            official = target
        return official

    def update_distance(self, source_name, dest_name, distance, bidirectional=True):
        """Update the distance of the connection between two stations.

        Returns:
            Number of directed edges updated.

        Raises:
            ValueError: on invalid distance, unknown station or missing connection.
        """
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise ValueError("distance must be a positive integer (meters)")
        src = self._require_number(source_name)
        dst = self._require_number(dest_name)
        updated = 0
        for edge in self.graph.find_edges(src, dst):
            edge.distance = distance
            updated += 1
        if bidirectional:
            for edge in self.graph.find_edges(dst, src):
                edge.distance = distance
                updated += 1
        if updated == 0:
            raise ValueError(f"no connection between '{source_name}' and '{dest_name}'")
        return updated

    # ----- integrity checks -----
    def check_integrity(self):
        """Run data integrity checks.

        Returns:
            A list of human-readable issue strings prefixed with [ERROR] or [WARNING].
            An empty list means no issues were found.
        """
        issues = []
        index = self.line_stations()

        # Coverage of main lines.
        for line in REQUIRED_MAIN_LINES:
            count = len(index.get(line, []))
            if count == 0:
                issues.append(f"[ERROR] main line '{line}' is missing from the network")
            elif count < 2:
                issues.append(f"[WARNING] main line '{line}' has only {count} station")

        # Station data.
        connected = set()
        for edge in self.graph.edges():
            connected.add(edge.source)
            connected.add(edge.dest)
        for name in self.stations():
            if not self.station_lines(name):
                issues.append(f"[ERROR] station '{name}' has no line assignment")
            if self.station_to_number[name] not in connected:
                issues.append(f"[WARNING] station '{name}' has no connections")

        # Connection integrity and distance accuracy.
        seen = {}
        for edge in self.graph.edges():
            src = self.number_to_name[edge.source]
            dst = self.number_to_name[edge.dest]
            label = f"{src} -> {dst} ({edge.line})"
            if edge.line not in self.station_lines(src) or edge.line not in self.station_lines(dst):
                issues.append(f"[WARNING] {label}: line not listed for both endpoint stations")
            if edge.distance <= 0:
                issues.append(f"[ERROR] {label}: distance must be positive, got {edge.distance}")
            elif edge.distance < MIN_REASONABLE_DISTANCE_M:
                issues.append(f"[WARNING] {label}: suspiciously short distance {edge.distance} m")
            elif edge.distance > MAX_REASONABLE_DISTANCE_M:
                issues.append(f"[WARNING] {label}: suspiciously long distance {edge.distance} m")

            key = (edge.source, edge.dest, edge.line)
            if key in seen and seen[key] != edge.distance:
                issues.append(
                    f"[ERROR] {label}: conflicting duplicate distances "
                    f"{seen[key]} m and {edge.distance} m"
                )
            seen.setdefault(key, edge.distance)

            reverse = [e for e in self.graph.find_edges(edge.dest, edge.source) if e.line == edge.line]
            if not reverse:
                issues.append(f"[WARNING] {label}: reverse connection missing (one-way only)")

        # Connectivity of the network (ignoring direction).
        undirected = {node: set() for node in self.graph.nodes()}
        for edge in self.graph.edges():
            undirected[edge.source].add(edge.dest)
            undirected[edge.dest].add(edge.source)
        visited = set()
        components = 0
        for start in undirected:
            if start in visited:
                continue
            components += 1
            visited.add(start)
            queue = deque([start])
            while queue:
                node = queue.popleft()
                for neighbour in undirected[node]:
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)
        if components > 1:
            issues.append(f"[WARNING] network is split into {components} disconnected parts")

        return issues
