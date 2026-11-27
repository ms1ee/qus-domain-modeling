"""Subway network management: loading, lookup, updates and integrity checks.

Station numbers are assigned here (the Graph does not assign them).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from data_loader import load_subway_data
from models import Edge, Graph

# Main lines that the data set is expected to cover (PRD section 4.1).
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
# Sanity bound for a single inter-station distance in meters.
MAX_REASONABLE_DISTANCE_M = 15000


@dataclass
class DataIntegrityReport:
    """Result of a data integrity check.

    Attributes:
        passed: True when no issues were found.
        issues: human-readable descriptions of problems.
    """

    passed: bool
    issues: List[str] = field(default_factory=list)


def _normalize(name):
    """Normalize a station name for lenient matching (case and spaces ignored)."""
    return "".join(str(name).split()).casefold()


class SubwayNetwork:
    """Holds the station mapping, the graph and the line information."""

    def __init__(self, data=None):
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self.line_names = set()
        self._declared_stations = set()
        self._edges_by_key = {}
        self._normalized_index = {}
        self._build_issues = []
        self._next_id = 0
        if data is None:
            data = load_subway_data()
        self._build(data)

    # ----- construction -------------------------------------------------------
    def _build(self, data):
        for station in data.get("stations", []):
            name = station["name"]
            lines = list(station.get("lines", []))
            self._ensure_station(name)
            self._declared_stations.add(name)
            self.graph.set_station_lines(name, lines)
            self.line_names.update(lines)
        for conn in data.get("connections", []):
            issue = self._add_connection(conn["source"], conn["dest"],
                                         conn["distance"], conn["line"])
            if issue:
                self._build_issues.append(issue)

    def _ensure_station(self, name):
        """Return the number of a station, creating it if necessary."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = self._next_id
        self._next_id += 1
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self._normalized_index[_normalize(name)] = name
        return number

    @staticmethod
    def _edge_key(a, b, line):
        return (min(a, b), max(a, b), line)

    def _add_connection(self, source_name, dest_name, distance, line):
        """Add a connection. Returns an issue string on invalid input, else None."""
        if source_name == dest_name:
            return f"Connection on '{line}' links station '{source_name}' to itself"
        a = self._ensure_station(source_name)
        b = self._ensure_station(dest_name)
        key = self._edge_key(a, b, line)
        if key in self._edges_by_key:
            return f"Duplicate connection {source_name} - {dest_name} on '{line}'"
        edge = Edge(a, b, distance, line)
        self.graph.add_edge(edge)
        self._edges_by_key[key] = edge
        self.line_names.add(line)
        for name in (source_name, dest_name):
            lines = self.graph.get_station_lines(name)
            if line not in lines:
                self.graph.set_station_lines(name, lines + [line])
        return None

    # ----- lookups ------------------------------------------------------------
    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def standardize_name(self, text):
        """Map user input to an official station name, or None if unknown."""
        if text in self.station_to_number:
            return text
        return self._normalized_index.get(_normalize(text))

    def station_number(self, name):
        """Return the station number for an official name, or None."""
        return self.station_to_number.get(name)

    def name_of(self, number):
        """Return the official name for a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return the lines serving a station."""
        return self.graph.get_station_lines(name)

    def stations_on_line(self, line):
        """Return the station names of a line in travel order (best effort)."""
        edges = [e for e in self.graph.edges() if e.line == line]
        if not edges:
            return []
        adjacency = {}
        for e in edges:
            adjacency.setdefault(e.source, []).append(e.dest)
            adjacency.setdefault(e.dest, []).append(e.source)
        visited = set()
        ordered = []
        for start in sorted(adjacency, key=lambda n: (len(adjacency[n]), n)):
            if start in visited:
                continue
            current = start
            while current is not None and current not in visited:
                visited.add(current)
                ordered.append(self.number_to_station[current])
                current = next((nb for nb in adjacency[current] if nb not in visited), None)
        return ordered

    # ----- data updates -------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line.

        Args:
            line_name: new line name (must be unused).
            station_names: ordered station names of the line.
            distances: distances in meters between consecutive stations.

        Raises:
            ValueError: on invalid or conflicting input.
        """
        line_name = (line_name or "").strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names:
            raise ValueError(f"Line '{line_name}' already exists")
        stations = [s.strip() for s in station_names]
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(stations)) != len(stations):
            raise ValueError("Station list contains duplicates")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError("Distances must be positive numbers")
        for name in stations:
            self._ensure_station(name)
            self._declared_stations.add(name)
        for i, distance in enumerate(distances):
            issue = self._add_connection(stations[i], stations[i + 1], distance, line_name)
            if issue:
                raise ValueError(issue)
        self.line_names.add(line_name)

    def update_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list. Returns the final name."""
        number = self.station_to_number.get(name)
        if number is None:
            raise KeyError(f"Station '{name}' does not exist")
        current = name
        if new_name and new_name != name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            del self.station_to_number[name]
            self.station_to_number[new_name] = number
            self.number_to_station[number] = new_name
            if self._normalized_index.get(_normalize(name)) == name:
                del self._normalized_index[_normalize(name)]
            self._normalized_index[_normalize(new_name)] = new_name
            if name in self._declared_stations:
                self._declared_stations.discard(name)
                self._declared_stations.add(new_name)
            old_lines = self.graph.station_lines.pop(name, [])
            self.graph.set_station_lines(new_name, old_lines)
            current = new_name
        if lines is not None:
            self.graph.set_station_lines(current, lines)
            self.line_names.update(lines)
        return current

    def update_distance(self, source_name, dest_name, line, distance):
        """Update the distance of an existing connection in meters."""
        a = self.station_to_number.get(source_name)
        b = self.station_to_number.get(dest_name)
        if a is None or b is None:
            raise KeyError("Both stations must exist")
        edge = self._edges_by_key.get(self._edge_key(a, b, line))
        if edge is None:
            raise KeyError(f"No connection between '{source_name}' and '{dest_name}' on '{line}'")
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("Distance must be a positive number")
        edge.distance = distance

    # ----- integrity ----------------------------------------------------------
    def check_integrity(self):
        """Run coverage, connectivity and distance checks.

        Returns:
            DataIntegrityReport describing the findings.
        """
        issues = list(self._build_issues)

        # Coverage of main lines.
        for line in REQUIRED_MAIN_LINES:
            if line not in self.line_names:
                issues.append(f"Main line '{line}' is missing from the network data")
        for line in sorted(self.line_names):
            if len(self.stations_on_line(line)) < 2:
                issues.append(f"Line '{line}' has fewer than two stations")

        # Station data.
        for name in self.station_names():
            if name not in self._declared_stations:
                issues.append(f"Station '{name}' is used in connections but not listed in stations")
            number = self.station_to_number[name]
            station_lines = self.graph.get_station_lines(name)
            if not station_lines:
                issues.append(f"Station '{name}' has no line affiliation")
            for line in station_lines:
                if not any(e.line == line for e in self.graph.adj(number)):
                    issues.append(f"Station '{name}' lists line '{line}' but has no connection on it")

        # Connection and distance checks.
        for edge in self.graph.edges():
            a_name = self.name_of(edge.source)
            b_name = self.name_of(edge.dest)
            label = f"{a_name} - {b_name} ('{edge.line}')"
            if not any(e is edge for e in self.graph.adj(edge.source)) or \
                    not any(e is edge for e in self.graph.adj(edge.dest)):
                issues.append(f"Connection {label} is not bidirectional")
            if not isinstance(edge.distance, (int, float)) or edge.distance <= 0:
                issues.append(f"Connection {label} has an invalid distance {edge.distance!r}")
            elif edge.distance > MAX_REASONABLE_DISTANCE_M:
                issues.append(f"Connection {label} distance {edge.distance} m exceeds the plausible maximum")
            for name in (a_name, b_name):
                if edge.line not in self.graph.get_station_lines(name):
                    issues.append(f"Station '{name}' does not list line '{edge.line}' of connection {label}")

        return DataIntegrityReport(passed=not issues, issues=issues)
