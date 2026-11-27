"""Core graph data structures for the subway network.

Station numbers (integers) are assigned by the caller (see network.py);
the Graph stores station names only for the purpose of line lookups.
"""


class Edge:
    """A weighted, directed connection between two stations.

    Attributes:
        source: Station number of the origin station.
        dest: Station number of the destination station.
        distance: Physical distance in meters (also used as the edge weight).
        line: Name of the subway line that serves this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight, equal to the physical distance in meters."""
        return self.distance

    def __repr__(self):
        return (f"Edge(source={self.source!r}, dest={self.dest!r}, "
                f"distance={self.distance!r}, line={self.line!r})")


class Graph:
    """Weighted directed graph with adjacency lists.

    Each connection is usable only in the direction it was added.

    Attributes:
        adj: dict mapping station number -> list of outgoing Edge objects.
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self.adj = {}
        self.station_lines = {}

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station.

        Args:
            station_name: Official station name.
            lines: Iterable of line names.
        """
        self.station_lines[station_name] = list(lines)

    def add_vertex(self, station_number):
        """Ensure a station number exists as a vertex of the graph."""
        self.adj.setdefault(station_number, [])

    def add_edge(self, edge):
        """Add a directed edge (and its endpoint vertices) to the graph.

        Args:
            edge: An Edge instance.
        """
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.adj[edge.source].append(edge)

    def adjacent(self, station_number):
        """Return the outgoing edges of a station (empty list if unknown)."""
        return self.adj.get(station_number, [])

    def remove_edges(self, source, dest):
        """Remove all directed edges from source to dest.

        Returns:
            int: Number of removed edges.
        """
        if source not in self.adj:
            return 0
        before = len(self.adj[source])
        self.adj[source] = [e for e in self.adj[source] if e.dest != dest]
        return before - len(self.adj[source])

    def vertices(self):
        """Return a list of all station numbers in the graph."""
        return list(self.adj.keys())

    def num_vertices(self):
        """Return the number of stations in the graph."""
        return len(self.adj)

    def num_edges(self):
        """Return the number of directed edges in the graph."""
        return sum(len(edges) for edges in self.adj.values())
