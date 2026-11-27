"""Core graph model: stations are numbered graph nodes, connections are weighted undirected edges."""

import sys


class Edge:
    """A weighted, undirected connection between two stations on one subway line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters (also used as the edge weight).
        line: Name of the subway line the connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (the distance in meters)."""
        return self.distance

    def other(self, node):
        """Return the endpoint opposite to ``node``."""
        return self.dest if node == self.source else self.source

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller (see DataManager); the graph only
    stores adjacency lists keyed by those numbers. Station names and the lines
    serving each station are kept in ``station_lines``.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    def add_node(self, node):
        """Ensure a station number exists as a node in the graph."""
        self._adjacency.setdefault(node, [])

    def has_node(self, node):
        """Return True if the station number is a node of the graph."""
        return node in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Record the (de-duplicated, order-preserving) lines serving a station."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def add_edge(self, edge):
        """Add an undirected edge; it is stored in both endpoints' adjacency lists."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, node):
        """Return the list of edges incident to ``node`` (do not mutate it)."""
        return self._adjacency.get(node, [])

    def nodes(self):
        """Return a sorted list of all station numbers."""
        return sorted(self._adjacency)

    def edges(self):
        """Return a list of all unique edges."""
        return list(self._edges)

    @property
    def node_count(self):
        """Number of stations (nodes) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of unique connections (edges) in the graph."""
        return len(self._edges)

    def memory_usage_mb(self):
        """Estimate the memory footprint of the graph structures in megabytes."""
        total = (
            sys.getsizeof(self._adjacency)
            + sys.getsizeof(self._edges)
            + sys.getsizeof(self.station_lines)
        )
        for lst in self._adjacency.values():
            total += sys.getsizeof(lst)
        for edge in self._edges:
            total += sys.getsizeof(edge)
        for lines in self.station_lines.values():
            total += sys.getsizeof(lines)
        return total / (1024 * 1024)
