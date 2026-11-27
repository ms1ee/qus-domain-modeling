"""Graph data structures used to model the subway network.

The graph is a weighted adjacency-list structure. Vertices are station
numbers (assigned by the caller), edges carry the inter-station distance in
meters (as ``weight``) and the subway line they belong to. Each edge is only
usable in its stored direction; bidirectional connections are represented by
two edges.
"""


class Edge:
    """A directed, weighted, line-tagged edge.

    Attributes:
        source: Station number of the origin.
        dest: Station number of the destination.
        distance: Distance in meters.
        line: Name of the subway line this edge belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equals the distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source!r} -> {self.dest!r}, {self.distance} m, {self.line!r})"


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned externally; the graph only stores them as
    vertices. ``station_lines`` maps station names to the lines serving them.
    """

    def __init__(self):
        self._adj = {}
        self.station_lines = {}

    # ----- vertex management -------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex if it does not already exist."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists."""
        return vertex in self._adj

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adj.keys())

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self._adj)

    # ----- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge, creating its endpoints if necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)

    def adj(self, vertex):
        """Return the list of outgoing edges of a vertex."""
        return self._adj.get(vertex, [])

    def edges(self):
        """Return a list of all edges in the graph."""
        result = []
        for edges in self._adj.values():
            result.extend(edges)
        return result

    def edge_count(self):
        """Return the number of directed edges."""
        return sum(len(edges) for edges in self._adj.values())

    def edges_between(self, source, dest):
        """Return all edges from ``source`` to ``dest`` (any line)."""
        return [e for e in self.adj(source) if e.dest == dest]

    def remove_edges_between(self, source, dest):
        """Remove all edges from ``source`` to ``dest``; return the number removed."""
        if source not in self._adj:
            return 0
        before = len(self._adj[source])
        self._adj[source] = [e for e in self._adj[source] if e.dest != dest]
        return before - len(self._adj[source])

    # ----- station line information -----------------------------------------
    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return a copy of the lines serving a station (empty if unknown)."""
        return list(self.station_lines.get(station_name, []))
