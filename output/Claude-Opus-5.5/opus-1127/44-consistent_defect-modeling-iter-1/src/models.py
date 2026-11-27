"""Core data structures: stations, lines, edges, graph and route results."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """A weighted, directed connection between two station numbers."""

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight: the inter-station distance in meters."""
        return self.distance

    def __repr__(self):
        return "Edge(%r -> %r, %r m, %r)" % (self.source, self.dest,
                                            self.distance, self.line)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == \
            (other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted directed graph using adjacency lists.

    Station numbers are assigned by the caller; the graph only stores them.
    Each edge is usable only in the direction it was added.
    """

    def __init__(self):
        self.adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}

    # ---- node management -------------------------------------------------
    def add_vertex(self, v):
        """Ensure vertex ``v`` exists in the graph."""
        if v not in self.adj:
            self.adj[v] = []

    def set_station_lines(self, station_name, lines):
        """Record the lines a station belongs to."""
        self.station_lines[station_name] = list(lines or [])

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self.adj.keys())

    @property
    def V(self):
        return len(self.adj)

    @property
    def E(self):
        return sum(len(edges) for edges in self.adj.values())

    # ---- edge management -------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge (only usable from edge.source to edge.dest)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)

    def remove_edge(self, source, dest, line=None):
        """Remove directed edges source->dest (optionally only on ``line``)."""
        if source not in self.adj:
            return 0
        before = len(self.adj[source])
        self.adj[source] = [e for e in self.adj[source]
                            if not (e.dest == dest and
                                    (line is None or e.line == line))]
        return before - len(self.adj[source])

    def edges_from(self, v):
        """Return the outgoing edges of vertex ``v``."""
        return self.adj.get(v, [])

    def edges(self):
        """Iterate over all edges."""
        for edges in self.adj.values():
            for e in edges:
                yield e


@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self) -> bool:
        return len(set(self.lines)) > 1


@dataclass
class Line:
    name: str
    stations: List[str] = field(default_factory=list)


@dataclass
class TransferPoint:
    station_name: str
    from_line: str
    to_line: str


@dataclass
class Segment:
    line: str
    stations: List[str]
    distance: int


@dataclass
class Route:
    start: str
    end: str
    mode: str
    station_sequence: List[str]
    total_distance: int
    transfer_count: int
    estimated_time: float
    involved_lines: List[str]
    fare: int
    transfers: List[TransferPoint] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)


@dataclass
class PathSummary:
    total_distance: int
    total_fare: int
    transfer_count: int
    estimated_time: float


@dataclass
class DataIntegrityCheck:
    station_coverage_valid: bool = True
    connection_integrity_valid: bool = True
    distance_accuracy_valid: bool = True
    messages: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return (self.station_coverage_valid and
                self.connection_integrity_valid and
                self.distance_accuracy_valid)


@dataclass
class QueryConfiguration:
    output_file: Optional[str] = None
    format: str = "text"
    mode: str = "shortest_distance"
    max_transfers: Optional[int] = None
    line_preference: Optional[str] = None
    check_data: bool = False
