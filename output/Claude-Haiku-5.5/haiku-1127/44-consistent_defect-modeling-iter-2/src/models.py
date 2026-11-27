"""Core data models: graph primitives and query/route/summary records."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class Edge:
    """A directed, weighted edge between two station numbers.

    Attributes:
        source: Station number of the origin.
        dest: Station number of the destination.
        distance: Physical distance in meters (also used as the weight).
        line: Name of the subway line the edge belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest-path algorithms (equals distance)."""
        return self.distance

    def __repr__(self) -> str:
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller; the graph only stores them.
    Station names and their line affiliations are kept in ``station_lines``.
    """

    def __init__(self) -> None:
        # station name -> list of line names serving that station
        self.station_lines: Dict[str, List[str]] = {}
        # station number -> list of outgoing edges
        self._adjacency: Dict[int, List[Edge]] = {}

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Record the lines serving a station (replaces any previous value)."""
        self.station_lines[station_name] = list(lines)

    def add_vertex(self, number: int) -> None:
        """Ensure a vertex exists in the graph even without edges."""
        self._adjacency.setdefault(number, [])

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge; both endpoints become vertices.

        Raises:
            TypeError: If ``edge`` is not an Edge.
            ValueError: If the distance is negative.
        """
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        if edge.distance < 0:
            raise ValueError("edge distance must be non-negative")
        self._adjacency.setdefault(edge.source, []).append(edge)
        self._adjacency.setdefault(edge.dest, [])

    def adjacent(self, number: int) -> List[Edge]:
        """Return the outgoing edges of a vertex (empty list if unknown)."""
        return self._adjacency.get(number, [])

    def has_vertex(self, number: int) -> bool:
        """Return True if the vertex exists in the graph."""
        return number in self._adjacency

    def vertices(self) -> List[int]:
        """Return all vertex numbers."""
        return list(self._adjacency.keys())

    def edge_count(self) -> int:
        """Return the number of directed edges."""
        return sum(len(edges) for edges in self._adjacency.values())


@dataclass
class Query:
    """A passenger's path query."""

    start_station: str
    end_station: str
    mode: str = "comprehensive"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class Route:
    """A computed route through the network.

    Attributes:
        station_sequence: Station names from start to end.
        total_distance_meters: Sum of edge distances in meters.
        transfer_count: Number of line changes along the route.
        involved_lines: Unique line names in order of appearance.
        segments: List of (line name, station names travelled on that line).
        transfers: List of (transfer station, line before, line after).
    """

    station_sequence: List[str]
    total_distance_meters: float
    transfer_count: int
    involved_lines: List[str]
    segments: List[Tuple[str, List[str]]] = field(default_factory=list)
    transfers: List[Tuple[str, str, str]] = field(default_factory=list)


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_meters: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float
