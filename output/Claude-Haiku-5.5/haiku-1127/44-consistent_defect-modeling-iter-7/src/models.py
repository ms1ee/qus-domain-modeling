"""
Core data models for the Beijing Subway fare calculation system.

Contains the graph structures (Edge, Graph) and the domain records used by
the path, fare, reporting and CLI layers.
"""

from dataclasses import dataclass, field
from typing import Optional


class Edge:
    """A directed, weighted connection between two station numbers.

    Attributes:
        source: Station number of the departure station.
        dest: Station number of the arrival station.
        distance: Distance in meters.
        weight: Edge weight used by path search (equal to distance, as float).
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = float(distance)
        self.line = line

    def __repr__(self):
        return f"Edge({self.source!r} -> {self.dest!r}, {self.distance} m, {self.line!r})"


class Graph:
    """Weighted directed graph of subway stations.

    Station numbers are assigned by the caller (see network.SubwayNetwork).
    Each connection is usable only in the direction it was added.

    Attributes:
        adjacency: dict mapping station number -> list[Edge] of outgoing edges.
        station_lines: dict mapping station name -> list of line names serving it.
    """

    def __init__(self):
        self.adjacency = {}
        self.station_lines = {}

    def add_node(self, number):
        """Ensure a station number exists as a graph node."""
        self.adjacency.setdefault(number, [])

    def has_node(self, number):
        """Return True if the station number is a node of the graph."""
        return number in self.adjacency

    def nodes(self):
        """Return a list of all station numbers in the graph."""
        return list(self.adjacency.keys())

    def node_count(self):
        """Return the number of stations in the graph."""
        return len(self.adjacency)

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) list of lines for a station."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoint nodes when needed."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency[edge.source].append(edge)

    def neighbors(self, number):
        """Return the outgoing edges of a station number (empty list if unknown)."""
        return self.adjacency.get(number, [])

    def edges(self):
        """Yield every edge in the graph."""
        for edge_list in self.adjacency.values():
            yield from edge_list

    def edge_count(self):
        """Return the total number of directed edges."""
        return sum(len(edge_list) for edge_list in self.adjacency.values())

    def find_edges(self, source, dest):
        """Return all edges going from source to dest."""
        return [edge for edge in self.neighbors(source) if edge.dest == dest]

    def update_distance(self, source, dest, distance):
        """Update the distance of all edges from source to dest.

        Returns:
            int: Number of edges updated.
        """
        changed = 0
        for edge in self.find_edges(source, dest):
            edge.distance = distance
            edge.weight = float(distance)
            changed += 1
        return changed


@dataclass
class Station:
    """Station record: name, number and transfer flag."""
    name: str
    number: str
    is_transfer: bool = False


@dataclass
class Line:
    """Line record: name and ordered station names."""
    name: str
    station_sequence: list = field(default_factory=list)


@dataclass
class RouteSegment:
    """A contiguous ride on one line."""
    line_name: str
    start_station: str
    end_station: str
    distance_meters: float


@dataclass
class TransferPoint:
    """A station where the passenger changes lines."""
    station_name: str
    lines_involved: list = field(default_factory=list)


@dataclass
class Route:
    """A computed journey: ordered station names, segments and transfers."""
    total_distance_meters: float
    mode: str
    transfer_count: int
    station_sequence: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)


@dataclass
class PathSummary:
    """Key figures extracted from a route."""
    total_distance_meters: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Query:
    """A passenger query as entered through the CLI."""
    origin: str
    destination: str
    mode: str
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class Report:
    """A rendered report in a given format."""
    format: str
    content: str
    output_file: Optional[str] = None
