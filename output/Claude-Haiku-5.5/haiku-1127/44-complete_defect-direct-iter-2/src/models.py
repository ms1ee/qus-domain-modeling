"""Core graph data structures for the subway network.

The Graph stores an undirected weighted adjacency list keyed by integer
station numbers. Station numbers are assigned by the caller (see
subway_network.SubwayNetwork), not by the Graph itself.
"""

import math


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters (also used as the weight).
        line: name of the subway line that operates this segment.
    """

    def __init__(self, source, dest, distance, line):
        if source == dest:
            raise ValueError("self-loop edges are not allowed")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("edge distance must be a number")
        if not math.isfinite(distance) or distance < 0:
            raise ValueError("edge distance must be a finite non-negative number")
        if not isinstance(line, str) or not line:
            raise ValueError("edge line must be a non-empty string")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equals distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return (f"Edge({self.source}, {self.dest}, "
                f"distance={self.distance}, line={self.line!r})")


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names the
            station belongs to (used for transfer detection).
    """

    def __init__(self):
        self._adj = {}
        self._edge_count = 0
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Register a vertex (station number) if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def set_station_lines(self, station_name, lines):
        """Set the list of lines that serve a station (stored as a copy)."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge; it is registered in both endpoint lists."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edge_count += 1

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex`` (do not mutate)."""
        return self._adj.get(vertex, [])

    def vertices(self):
        """Return the list of all vertex numbers."""
        return list(self._adj.keys())

    def edges(self):
        """Return each undirected edge exactly once."""
        seen = set()
        result = []
        for edge_list in self._adj.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adj)

    def num_edges(self):
        """Return the number of undirected edges."""
        return self._edge_count
