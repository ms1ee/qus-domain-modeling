"""Core data structures: stations, lines, edges and the network graph."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Station:
    """A subway station."""
    name: str
    number: int
    lines: List[str] = field(default_factory=list)

    @property
    def is_transfer_station(self):
        return len(self.lines) > 1


@dataclass
class Line:
    """A subway line with its ordered station sequence."""
    name: str
    station_sequence: List[str] = field(default_factory=list)


class Edge:
    """A directed weighted edge between two station numbers."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def from_(self):
        return self.source

    def to(self):
        return self.dest

    def __repr__(self):
        return (f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, "
                f"{self.line!r})")

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == \
            (other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller. Each edge is usable only in
    its listed direction.
    """

    def __init__(self):
        self.adj: Dict[int, List[Edge]] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self._edge_count = 0

    # ----- vertices -----
    def add_vertex(self, v):
        self.adj.setdefault(v, [])

    def vertices(self):
        return list(self.adj.keys())

    def V(self):
        return len(self.adj)

    def E(self):
        return self._edge_count

    # ----- station metadata -----
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edges -----
    def add_edge(self, edge):
        self.adj.setdefault(edge.source, []).append(edge)
        self.adj.setdefault(edge.dest, [])
        self._edge_count += 1

    def edges_from(self, v):
        return self.adj.get(v, [])

    def edges(self):
        for lst in self.adj.values():
            for e in lst:
                yield e

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of an existing edge. Returns True on success."""
        updated = False
        for e in self.adj.get(source, []):
            if e.dest == dest and (line is None or e.line == line):
                e.distance = distance
                e.weight = distance
                updated = True
        return updated
