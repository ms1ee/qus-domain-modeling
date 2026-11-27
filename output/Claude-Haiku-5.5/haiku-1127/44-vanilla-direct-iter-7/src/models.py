"""Graph data structures used to model the subway network.

Stations are identified by integer numbers assigned by the caller
(see ``subway_network.SubwayNetwork``). The graph is undirected: adding an
edge stores one oriented copy per direction so that path searches can walk
the edges in either direction.
"""


class Edge:
    """A weighted connection between two stations on a subway line.

    Attributes:
        source: Station number at the start of the edge.
        dest: Station number at the end of the edge.
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
        """Edge weight used by shortest-path search (equal to the distance)."""
        return self.distance

    def reversed(self):
        """Return a new edge pointing in the opposite direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adj = {}
        self.station_lines = {}

    def add_vertex(self, v):
        """Add a vertex (station number) if it is not already present."""
        self._adj.setdefault(v, [])

    def vertices(self):
        """Return a list of all vertices (station numbers)."""
        return list(self._adj.keys())

    def adj(self, v):
        """Return the list of outgoing edges of vertex ``v``."""
        return self._adj.get(v, [])

    def set_station_lines(self, station_name, lines):
        """Set the line affiliation of a station, removing duplicates."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions).

        Args:
            edge: An ``Edge`` whose source and dest are station numbers.

        Raises:
            ValueError: If the edge connects a station to itself.
        """
        if edge.source == edge.dest:
            raise ValueError("self-loops are not allowed in the subway graph")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge.reversed())

    def edges_between(self, a, b):
        """Return all edges oriented from ``a`` to ``b``."""
        return [edge for edge in self.adj(a) if edge.dest == b]

    def remove_edges_between(self, a, b):
        """Remove every edge between vertices ``a`` and ``b`` in both directions.

        Returns:
            int: Number of undirected edges removed.
        """
        removed = len(self.edges_between(a, b))
        if a in self._adj:
            self._adj[a] = [edge for edge in self._adj[a] if edge.dest != b]
        if b in self._adj:
            self._adj[b] = [edge for edge in self._adj[b] if edge.dest != a]
        return removed

    def edge_count(self):
        """Return the number of undirected edges in the graph."""
        return sum(len(edges) for edges in self._adj.values()) // 2

    def __len__(self):
        return len(self._adj)

    def __contains__(self, v):
        return v in self._adj
