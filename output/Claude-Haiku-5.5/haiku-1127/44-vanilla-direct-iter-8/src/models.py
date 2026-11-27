"""Graph data structures used to model the subway network.

The network is a weighted undirected graph. Vertices are station numbers
(assigned by the caller, typically SubwayNetwork in data_manager) and edges
carry the inter-station distance (in meters) and the line name.
"""


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Actual distance between the stations in meters.
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of {self!r}")

    def connects(self, a, b):
        """Return True if this edge joins station numbers ``a`` and ``b``."""
        return (self.source == a and self.dest == b) or (self.source == b and self.dest == a)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adj = {}
        self._edge_count = 0
        self.station_lines = {}

    # ----- vertices -------------------------------------------------------
    def add_vertex(self, vertex):
        """Add a vertex (station number) if it is not already present."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adj

    def vertices(self):
        """Return a list of all vertices."""
        return list(self._adj.keys())

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self._adj)

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) line affiliation of a station."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def get_station_lines(self, station_name):
        """Return a copy of the line list of a station (empty if unknown)."""
        return list(self.station_lines.get(station_name, []))

    # ----- edges ----------------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge, creating missing endpoints.

        Raises:
            ValueError: If the edge is a self-loop.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loops are not allowed in the subway network")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edge_count += 1

    def adj(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self._adj.get(vertex, [])

    def degree(self, vertex):
        """Return the number of edges incident to ``vertex``."""
        return len(self.adj(vertex))

    def edge_count(self):
        """Return the number of distinct edges."""
        return self._edge_count

    def edges(self):
        """Return every distinct edge exactly once."""
        result = []
        seen = set()
        for edge_list in self._adj.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def remove_edges(self, a, b, line=None):
        """Remove edges between stations ``a`` and ``b`` (optionally on one line).

        Returns:
            int: Number of removed edges.
        """
        def matches(edge):
            return edge.connects(a, b) and (line is None or edge.line == line)

        if a not in self._adj or b not in self._adj:
            return 0
        removed = sum(1 for edge in self._adj[a] if matches(edge))
        self._adj[a] = [edge for edge in self._adj[a] if not matches(edge)]
        self._adj[b] = [edge for edge in self._adj[b] if not matches(edge)]
        self._edge_count -= removed
        return removed
