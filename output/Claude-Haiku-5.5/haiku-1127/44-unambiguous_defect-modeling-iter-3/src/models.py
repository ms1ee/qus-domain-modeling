"""Core domain models for the Beijing Subway fare calculation system."""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubwayError(Exception):
    """Base class for all errors raised by the subway fare system."""


class InputError(SubwayError):
    """Raised when user input is malformed or logically invalid."""


class StationNotFoundError(SubwayError):
    """Raised when a referenced station does not exist in the network."""


class PathNotFoundError(SubwayError):
    """Raised when no route exists between two stations."""


class PathfindingError(SubwayError):
    """Raised when a route cannot be computed under the given constraints."""


class FareError(SubwayError):
    """Raised when a fare cannot be calculated."""


# ---------------------------------------------------------------------------
# Graph structures
# ---------------------------------------------------------------------------

class Edge:
    """A weighted, undirected connection between two stations.

    ``source`` and ``dest`` are station numbers (integers assigned by the caller).
    ``weight`` equals the inter-station distance in meters.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = str(line)

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint of this edge that is not ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph modelling the subway network.

    Station numbers are assigned by the caller via ``add_station``; the graph
    only stores the mapping and the adjacency lists.
    """

    def __init__(self):
        # adjacency: station number -> list of incident Edge objects
        self.adjacency = {}
        # Bidirectional station name <-> number mapping
        self.station_to_number = {}
        self.number_to_station = {}
        # station name -> list of line names serving the station
        self.station_lines = {}
        self._edges = []

    # -- station management -------------------------------------------------

    def add_station(self, name, number):
        """Register a station with its caller-assigned number."""
        if name in self.station_to_number and self.station_to_number[name] != number:
            raise ValueError(f"Station '{name}' already registered with a different number")
        if number in self.number_to_station and self.number_to_station[number] != name:
            raise ValueError(f"Station number {number} already used by another station")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.adjacency.setdefault(number, [])
        self.station_lines.setdefault(name, [])

    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station (a station with >1 line is a transfer station)."""
        if station_name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{station_name}' does not exist")
        self.station_lines[station_name] = list(lines)

    def has_station(self, name):
        """Return True if a station with this name is registered."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for ``name``."""
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise StationNotFoundError(f"Station '{name}' does not exist") from exc

    def name_of(self, number):
        """Return the station name for ``number``."""
        return self.number_to_station[number]

    def is_transfer_station(self, name):
        """Return True if the station is served by more than one line."""
        return len(self.station_lines.get(name, [])) > 1

    # -- edge management ----------------------------------------------------

    def add_edge(self, edge):
        """Add an undirected edge; both endpoints must already be registered."""
        for number in (edge.source, edge.dest):
            if number not in self.adjacency:
                raise StationNotFoundError(f"Station number {number} is not registered")
        if edge.distance < 0:
            raise ValueError("Edge distance cannot be negative")
        self.adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def neighbors(self, number):
        """Return the list of edges incident to station ``number``."""
        return self.adjacency.get(number, [])

    @property
    def edges(self):
        """Return a copy of the list of all edges."""
        return list(self._edges)

    @property
    def station_count(self):
        return len(self.station_to_number)

    @property
    def edge_count(self):
        return len(self._edges)


# ---------------------------------------------------------------------------
# Query and path results
# ---------------------------------------------------------------------------

@dataclass
class Query:
    """A passenger's route query and its configuration."""

    start_station: str
    end_station: str
    mode: str = "shortest_distance"
    max_transfers: int = None
    line_preference: str = None


@dataclass
class Segment:
    """A continuous ride on a single line."""

    line: str
    start: str
    end: str
    stations: list = field(default_factory=list)
    distance_m: float = 0.0


@dataclass
class TransferInfo:
    """A transfer point where the passenger changes from one line to another."""

    station: str
    from_line: str
    to_line: str


@dataclass
class Path:
    """A computed route through the subway network."""

    station_sequence: list
    total_distance_m: float
    transfer_count: int
    involved_lines: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    transfers: list = field(default_factory=list)


@dataclass
class PathSummary:
    """Key information extracted from a path."""

    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Report:
    """A rendered query result in a particular format ('text' or 'json')."""

    format: str
    content: str
