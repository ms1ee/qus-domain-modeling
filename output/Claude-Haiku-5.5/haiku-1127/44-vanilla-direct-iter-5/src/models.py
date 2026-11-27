"""Core data models: exceptions, weighted undirected graph and edges.

Station numbers (integers) are assigned by the caller (see
``subway_network.SubwayNetwork``); the ``Graph`` class only stores adjacency
lists keyed by those numbers.
"""
from __future__ import annotations


class SubwayError(Exception):
    """Base class for all subway-system errors."""


class UnknownStationError(SubwayError):
    """Raised when a station name or number is not part of the network."""


class NoPathError(SubwayError):
    """Raised when no route satisfies the query constraints."""


class DataError(SubwayError):
    """Raised when subway data is malformed or inconsistent."""


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        weight: edge weight, equal to the inter-station distance in meters.
        line: name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "weight", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str) -> None:
        if distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.weight = distance
        self.line = line

    @property
    def distance(self) -> float:
        """Alias of ``weight`` (distance in meters)."""
        return self.weight

    def other(self, vertex: int) -> int:
        """Return the endpoint of this edge that is not ``vertex``.

        Raises:
            ValueError: if ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.weight}, {self.line!r})"


class Graph:
    """Weighted undirected graph implemented with adjacency lists.

    Vertices are station numbers (ints). Each edge object is stored in the
    adjacency list of both of its endpoints, so updating an edge's weight is
    visible from both directions.

    Attributes:
        station_lines: mapping from station name to the list of line names
            that serve the station (transfer stations have several lines).
    """

    def __init__(self) -> None:
        self._adj: dict[int, list[Edge]] = {}
        self.station_lines: dict[str, list[str]] = {}

    # ----- vertices -------------------------------------------------------
    def add_vertex(self, vertex: int) -> None:
        """Add a vertex if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex: int) -> bool:
        return vertex in self._adj

    def vertices(self) -> list[int]:
        return list(self._adj.keys())

    def vertex_count(self) -> int:
        return len(self._adj)

    # ----- edges ----------------------------------------------------------
    def add_edge(self, edge: Edge) -> None:
        """Insert an undirected edge, creating missing endpoints."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)

    def adjacent(self, vertex: int) -> list[Edge]:
        """Return the edges incident to ``vertex`` (empty list if unknown)."""
        return self._adj.get(vertex, [])

    def edges(self) -> list[Edge]:
        """Return every distinct edge exactly once."""
        seen: set[int] = set()
        result: list[Edge] = []
        for edge_list in self._adj.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def edge_count(self) -> int:
        return len(self.edges())

    def edges_between(self, a: int, b: int) -> list[Edge]:
        """Return all edges joining vertices ``a`` and ``b``."""
        return [e for e in self.adjacent(a) if e.other(a) == b]

    # ----- station metadata -----------------------------------------------
    def set_station_lines(self, station_name: str, lines: list[str]) -> None:
        """Set the (de-duplicated, order-preserving) lines of a station."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def lines_of(self, station_name: str) -> list[str]:
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
