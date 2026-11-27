"""
Core graph data structures for the subway network.

Stations are represented as integer nodes. The caller assigns the station
numbers (see ``network.SubwayNetwork``). Edges are undirected and carry a
weight equal to the physical distance in meters and the name of the line.
"""

import sys


class Edge:
    """
    A weighted, undirected connection between two stations on a subway line.

    Attributes:
        source (int): Station number of one endpoint.
        dest (int): Station number of the other endpoint.
        distance (float): Physical distance in meters.
        line (str): Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = int(source)
        self.dest = int(dest)
        self.distance = float(distance)
        self.line = str(line)
        if self.distance < 0:
            raise ValueError("Edge distance must be non-negative")

    @property
    def weight(self):
        """The edge weight used by shortest path algorithms (distance in meters)."""
        return self.distance

    def other(self, node):
        """
        Return the endpoint of this edge opposite to ``node``.

        Raises:
            ValueError: If ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"Node {node} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """
    Weighted undirected graph with adjacency lists.

    Nodes are station numbers. ``station_lines`` maps station names to the
    list of line names serving that station; a station served by more than one
    line is a transfer (interchange) station.
    """

    def __init__(self):
        self._adjacency = {}      # station number -> list[Edge]
        self._edges = []          # all edges, each stored once
        self.station_lines = {}   # station name -> list[str]

    # ------------------------------------------------------------------
    # Node and station management
    # ------------------------------------------------------------------
    def add_node(self, node):
        """Ensure that a node exists in the graph."""
        self._adjacency.setdefault(int(node), [])

    def has_node(self, node):
        """Return True if the node exists in the graph."""
        return node in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Set the line affiliations of a station (duplicates are removed, order kept)."""
        unique = list(dict.fromkeys(str(line) for line in lines))
        self.station_lines[station_name] = unique

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------
    def add_edge(self, edge):
        """
        Add an undirected edge to the graph.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent_edges(self, node):
        """Return the list of edges incident to ``node`` (empty if unknown)."""
        return self._adjacency.get(node, [])

    def find_edges(self, a, b):
        """Return all edges directly connecting nodes ``a`` and ``b``."""
        return [e for e in self._adjacency.get(a, []) if e.other(a) == b]

    def update_edge_distance(self, a, b, distance):
        """
        Update the distance of all edges between nodes ``a`` and ``b``.

        Returns:
            int: Number of edges updated.
        """
        edges = self.find_edges(a, b)
        for edge in edges:
            edge.distance = float(distance)
        return len(edges)

    def nodes(self):
        """Return a list of all node numbers."""
        return list(self._adjacency.keys())

    def edges(self):
        """Return a list of all edges."""
        return list(self._edges)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    @property
    def node_count(self):
        """Number of nodes (stations)."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of undirected edges (connections)."""
        return len(self._edges)

    def memory_usage_mb(self):
        """Approximate memory footprint of the graph structure in megabytes."""
        total = sys.getsizeof(self._adjacency) + sys.getsizeof(self._edges)
        total += sys.getsizeof(self.station_lines)
        for lst in self._adjacency.values():
            total += sys.getsizeof(lst)
        for edge in self._edges:
            total += sys.getsizeof(edge) + sys.getsizeof(edge.line)
        return total / (1024 * 1024)
