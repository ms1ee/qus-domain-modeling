"""
Core data structures: Edge, Graph and simple domain objects
(Station, Line, Connection, Transfer, Route).
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Edge:
    """
    A weighted edge between two stations (identified by station numbers).

    Attributes:
        source:   station number of the origin
        dest:     station number of the destination
        distance: distance in meters
        weight:   same as distance (used by the shortest path algorithm)
        line:     name of the subway line this edge belongs to
    """

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError(f"Edge distance must be numeric, got {distance!r}")
        if math.isnan(distance) or distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance!r}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, v):
        """Return the endpoint opposite to ``v``."""
        if v == self.source:
            return self.dest
        if v == self.dest:
            return self.source
        raise ValueError(f"Vertex {v} is not an endpoint of this edge")

    def reversed(self):
        """Return a new edge going in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """
    Weighted undirected graph stored as adjacency lists.

    Station numbers are assigned by the caller. Each undirected connection is
    stored once in ``edges`` and twice in ``adjacency`` (once per direction, so
    that every edge in ``adjacency[v]`` has ``edge.source == v``).
    """

    def __init__(self):
        self.adjacency: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.edges: List[Edge] = []

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, v):
        if v not in self.adjacency:
            self.adjacency[v] = []

    @property
    def vertices(self):
        return list(self.adjacency.keys())

    @property
    def vertex_count(self):
        return len(self.adjacency)

    @property
    def edge_count(self):
        return len(self.edges)

    def V(self):
        return self.vertex_count

    def E(self):
        return self.edge_count

    # ---- station lines --------------------------------------------------
    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (duplicates removed, order kept)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines or []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge.reversed())
        self.edges.append(edge)

    def adj(self, v):
        """Edges leaving vertex ``v`` (each has ``source == v``)."""
        return self.adjacency.get(v, [])

    def degree(self, v):
        return len(self.adjacency.get(v, []))

    def __repr__(self):
        return f"Graph(V={self.vertex_count}, E={self.edge_count})"


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@dataclass
class Station:
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    name: str
    stations: List[str] = field(default_factory=list)


@dataclass
class Connection:
    source: str
    dest: str
    distance: int
    line: str


@dataclass
class Transfer:
    station_name: str
    from_line: str
    to_line: str

    def to_dict(self):
        return {"station": self.station_name, "from_line": self.from_line, "to_line": self.to_line}


@dataclass
class Route:
    start: str
    end: str
    mode: str
    station_sequence: List[str]
    total_distance_meters: float
    transfer_count: int
    estimated_time_minutes: float
    involved_lines: List[str]
    transfers: List[Transfer]
    segments: List[dict]
    fare: int
    max_transfers: Optional[int] = None
    line_preference: List[str] = field(default_factory=list)

    @property
    def total_distance_km(self):
        return round(self.total_distance_meters / 1000.0, 2)

    def to_dict(self):
        return {
            "query": {
                "start": self.start,
                "end": self.end,
                "mode": self.mode,
                "max_transfers": self.max_transfers,
                "line_preference": list(self.line_preference),
            },
            "path": list(self.station_sequence),
            "station_count": len(self.station_sequence),
            "distance": {
                "meters": self.total_distance_meters,
                "kilometers": self.total_distance_km,
            },
            "distance_meters": self.total_distance_meters,
            "distance_km": self.total_distance_km,
            "fare": self.fare,
            "fare_text": f"Fare: {self.fare} yuan",
            "estimated_time_minutes": self.estimated_time_minutes,
            "transfer_count": self.transfer_count,
            "transfers": [t.to_dict() for t in self.transfers],
            "lines": list(self.involved_lines),
            "segments": [dict(s) for s in self.segments],
        }
