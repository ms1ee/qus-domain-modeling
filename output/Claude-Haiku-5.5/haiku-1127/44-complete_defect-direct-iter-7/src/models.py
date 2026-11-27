"""Graph data structures for the subway network.

Station numbers (integers) are assigned by the caller (see subway_network.py).
The Graph stores an undirected weighted adjacency list.
"""


class Edge:
    """An undirected weighted edge between two stations.

    Attributes:
        source: station number of one endpoint
        dest:   station number of the other endpoint
        distance: physical distance in meters
        line:   name of the subway line the edge belongs to
    The ``weight`` attribute is an alias of ``distance``.
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
        """Weight used by shortest path algorithms (equal to distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph represented by adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names
    """

    def __init__(self):
        self._adj = {}
        self.station_lines = {}
        self._edge_count = 0

    def add_node(self, v):
        """Ensure that vertex ``v`` exists in the graph."""
        self._adj.setdefault(v, [])

    def has_node(self, v):
        """Return True if vertex ``v`` exists."""
        return v in self._adj

    def nodes(self):
        """Return a sorted list of all vertex numbers."""
        return sorted(self._adj)

    def set_station_lines(self, station_name, lines):
        """Record the (de-duplicated, ordered) lines serving a station."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def add_edge(self, edge):
        """Add an undirected edge; both endpoints are created if necessary."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self._adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].append(edge)
        self._edge_count += 1

    def adjacent(self, v):
        """Return a list of edges incident to vertex ``v``."""
        if v not in self._adj:
            raise KeyError(f"Unknown station number: {v}")
        return list(self._adj[v])

    def degree(self, v):
        """Return the number of edges incident to vertex ``v``."""
        return len(self.adjacent(v))

    def edges(self):
        """Return every distinct edge exactly once."""
        seen = set()
        result = []
        for incident in self._adj.values():
            for edge in incident:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def remove_edge(self, source, dest, line=None):
        """Remove edges between two vertices (optionally only on ``line``).

        Returns True if at least one edge was removed.
        """
        if source not in self._adj:
            return False
        to_remove = []
        for edge in self._adj[source]:
            same_pair = {edge.source, edge.dest} == {source, dest}
            if same_pair and (line is None or edge.line == line):
                to_remove.append(edge)
        if not to_remove:
            return False
        removed_ids = {id(edge) for edge in to_remove}
        for vertex in {source, dest}:
            if vertex in self._adj:
                self._adj[vertex] = [e for e in self._adj[vertex] if id(e) not in removed_ids]
        self._edge_count -= len(to_remove)
        return True

    def vertex_count(self):
        """Return the number of vertices."""
        return len(self._adj)

    def edge_count(self):
        """Return the number of edges."""
        return self._edge_count
