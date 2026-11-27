"""Core data structures: graph, edges and domain value objects."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """A directed, weighted edge between two station numbers.

    ``weight`` equals the inter-station distance in meters; ``line`` is the
    name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line):
        if distance is None or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        """Return one endpoint of the edge (the source)."""
        return self.source

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return the same connection travelled in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r} -> {self.dest!r}, {self.weight}m, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.weight, self.line) == (
            other.source, other.dest, other.weight, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.weight, self.line))


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Vertices are station numbers assigned by the caller.  Each undirected
    connection is stored as two directed ``Edge`` objects (one per direction)
    so that path reconstruction always yields correctly oriented edges.
    Multiple edges between the same pair of stations (on different lines)
    are allowed; this is how multi-line interchanges are represented.
    """

    def __init__(self):
        self.adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.edges: List[Edge] = []  # original (undirected) edges as added

    # ------------------------------------------------------------------ nodes
    def add_vertex(self, vertex):
        """Add a vertex if not already present."""
        self.adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        return vertex in self.adj

    def vertices(self):
        return list(self.adj.keys())

    @property
    def V(self):
        """Number of vertices."""
        return len(self.adj)

    @property
    def E(self):
        """Number of undirected edges."""
        return len(self.edges)

    vertex_count = V
    edge_count = E

    def set_station_lines(self, station_name, lines):
        """Record the lines served by a station (by station name)."""
        self.station_lines[station_name] = list(lines or [])

    # ------------------------------------------------------------------ edges
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.source != edge.dest:
            self.adj[edge.dest].append(edge.reversed())
        self.edges.append(edge)

    def adjacent(self, vertex):
        """Return the outgoing edges of ``vertex``."""
        return self.adj.get(vertex, [])

    def degree(self, vertex):
        return len(self.adj.get(vertex, []))

    def to_dict(self):
        """Return the adjacency lists as a plain dictionary.

        Format: ``{vertex: [(neighbour, distance, line), ...]}``
        """
        return {v: [(e.dest, e.weight, e.line) for e in edges] for v, edges in self.adj.items()}

    def __repr__(self):
        return f"Graph(V={self.V}, E={self.E})"


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self) -> bool:
        return len(set(self.lines)) > 1


@dataclass
class Connection:
    source: str
    dest: str
    distance: int
    line: str


@dataclass
class Line:
    name: str
    station_sequence: List[str] = field(default_factory=list)
    transfer_stations: List[str] = field(default_factory=list)


@dataclass
class FareTier:
    min_distance_km: int
    max_distance_km: int
    fare: int


@dataclass
class Fare:
    amount: int
    distance_km: float


@dataclass
class Route:
    station_sequence: List[str]
    total_distance: int
    transfer_count: int
    involved_lines: List[str]
    estimated_time: float
    fare: int
    segments: List[dict] = field(default_factory=list)
    transfer_stations: List[str] = field(default_factory=list)


@dataclass
class PathSummary:
    total_distance_km: float
    total_fare: int
    transfer_count: int
    estimated_time: float


@dataclass
class QueryConfiguration:
    output_file: Optional[str] = None
    format: str = "text"
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None
    check_data: bool = False
