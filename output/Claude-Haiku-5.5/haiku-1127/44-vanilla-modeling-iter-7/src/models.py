"""
Core data models for the subway fare system.

Contains the weighted undirected graph (Graph), its edges (Edge), and the
result/value objects used by reporting and the CLI (Query, Transfer, Segment,
Route, PathSummary, Report).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """A weighted, line-tagged connection between two adjacent stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        weight: Edge weight, equal to the distance in meters.
        line: Name of the subway line this connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.line = line
        self.weight = 0.0
        self.distance = distance  # goes through the validating setter

    @property
    def distance(self):
        """Distance in meters (same value as ``weight``)."""
        return self.weight

    @distance.setter
    def distance(self, value):
        value = float(value)
        if value != value or value <= 0:
            raise ValueError(f"Edge distance must be a positive number, got {value}")
        self.weight = value

    def other(self, node):
        """Return the endpoint opposite to ``node``."""
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"Node {node} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}-{self.dest}, {self.weight:.0f}m, line={self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (see SubwayNetwork); the graph
    only stores the mapping and the adjacency structure.

    Attributes:
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        station_lines: dict mapping station name -> list of line names.
        adjacency_list: dict mapping station number -> list of incident Edge objects.
        edges: list of all Edge objects (each undirected edge stored once).
    """

    def __init__(self):
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.adjacency_list: Dict[int, List[Edge]] = {}
        self.edges: List[Edge] = []

    # ----- station management -------------------------------------------------
    def register_station(self, name, number):
        """Register a station with an externally assigned number."""
        if name in self.station_to_number:
            raise ValueError(f"Station '{name}' is already registered")
        if number in self.number_to_station:
            raise ValueError(f"Station number {number} is already in use")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.station_lines.setdefault(name, [])
        self.adjacency_list.setdefault(number, [])

    def has_station(self, name):
        """Return True if a station with this exact name is registered."""
        return name in self.station_to_number

    def set_station_lines(self, name, lines):
        """Set the (de-duplicated, order-preserving) line list of a station."""
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station '{name}'")
        self.station_lines[name] = list(dict.fromkeys(lines))

    def number_of(self, name):
        """Return the station number for a station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_count(self):
        """Return the number of registered stations."""
        return len(self.station_to_number)

    def station_names(self):
        """Return the list of all station names in number order."""
        return [self.number_to_station[n] for n in sorted(self.number_to_station)]

    def rename_station(self, old_name, new_name):
        """Rename a station while keeping its number and edges."""
        if old_name not in self.station_to_number:
            raise KeyError(f"Unknown station '{old_name}'")
        if new_name in self.station_to_number:
            raise ValueError(f"Station '{new_name}' already exists")
        number = self.station_to_number.pop(old_name)
        self.station_to_number[new_name] = number
        self.number_to_station[number] = new_name
        self.station_lines[new_name] = self.station_lines.pop(old_name, [])

    # ----- edge management ----------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge to the adjacency lists of both endpoints."""
        if edge.source not in self.number_to_station or edge.dest not in self.number_to_station:
            raise KeyError("Both endpoints of an edge must be registered stations")
        self.adjacency_list.setdefault(edge.source, []).append(edge)
        if edge.dest != edge.source:
            self.adjacency_list.setdefault(edge.dest, []).append(edge)
        self.edges.append(edge)

    def adjacent(self, number):
        """Return the list of edges incident to a station number."""
        return self.adjacency_list.get(number, [])


@dataclass
class Query:
    """A passenger query: start/end stations plus the chosen options."""
    start_station: str
    end_station: str
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None


@dataclass
class Transfer:
    """A line change at a station."""
    station_name: str
    from_line: str
    to_line: str


@dataclass
class Segment:
    """A continuous ride on one line between two stations."""
    line: str
    from_station: str
    to_station: str
    distance_m: float


@dataclass
class Route:
    """A computed route with derived statistics."""
    station_sequence: List[str]
    total_distance_m: float
    transfer_count: int
    involved_lines: List[str]
    estimated_time_minutes: float
    transfers: List[Transfer] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)


@dataclass
class PathSummary:
    """Key figures extracted from a route."""
    total_distance_km: float
    fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A rendered report, optionally tied to an output file."""
    format: str
    content: str
    output_file_path: Optional[str] = None
