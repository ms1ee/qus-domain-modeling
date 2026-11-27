"""Core domain model: weighted undirected graph of subway stations."""

import sys
from dataclasses import dataclass


class Edge:
    """An undirected weighted connection between two stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance in meters (used as the edge weight).
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
        """Edge weight, equal to the inter-station distance in meters."""
        return self.distance

    def other_end(self, node):
        """Return the endpoint opposite to ``node``.

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
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller (see DataManager); the graph
    only stores nodes, edges and the station-to-lines mapping.
    """

    def __init__(self):
        self._adjacency = {}      # station number -> list of incident Edge objects
        self._edge_count = 0
        self.station_lines = {}   # station name -> list of line names

    def add_node(self, node):
        """Register a station number as a node (no-op if it already exists)."""
        self._adjacency.setdefault(node, [])

    def set_station_lines(self, station_name, lines):
        """Set the subway lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge; both endpoints receive it in their adjacency lists."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edge_count += 1

    def adjacent(self, node):
        """Return the list of edges incident to ``node`` (empty if unknown)."""
        return self._adjacency.get(node, [])

    def contains_node(self, node):
        """Return True if the station number is a node of the graph."""
        return node in self._adjacency

    def nodes(self):
        """Return the list of all station numbers."""
        return list(self._adjacency.keys())

    def is_transfer_station(self, station_name):
        """A station is a transfer (interchange) station if served by more than one line."""
        return len(self.station_lines.get(station_name, [])) > 1

    @property
    def node_count(self):
        return len(self._adjacency)

    @property
    def edge_count(self):
        return self._edge_count

    def memory_usage_mb(self):
        """Approximate memory footprint of the graph structure in megabytes."""
        total = sys.getsizeof(self._adjacency)
        seen = set()
        for node, edges in self._adjacency.items():
            total += sys.getsizeof(node) + sys.getsizeof(edges)
            for edge in edges:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    total += sys.getsizeof(edge)
        return total / (1024 * 1024)


@dataclass
class Station:
    """Station record (domain model reference)."""

    station_id: int
    name: str
    is_transfer_station: bool = False


@dataclass
class Line:
    """Subway line record (domain model reference)."""

    name: str
    line_code: str
