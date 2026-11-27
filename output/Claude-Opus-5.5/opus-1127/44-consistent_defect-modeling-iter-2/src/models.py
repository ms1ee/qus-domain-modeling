"""Core data structures: edges, graph, stations, lines."""

from dataclasses import dataclass, field
from typing import List


class Edge:
    """A directed, weighted edge between two stations (by station number)."""

    __slots__ = ("source", "dest", "distance", "weight", "line")

    def __init__(self, source, dest, distance, line=None):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller; the graph simply stores the
    edges it is given.  Each edge is usable only in its listed direction.
    """

    def __init__(self):
        self.adj_list = {}          # station number -> list[Edge]
        self.station_lines = {}     # station name -> list[str]
        self.edge_count = 0

    # ---- vertices -------------------------------------------------------
    def add_vertex(self, v):
        if v not in self.adj_list:
            self.adj_list[v] = []

    @property
    def vertex_count(self):
        return len(self.adj_list)

    def V(self):
        return self.vertex_count

    def E(self):
        return self.edge_count

    def vertices(self):
        return list(self.adj_list.keys())

    def has_vertex(self, v):
        return v in self.adj_list

    # ---- edges ----------------------------------------------------------
    def add_edge(self, edge):
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj_list[edge.source].append(edge)
        self.edge_count += 1

    def adj(self, v):
        return self.adj_list.get(v, [])

    def edges(self):
        for lst in self.adj_list.values():
            for e in lst:
                yield e

    def remove_edges(self, source, dest, line=None):
        lst = self.adj_list.get(source, [])
        keep = [e for e in lst if not (e.dest == dest and (line is None or e.line == line))]
        self.edge_count -= len(lst) - len(keep)
        if source in self.adj_list:
            self.adj_list[source] = keep

    # ---- station metadata ----------------------------------------------
    def set_station_lines(self, station_name, lines):
        self.station_lines[station_name] = list(lines) if lines else []

    def get_station_lines(self, station_name):
        return self.station_lines.get(station_name, [])

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1


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
    station_sequence: List[str] = field(default_factory=list)


@dataclass
class Transfer:
    station: str
    from_line: str
    to_line: str
    transfer_time: float = 5.0
    transfer_distance: int = 0
