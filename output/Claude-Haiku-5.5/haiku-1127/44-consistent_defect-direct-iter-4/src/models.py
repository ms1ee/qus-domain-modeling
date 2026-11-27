"""Graph data structures for the subway network.

The graph is a weighted *directed* graph. Each Edge is usable only in the
direction in which it was listed. Station numbers are assigned by the caller
(see network.SubwayNetwork); Graph only stores numbers and station names.
"""


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: Station number of the origin.
        dest: Station number of the destination.
        distance: Physical distance in meters.
        line: Name of the subway line operating this connection.
        weight: Dijkstra base weight; equal to the distance in meters.
    """

    __slots__ = ("source", "dest", "distance", "line", "weight")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line
        self.weight = distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.weight}m, line={self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists keyed by station number."""

    def __init__(self):
        # station number -> list of outgoing Edge objects
        self._adj = {}
        # station name -> list of subway line names serving the station
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Ensure a station number exists as a vertex of the graph."""
        self._adj.setdefault(vertex, [])

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station (replaces any previous value)."""
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoints if necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adj(self, vertex):
        """Return the list of outgoing edges of a vertex (empty if unknown)."""
        return self._adj.get(vertex, [])

    def vertices(self):
        """Return a list of all station numbers in the graph."""
        return list(self._adj.keys())

    def edges(self):
        """Iterate over all edges of the graph."""
        for edge_list in self._adj.values():
            yield from edge_list

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adj)

    def num_edges(self):
        """Return the number of directed edges."""
        return sum(len(edge_list) for edge_list in self._adj.values())

    def find_edges(self, source, dest):
        """Return all edges going from source to dest."""
        return [edge for edge in self.adj(source) if edge.dest == dest]

    def has_edge(self, source, dest):
        """Return True if a directed edge source -> dest exists."""
        return bool(self.find_edges(source, dest))

    def update_distance(self, source, dest, distance):
        """Update the distance of all edges source -> dest.

        Returns:
            int: Number of edges updated.
        """
        count = 0
        for edge in self.find_edges(source, dest):
            edge.distance = distance
            edge.weight = distance
            count += 1
        return count
