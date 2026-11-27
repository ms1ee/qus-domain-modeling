"""Core data models: stations, lines, edges, graph, routes."""
from dataclasses import dataclass, field
from enum import Enum


class QueryMode(str, Enum):
    SHORTEST_DISTANCE = "shortest_distance"
    LEAST_TRANSFER = "least_transfer"
    COMPREHENSIVE = "comprehensive"


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


@dataclass
class Station:
    id: int
    name: str
    is_transfer: bool = False


@dataclass
class Line:
    name: str
    station_sequence: list = field(default_factory=list)


class Edge:
    """Directed view of an undirected connection (station numbers)."""

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        return self.distance

    def reversed(self):
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return "Edge(%r, %r, %r, %r)" % (self.source, self.dest, self.distance, self.line)


class Graph:
    """Weighted undirected graph. Station numbers are assigned by the caller."""

    def __init__(self):
        self.adjacency = {}          # number -> list[Edge]
        self.station_to_number = {}  # name -> number
        self.number_to_station = {}  # number -> name
        self.station_lines = {}      # name -> list[str]

    def add_station(self, name, number):
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge (stores both directions)."""
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, []).append(edge.reversed())

    def neighbors(self, number):
        return self.adjacency.get(number, [])

    def has_station(self, name):
        return name in self.station_to_number

    def is_transfer(self, name):
        return len(self.station_lines.get(name, [])) > 1

    def nodes(self):
        return list(self.adjacency.keys())


@dataclass
class Route:
    station_sequence: list
    total_distance: int
    transfer_count: int
    involved_lines: list
    segments: list = field(default_factory=list)   # (line, [stations])
    transfers: list = field(default_factory=list)  # (station, from_line, to_line)


@dataclass
class Query:
    start_station: str
    end_station: str
    mode: str = "shortest_distance"
