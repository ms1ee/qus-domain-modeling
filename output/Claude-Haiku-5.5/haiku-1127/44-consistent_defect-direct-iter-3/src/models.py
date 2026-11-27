"""
Graph data structures for the subway network.

The graph is a weighted DIRECTED graph: every Edge is usable only in the
direction in which it was declared. Station numbers (vertices) are assigned
by the caller, not by the Graph itself.
"""


class Edge:
    """
    A directed, weighted connection between two stations.

    Attributes:
        source: Station number where the edge starts.
        dest: Station number where the edge ends.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line the connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equals the distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """
    Weighted directed graph implemented with adjacency lists.

    Attributes:
        station_lines: Mapping from station name to the list of line names
                       serving that station.
    """

    def __init__(self):
        self._adj = {}          # vertex -> list[Edge] (outgoing edges)
        self.station_lines = {}  # station name -> list[str]

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, v):
        """Add a vertex (station number) if it does not already exist."""
        if v not in self._adj:
            self._adj[v] = []

    def has_vertex(self, v):
        """Return True if the vertex exists in the graph."""
        return v in self._adj

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adj.keys())

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adj)

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge, creating its endpoints if necessary."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adj(self, v):
        """Return the list of outgoing edges of vertex v (empty list if unknown)."""
        return self._adj.get(v, [])

    def edges(self):
        """Return a list of all edges in the graph."""
        result = []
        for out_edges in self._adj.values():
            result.extend(out_edges)
        return result

    def num_edges(self):
        """Return the number of directed edges."""
        return sum(len(out_edges) for out_edges in self._adj.values())

    def get_edges(self, source, dest):
        """Return all edges going from source to dest."""
        return [e for e in self.adj(source) if e.dest == dest]

    # ----- station line information -----------------------------------------
    def set_station_lines(self, station_name, lines):
        """Set the lines serving a station (keyed by station name)."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
