"""Core data models used throughout the Beijing Subway fare system.

Contains the weighted undirected graph (``Graph``), its edges (``Edge``),
and result containers for computed routes (``Route``, ``RouteSegment``).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("edge distance must be a number")
        if distance < 0:
            raise ValueError("edge distance must not be negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest-path search (equal to the distance in meters)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (for example, the network
    builder). The graph keeps the mapping between station names and numbers,
    the lines serving each station, and the adjacency lists.

    Attributes:
        station_to_number: Mapping from station name to station number.
        number_to_station: Mapping from station number to station name.
        station_lines: Mapping from station name to the list of line names.
        adjacency: Mapping from station number to the list of incident edges.
    """

    def __init__(self) -> None:
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.adjacency: Dict[int, List[Edge]] = {}

    def add_station(self, name: str, number: int, lines: Optional[List[str]] = None) -> None:
        """Register a station under a caller-assigned number.

        Raises:
            ValueError: If the name or number is already bound to a different station.
        """
        if not name:
            raise ValueError("station name must not be empty")
        existing_number = self.station_to_number.get(name)
        if existing_number is not None and existing_number != number:
            raise ValueError(f"station '{name}' is already registered with number {existing_number}")
        existing_name = self.number_to_station.get(number)
        if existing_name is not None and existing_name != name:
            raise ValueError(f"number {number} is already used by station '{existing_name}'")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])
        if lines is not None:
            self.set_station_lines(name, lines)

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the lines serving a station, removing duplicates while keeping order."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge to the adjacency lists of both endpoints.

        Raises:
            ValueError: If the edge is a self-loop.
            KeyError: If an endpoint is not a registered station number.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loop edges are not allowed")
        for vertex in (edge.source, edge.dest):
            if vertex not in self.number_to_station:
                raise KeyError(f"unknown station number {vertex}")
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge)

    def adj(self, vertex: int) -> List[Edge]:
        """Return the edges incident to ``vertex`` (empty list if unknown)."""
        return self.adjacency.get(vertex, [])

    def number_of(self, name: str) -> int:
        """Return the number of a station name.

        Raises:
            KeyError: If the station is unknown.
        """
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def has_station(self, name: str) -> bool:
        """Return True if the station name is registered."""
        return name in self.station_to_number

    def vertices(self) -> List[int]:
        """Return all registered station numbers."""
        return list(self.number_to_station.keys())

    def num_stations(self) -> int:
        """Return the number of registered stations."""
        return len(self.number_to_station)

    def num_edges(self) -> int:
        """Return the number of undirected edges."""
        return sum(len(edges) for edges in self.adjacency.values()) // 2


@dataclass
class Station:
    """Lightweight station descriptor."""

    name: str
    number: int
    is_transfer_station: bool = False


@dataclass
class RouteSegment:
    """A contiguous run of the route travelling on a single line."""

    line_name: str
    start_station: str
    end_station: str
    distance: float


@dataclass
class Route:
    """Result of a path query.

    Attributes:
        station_sequence: Station names in travel order, start to end.
        total_distance_m: Total travel distance in meters.
        transfer_count: Number of line changes along the route.
        segments: Per-line route segments.
        transfers: Tuples of (transfer station, from line, to line).
        lines: Distinct lines involved, in order of first use.
        mode: Query mode used to compute the route.
        estimated_time: Estimated travel time in minutes.
    """

    station_sequence: List[str]
    total_distance_m: float
    transfer_count: int
    segments: List[RouteSegment]
    transfers: List[Tuple[str, str, str]]
    lines: List[str]
    mode: str
    estimated_time: float

    @property
    def total_distance_km(self) -> float:
        """Total travel distance in kilometers."""
        return self.total_distance_m / 1000.0
