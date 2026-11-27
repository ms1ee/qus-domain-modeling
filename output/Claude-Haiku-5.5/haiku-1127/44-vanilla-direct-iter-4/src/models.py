"""Graph data structures used to model the subway network.

The graph is a weighted undirected graph. Vertices are integer station numbers
that are assigned by the caller (see ``data_manager.SubwayNetwork``). Each edge
carries the physical distance in meters (``weight``) and the subway line it
belongs to.
"""


class Edge:
    """An undirected weighted edge between two stations on one subway line."""

    def __init__(self, source, dest, distance, line):
        """Create an edge.

        Args:
            source: Station number of one endpoint.
            dest: Station number of the other endpoint.
            distance: Track distance between the stations in meters.
            line: Name of the subway line the edge belongs to.
        """
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of {self!r}")

    def set_distance(self, distance):
        """Update the distance (and therefore the weight) of this edge."""
        self.distance = distance
        self.weight = distance

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.weight}, {self.line!r})"


class Graph:
    """Weighted undirected graph represented with adjacency lists.

    Station numbers are supplied by the caller. The graph also keeps a mapping
    from station names to the lines serving them (``station_lines``).
    """

    def __init__(self):
        self._adj = {}          # station number -> list of incident Edge objects
        self._edges = []        # every edge exactly once
        self.station_lines = {}  # station name -> list of line names

    # ------------------------------------------------------------------ vertices
    def add_vertex(self, v):
        """Ensure vertex ``v`` exists in the graph."""
        self._adj.setdefault(v, [])

    def has_vertex(self, v):
        """Return True if vertex ``v`` exists in the graph."""
        return v in self._adj

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self._adj.keys())

    @property
    def vertex_count(self):
        """Number of vertices in the graph."""
        return len(self._adj)

    @property
    def edge_count(self):
        """Number of undirected edges in the graph."""
        return len(self._edges)

    def set_station_lines(self, station_name, lines):
        """Record the lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    # --------------------------------------------------------------------- edges
    def add_edge(self, edge):
        """Add an undirected edge, creating its endpoints if needed."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent_edges(self, v):
        """Return the edges incident to ``v``.

        The returned list is the internal adjacency list and must not be mutated.
        """
        return self._adj.get(v, [])

    def edges(self):
        """Return a copy of the list of all edges (each listed once)."""
        return list(self._edges)

    def find_edges(self, a, b, line=None):
        """Return edges between ``a`` and ``b``, optionally restricted to ``line``."""
        if a not in self._adj:
            return []
        result = []
        for edge in self._adj[a]:
            if edge.other(a) == b and (line is None or edge.line == line):
                result.append(edge)
        return result

    def update_edge_distance(self, a, b, distance, line=None):
        """Update the distance of edges between ``a`` and ``b``.

        Args:
            a: First station number.
            b: Second station number.
            distance: New distance in meters.
            line: If given, only edges on this line are updated.

        Returns:
            int: Number of edges updated.
        """
        matches = self.find_edges(a, b, line)
        for edge in matches:
            edge.set_distance(distance)
        return len(matches)

    def degree(self, v):
        """Return the number of edges incident to ``v``."""
        return len(self._adj.get(v, []))

    # --------------------------------------------------------------- analysis
    def connected_components(self):
        """Return the number of connected components in the graph."""
        seen = set()
        count = 0
        for start in self._adj:
            if start in seen:
                continue
            count += 1
            seen.add(start)
            stack = [start]
            while stack:
                node = stack.pop()
                for edge in self._adj[node]:
                    nxt = edge.other(node)
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        return count
