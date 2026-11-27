"""Core domain data structures: edges, graph, paths, queries and summaries."""

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters (also used as the edge weight).
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (see ``subway_network``).
    The graph keeps:
        adjacency: dict[station number, list[Edge]]
        station_to_number: dict[station name, station number]
        number_to_station: dict[station number, station name]
        station_lines: dict[station name, list[line name]]
    """

    def __init__(self):
        self.adjacency: Dict[int, List[Edge]] = {}
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self._edge_count = 0

    @property
    def vertex_count(self):
        """Number of stations (vertices) in the graph."""
        return len(self.adjacency)

    @property
    def edge_count(self):
        """Number of undirected connections (edges) added to the graph."""
        return self._edge_count

    def add_vertex(self, vertex):
        """Ensure a station number exists as a vertex."""
        self.adjacency.setdefault(vertex, [])

    def register_station(self, name, number):
        """Associate a station name with a station number.

        Raises:
            ValueError: If the name or number is already bound to a different
                counterpart.
        """
        existing = self.station_to_number.get(name)
        if existing is not None and existing != number:
            raise ValueError(f"Station '{name}' already registered with number {existing}")
        bound = self.number_to_station.get(number)
        if bound is not None and bound != name:
            raise ValueError(f"Number {number} already used by station '{bound}'")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.station_lines.setdefault(name, [])
        self.add_vertex(number)

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) lines serving a station."""
        self.station_lines[station_name] = list(dict.fromkeys(str(line) for line in lines))

    def add_edge(self, edge):
        """Add an undirected edge; it is stored in both endpoints' adjacency lists."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adjacency[edge.dest].append(edge)
        self._edge_count += 1

    def neighbors(self, vertex):
        """Return the edges incident to ``vertex`` (empty list if unknown)."""
        return self.adjacency.get(vertex, [])

    def number_of(self, name):
        """Return the station number for a name, or None if unknown."""
        return self.station_to_number.get(name)

    def name_of(self, number):
        """Return the station name for a number (falls back to the number as text)."""
        return self.number_to_station.get(number, str(number))

    def lines_of(self, name):
        """Return a copy of the list of lines serving a station."""
        return list(self.station_lines.get(name, []))

    def iter_edges(self) -> Iterator[Edge]:
        """Yield every undirected edge exactly once."""
        for vertex, edges in self.adjacency.items():
            for edge in edges:
                if edge.source == vertex:
                    yield edge


@dataclass
class Transfer:
    """A station where the passenger changes from one line to another."""

    station_name: str
    lines: List[str]


@dataclass
class Path:
    """A complete route between two stations.

    Attributes:
        station_sequence: Ordered station names from start to end.
        edges: Ordered edges travelled (one fewer than stations).
        total_distance: Total distance in meters.
        transfer_count: Number of line changes.
        involved_lines: Unique line names in order of first use.
        transfers: Transfer details.
    """

    station_sequence: List[str]
    edges: list
    total_distance: float
    transfer_count: int
    involved_lines: List[str]
    transfers: List[Transfer] = field(default_factory=list)


@dataclass
class Query:
    """A user query and the options it was run with."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class PathSummary:
    """Key figures extracted from a path."""

    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float
