"""Subway network management: station registry, connections and data maintenance.

``SubwayNetwork`` owns the weighted graph and the station name <-> station
number mappings. It supports building from the JSON dataset, name
standardisation, data updates (new lines, station modifications, distance
updates) and data integrity checks.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Optional, Set

from models import Edge, Graph

# Lines the dataset is expected to cover.
REQUIRED_LINES: List[str] = [
    "Line 1",
    "Line 2",
    "Line 4",
    "Line 5",
    "Line 6",
    "Line 8",
    "Line 10",
    "Line 13",
    "Line 14",
    "Line 15",
    "Changping Line",
    "Yizhuang Line",
    "Fangshan Line",
    "Airport Line",
]

# Plausible range for a single inter-station distance in meters.
MIN_PLAUSIBLE_DISTANCE_M: float = 100
MAX_PLAUSIBLE_DISTANCE_M: float = 10000


class SubwayNetwork:
    """Subway network model combining the graph with station name mappings.

    Attributes:
        graph: Weighted undirected graph of stations.
        station_to_number: Mapping from station name to station number.
        number_to_station: Mapping from station number to station name.
    """

    def __init__(self) -> None:
        self.graph: Graph = Graph()
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self._next_number: int = 0

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "SubwayNetwork":
        """Build a network from the parsed JSON dataset."""
        network = cls()
        for station in data.get("stations", []):
            network.add_station(station["name"], station.get("lines", []))
        for conn in data.get("connections", []):
            network.add_connection(
                conn["source"], conn["dest"], conn["distance"], conn["line"]
            )
        return network

    @property
    def station_lines(self) -> Dict[str, List[str]]:
        """Mapping from station name to its line names."""
        return self.graph.station_lines

    # ------------------------------------------------------------------
    # Station management
    # ------------------------------------------------------------------
    def add_station(self, name: str, lines: Optional[Iterable[str]] = None) -> int:
        """Register a station (or extend an existing one) and return its number."""
        name = name.strip()
        if not name:
            raise ValueError("Station name cannot be empty")
        if name in self.station_to_number:
            number = self.station_to_number[name]
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
        existing = self.graph.station_lines.get(name, [])
        merged = list(existing) + list(lines or [])
        self.graph.set_station_lines(name, merged)
        return number

    def _ensure_station(self, name: str) -> int:
        """Return the number of a station, registering it if necessary."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        return self.add_station(name)

    def has_station(self, name: str) -> bool:
        """Return True if a station with exactly this name exists."""
        return name in self.station_to_number

    def get_station_number(self, name: str) -> int:
        """Return the station number for a canonical station name.

        Raises:
            KeyError: If the station does not exist.
        """
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station: {name}")
        return self.station_to_number[name]

    def station_name(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_count(self) -> int:
        """Return the number of registered stations."""
        return len(self.station_to_number)

    def resolve_station_name(self, query: str) -> Optional[str]:
        """Standardise a user-supplied station name to its official form.

        Accepts exact names, names with or without the trailing "站", and
        case/space-insensitive matches.

        Returns:
            The official station name, or None if no unique match exists.
        """
        q = query.strip()
        if not q:
            return None
        if q in self.station_to_number:
            return q
        if q.endswith("站") and q[:-1] in self.station_to_number:
            return q[:-1]
        if q + "站" in self.station_to_number:
            return q + "站"

        normalized = q.replace(" ", "").lower()
        matches = [
            name
            for name in self.station_to_number
            if name.replace(" ", "").lower() == normalized
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def modify_station(self, name: str, lines: Iterable[str]) -> None:
        """Replace the line affiliations of an existing station.

        Raises:
            KeyError: If the station does not exist.
        """
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station: {name}")
        self.graph.set_station_lines(name, lines)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def add_connection(self, source_name: str, dest_name: str, distance: float, line: str) -> None:
        """Add or update a connection between two stations.

        Raises:
            ValueError: If the distance is not positive or the stations are identical.
        """
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError(f"Invalid distance for {source_name}-{dest_name}: {distance}")
        if source_name == dest_name:
            raise ValueError("A station cannot be connected to itself")
        a = self._ensure_station(source_name)
        b = self._ensure_station(dest_name)
        self.graph.add_edge(Edge(a, b, distance, line))

    def update_distance(self, name_a: str, name_b: str, distance: float) -> None:
        """Update the distance of an existing connection.

        Raises:
            KeyError: If a station or the connection does not exist.
            ValueError: If the distance is not positive.
        """
        if distance <= 0:
            raise ValueError("Distance must be positive")
        a = self.get_station_number(name_a)
        b = self.get_station_number(name_b)
        if not self.graph.set_edge_distance(a, b, distance):
            raise KeyError(f"No connection between '{name_a}' and '{name_b}'")

    # ------------------------------------------------------------------
    # Line management
    # ------------------------------------------------------------------
    def line_names(self) -> Set[str]:
        """Return all line names known to the network."""
        names: Set[str] = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        for edge in self.graph.edges():
            names.add(edge.line)
        return names

    def line_stations(self, line: str) -> List[str]:
        """Return the station names of a line in travel order."""
        adj: Dict[int, List[int]] = defaultdict(list)
        for edge in self.graph.edges():
            if edge.line == line:
                adj[edge.source].append(edge.dest)
                adj[edge.dest].append(edge.source)
        if not adj:
            return []

        endpoints = [v for v in sorted(adj) if len(adj[v]) == 1]
        start = endpoints[0] if endpoints else min(adj)
        ordered = [start]
        visited = {start}
        current = start
        while True:
            nxt = [w for w in adj[current] if w not in visited]
            if not nxt:
                break
            current = nxt[0]
            visited.add(current)
            ordered.append(current)
        return [self.number_to_station[v] for v in ordered]

    def add_line(self, line_name: str, station_names: List[str], distances: List[float]) -> None:
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: Name of the new line.
            station_names: Stations in travel order (at least two).
            distances: Distance in meters between consecutive stations.

        Raises:
            ValueError: If the line already exists or the input is inconsistent.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")
        for d in distances:
            if not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"Invalid distance: {d}")

        for name in station_names:
            self.add_station(name, [line_name])
        for i, d in enumerate(distances):
            self.add_connection(station_names[i], station_names[i + 1], d, line_name)

    # ------------------------------------------------------------------
    # Data integrity
    # ------------------------------------------------------------------
    def check_data_integrity(self) -> List[str]:
        """Run all integrity checks and return a list of issue descriptions.

        An empty list means the data passed every check.
        """
        issues: List[str] = []
        issues.extend(self._check_coverage())
        issues.extend(self._check_connections())
        issues.extend(self._check_distances())
        return issues

    def _check_coverage(self) -> List[str]:
        """Verify that the main lines are represented in the dataset."""
        issues: List[str] = []
        if not self.station_to_number:
            issues.append("Coverage: no stations are loaded")
            return issues
        present = self.line_names()
        for line in REQUIRED_LINES:
            if line not in present:
                issues.append(f"Coverage: required line '{line}' has no stations or connections")
        return issues

    def _check_connections(self) -> List[str]:
        """Verify adjacency relationships between stations."""
        issues: List[str] = []
        edge_lines: Dict[int, Set[str]] = {v: set() for v in self.graph.vertices()}
        for v in self.graph.vertices():
            for edge in self.graph.adj(v):
                edge_lines[v].add(edge.line)

        for name, number in self.station_to_number.items():
            lines = self.graph.station_lines.get(name, [])
            if not lines:
                issues.append(f"Connection: station '{name}' has no line affiliation")
            if not self.graph.adj(number):
                issues.append(f"Connection: station '{name}' has no adjacent stations")
                continue
            for line in lines:
                if line not in edge_lines[number]:
                    issues.append(
                        f"Connection: station '{name}' is on line '{line}' but has no connection on that line"
                    )

        connected = [v for v in self.graph.vertices() if self.graph.adj(v)]
        if connected:
            seen = self._reachable_from(connected[0])
            unreachable = [self.number_to_station[v] for v in connected if v not in seen]
            if unreachable:
                start_name = self.number_to_station[connected[0]]
                issues.append(
                    f"Connection: {len(unreachable)} station(s) unreachable from '{start_name}': "
                    + ", ".join(unreachable[:10])
                )
        return issues

    def _check_distances(self) -> List[str]:
        """Verify the plausibility of stored distances."""
        issues: List[str] = []
        for edge in self.graph.edges():
            a = self.number_to_station[edge.source]
            b = self.number_to_station[edge.dest]
            if not isinstance(edge.distance, (int, float)) or edge.distance <= 0:
                issues.append(f"Distance: connection {a}-{b} has invalid distance {edge.distance}")
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= edge.distance <= MAX_PLAUSIBLE_DISTANCE_M):
                issues.append(
                    f"Distance: connection {a}-{b} has distance {edge.distance} m outside "
                    f"the plausible range [{MIN_PLAUSIBLE_DISTANCE_M}, {MAX_PLAUSIBLE_DISTANCE_M}]"
                )
        return issues

    def _reachable_from(self, start: int) -> Set[int]:
        """Return the set of vertices reachable from ``start`` (BFS)."""
        seen = {start}
        queue = deque([start])
        while queue:
            v = queue.popleft()
            for edge in self.graph.adj(v):
                if edge.dest not in seen:
                    seen.add(edge.dest)
                    queue.append(edge.dest)
        return seen
