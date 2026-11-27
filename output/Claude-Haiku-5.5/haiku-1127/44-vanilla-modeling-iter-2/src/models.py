"""Core graph data structures for the subway network.

Station numbers are integers assigned by the caller (see subway_network.py).
The Graph is an undirected weighted graph stored as adjacency lists.
"""

import sys


class Edge:
    """An undirected weighted connection between two stations on one line.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance in meters.
        line: name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to `vertex`."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with station-line metadata.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adj = {}          # station number -> list[Edge]
        self._edges = []        # every undirected edge exactly once
        self.station_lines = {}  # station name -> list[str]

    # ----- vertices and edges -------------------------------------------------
    def add_vertex(self, vertex):
        """Ensure `vertex` exists in the graph."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the station number exists in the graph."""
        return vertex in self._adj

    def add_edge(self, edge):
        """Add an undirected edge; it is visible from both endpoints."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, vertex):
        """Return the list of edges incident to `vertex`."""
        return self._adj.get(vertex, [])

    def vertices(self):
        """Return all station numbers in the graph."""
        return list(self._adj.keys())

    def edges(self):
        """Return all undirected edges (each listed once)."""
        return list(self._edges)

    # ----- station metadata ---------------------------------------------------
    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) lines serving a station."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving the station."""
        return list(self.station_lines.get(station_name, []))

    # ----- statistics ---------------------------------------------------------
    @property
    def node_count(self):
        """Number of stations (nodes)."""
        return len(self._adj)

    @property
    def edge_count(self):
        """Number of undirected connections (edges)."""
        return len(self._edges)

    def memory_usage_mb(self):
        """Approximate memory footprint of the graph structures in megabytes."""
        total = sys.getsizeof(self._adj) + sys.getsizeof(self._edges)
        for edge_list in self._adj.values():
            total += sys.getsizeof(edge_list)
        for edge in self._edges:
            total += sys.getsizeof(edge)
        total += sys.getsizeof(self.station_lines)
        for lines in self.station_lines.values():
            total += sys.getsizeof(lines)
        return total / (1024.0 * 1024.0)
