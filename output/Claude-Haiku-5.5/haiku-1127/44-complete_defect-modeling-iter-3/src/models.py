"""Core data models for the Beijing Subway fare calculation system.

Contains the weighted undirected graph structure used by the path
calculation module, plus lightweight dataclasses describing routes,
transfers, fares, queries, reports and data integrity results.
"""

from dataclasses import dataclass, field
from typing import List, Optional


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Distance between the stations in meters.
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source: int, dest: int, distance: float, line: str):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self) -> float:
        """Edge weight used by shortest-path search (equals the distance)."""
        return self.distance

    def other(self, number: int) -> int:
        """Return the endpoint opposite to ``number``."""
        if number == self.source:
            return self.dest
        if number == self.dest:
            return self.source
        raise ValueError(f"Station number {number} is not an endpoint of this edge")

    def __repr__(self) -> str:
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (see ``network.SubwayNetwork``);
    the graph only records the mapping and the adjacency lists.

    Attributes:
        station_to_number: Mapping from station name to station number.
        number_to_station: Mapping from station number to station name.
        station_lines: Mapping from station name to the list of its lines.
    """

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}
        self._adjacency = {}  # number -> list of (neighbor_number, Edge)
        self._edge_count = 0

    @property
    def node_count(self) -> int:
        """Number of station nodes in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """Number of undirected edges in the graph."""
        return self._edge_count

    def register_station(self, station_name: str, number: int) -> None:
        """Register a station name with an externally assigned number."""
        existing = self.station_to_number.get(station_name)
        if existing is not None and existing != number:
            raise ValueError(f"Station '{station_name}' is already registered with number {existing}")
        owner = self.number_to_station.get(number)
        if owner is not None and owner != station_name:
            raise ValueError(f"Number {number} is already used by station '{owner}'")
        self.station_to_number[station_name] = number
        self.number_to_station[number] = station_name
        self.station_lines.setdefault(station_name, [])
        self._adjacency.setdefault(number, [])

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the list of lines that serve a station (duplicates removed)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge to the graph."""
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self._adjacency.setdefault(edge.source, []).append((edge.dest, edge))
        self._adjacency.setdefault(edge.dest, []).append((edge.source, edge))
        self._edge_count += 1

    def neighbors(self, number: int) -> list:
        """Return a list of (neighbor_number, Edge) tuples for a station."""
        return self._adjacency.get(number, [])

    def has_node(self, number: int) -> bool:
        """Return True if the station number exists in the graph."""
        return number in self._adjacency

    def has_station(self, station_name: str) -> bool:
        """Return True if the station name is registered."""
        return station_name in self.station_to_number

    def get_number(self, station_name: str) -> int:
        """Return the number of a registered station name."""
        return self.station_to_number[station_name]

    def get_name(self, number: int) -> str:
        """Return the name of a station number."""
        return self.number_to_station[number]

    def station_names(self) -> List[str]:
        """Return all registered station names."""
        return list(self.station_to_number)


@dataclass
class Fare:
    """Computed fare for a trip."""

    amount_yuan: int
    rounded_distance_km: float


@dataclass
class Segment:
    """A continuous ride on one line within a route."""

    line: str
    start_station: str
    end_station: str
    station_names: List[str]
    distance_m: float

    @property
    def stop_count(self) -> int:
        """Number of inter-station hops within this segment."""
        return max(len(self.station_names) - 1, 0)


@dataclass
class Transfer:
    """A transfer (line change) at a station."""

    station_name: str
    from_line: str
    to_line: str
    transfer_time_minutes: float = 4.0

    @property
    def involved_lines(self) -> List[str]:
        """Unique line names involved in this transfer (in order)."""
        return list(dict.fromkeys([self.from_line, self.to_line]))

    @property
    def involved_line_count(self) -> int:
        """Number of distinct lines involved in this transfer."""
        return len(self.involved_lines)


@dataclass
class Route:
    """A computed journey between two stations."""

    start_station: str
    end_station: str
    mode: str
    stations: List[str]
    segments: List[Segment]
    transfers: List[Transfer]
    total_distance_m: float
    estimated_time_min: float
    fare: Fare

    @property
    def transfer_count(self) -> int:
        """Number of transfers on this route."""
        return len(self.transfers)

    @property
    def lines(self) -> List[str]:
        """Unique line names used by this route, in travel order."""
        return list(dict.fromkeys(segment.line for segment in self.segments))

    @property
    def total_distance_km(self) -> float:
        """Total distance in kilometers."""
        return self.total_distance_m / 1000.0


@dataclass
class Query:
    """User query parameters together with output options."""

    start_station: str
    end_station: str
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None
    output_format: str = "text"
    output_file: Optional[str] = None


@dataclass
class Report:
    """A rendered path report."""

    format: str
    content: str
    output_file: Optional[str] = None


@dataclass
class DataIntegrityReport:
    """Result of a data integrity check."""

    passed: bool
    issues: List[str] = field(default_factory=list)
