"""Core domain models: stations, lines, weighted directed graph, routes and reports."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Station:
    """A subway station with its official name, numeric identifier and lines."""

    name: str
    number: int
    lines: list = field(default_factory=list)


@dataclass
class Line:
    """A subway line with its ordered list of station names."""

    name: str
    station_sequence: list = field(default_factory=list)


class Edge:
    """A directed, weighted connection between two station numbers.

    Attributes:
        source: station number where the connection starts.
        dest: station number where the connection ends.
        distance: physical distance in meters (also used as weight).
        line: name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = int(source)
        self.dest = int(dest)
        self.distance = float(distance)
        self.line = str(line)

    @property
    def weight(self):
        """Edge weight used by shortest-path computations (meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph of subway stations.

    Station numbers are assigned by the caller (see network.SubwayNetwork).
    Each connection is usable only in the direction it was added.
    """

    def __init__(self):
        # station number -> list of outgoing edges
        self.adj = {}
        # station name -> list of line names serving the station
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add a directed edge, registering both endpoints as vertices."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])

    def adjacent(self, vertex):
        """Return outgoing edges of a vertex (empty list if unknown)."""
        return self.adj.get(vertex, [])

    def vertices(self):
        """Return all station numbers in the graph."""
        return list(self.adj.keys())

    def num_vertices(self):
        return len(self.adj)

    def num_edges(self):
        return sum(len(edges) for edges in self.adj.values())


@dataclass
class Transfer:
    """A transfer point where passengers change from one line to another."""

    station_name: str
    involved_lines: list = field(default_factory=list)


@dataclass
class Route:
    """Result of a path query, including fare and transfer information."""

    start_station: str
    end_station: str
    mode: str
    station_sequence: list
    edges: list
    total_distance_meters: float
    transfer_count: int
    transfers: list
    lines: list
    fare_yuan: int
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_meters: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A rendered report of one or more routes."""

    format: str
    content: str
    output_file_path: Optional[str] = None
