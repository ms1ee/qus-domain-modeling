"""Core data models for the subway system.

Contains the graph primitives (Edge, Graph), query/route data classes used by
the service and reporting layers, and the package exception hierarchy.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubwayError(Exception):
    """Base class for all user-facing subway system errors."""


class StationNotFoundError(SubwayError):
    """A station name does not exist in the network."""


class NoRouteError(SubwayError):
    """No path exists between the requested stations under the given constraints."""


class PathCalculationError(SubwayError):
    """An unexpected failure occurred during path calculation."""


class FareCalculationError(SubwayError):
    """An unexpected failure occurred during fare calculation."""


class DataUpdateError(SubwayError):
    """A data maintenance operation (add line, modify station, update distance) failed."""


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------

class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: Station number of the origin.
        dest: Station number of the destination.
        distance: Distance in meters (also used as the edge weight).
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source!r}->{self.dest!r}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller; the graph only stores them.
    ``station_lines`` maps station names to the lines serving them.
    """

    def __init__(self):
        self._adj = {}
        self._edge_count = 0
        self.station_lines = {}

    # -- node management ----------------------------------------------------

    def add_node(self, number):
        """Ensure a station number exists as a node in the graph."""
        self._adj.setdefault(number, [])

    def has_node(self, number):
        """Return True if the station number is a node of the graph."""
        return number in self._adj

    def nodes(self):
        """Return the list of all station numbers in the graph."""
        return list(self._adj.keys())

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    # -- edge management ----------------------------------------------------

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes if needed."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adj[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, node):
        """Return the outgoing edges of a node (empty list if unknown)."""
        return self._adj.get(node, [])

    def edges(self):
        """Iterate over all edges in the graph."""
        for edge_list in self._adj.values():
            for edge in edge_list:
                yield edge

    def find_edges(self, source, dest):
        """Return all edges from ``source`` to ``dest``."""
        return [edge for edge in self.adj(source) if edge.dest == dest]

    @property
    def station_count(self):
        """Number of station nodes."""
        return len(self._adj)

    @property
    def connection_count(self):
        """Number of directed connections (edges)."""
        return self._edge_count


# ---------------------------------------------------------------------------
# Query / route data classes
# ---------------------------------------------------------------------------

@dataclass
class Query:
    """A passenger query as submitted through the CLI."""

    origin_station: str
    destination_station: str
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class RouteSegment:
    """A contiguous stretch of a route travelled on a single line."""

    line_name: str
    distance_meters: float
    station_count: int


@dataclass
class Transfer:
    """A line change at a station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass
class Route:
    """A computed route.

    ``stations`` is stored in travel order (origin first). The
    ``station_sequence`` property gives the end-to-start ordering produced by
    path backtracking.
    """

    stations: List[str] = field(default_factory=list)
    segments: List[RouteSegment] = field(default_factory=list)
    transfers: List[Transfer] = field(default_factory=list)
    total_distance_meters: float = 0.0

    @property
    def transfer_count(self):
        """Number of line transfers along the route."""
        return len(self.transfers)

    @property
    def lines_involved(self):
        """Unique line names in order of first appearance."""
        seen = []
        for segment in self.segments:
            if segment.line_name not in seen:
                seen.append(segment.line_name)
        return seen

    @property
    def station_sequence(self):
        """Station names ordered from the end station back to the start station."""
        return list(reversed(self.stations))


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_meters: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class QueryResult:
    """Complete result of one query: query, route, and summary."""

    query: Query
    route: Route
    summary: PathSummary
