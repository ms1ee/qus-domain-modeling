"""
Graph data structures for subway network modeling.

``Graph`` is a weighted undirected graph stored as adjacency lists in the
``graph`` dictionary (station number -> list of outgoing ``Edge``).  Station
numbers are assigned by the caller.
"""


class Edge:
    """A weighted edge between two stations (by station number) on a line."""

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight equals the inter-station distance in meters."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def reversed(self):
        """Return a copy of this edge with swapped direction."""
        return Edge(self.dest, self.source, self.distance, self.line)

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.source, self.dest, self.distance, self.line) == (
            other.source, other.dest, other.distance, other.line)

    def __hash__(self):
        return hash((self.source, self.dest, self.distance, self.line))


class Graph:
    """Weighted undirected graph with adjacency lists."""

    def __init__(self):
        # station number -> list[Edge] (edges oriented away from the station)
        self.graph = {}
        # station name -> list of line names
        self.station_lines = {}
        self._edge_count = 0

    # ---- vertex management -------------------------------------------------
    def add_vertex(self, v):
        """Ensure that vertex ``v`` exists in the graph."""
        if v not in self.graph:
            self.graph[v] = []

    def has_vertex(self, v):
        return v in self.graph

    def vertices(self):
        return list(self.graph.keys())

    def num_vertices(self):
        return len(self.graph)

    def set_station_lines(self, station_name, lines):
        """Record the lines a station belongs to."""
        self.station_lines[station_name] = list(lines) if lines is not None else []

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(self.station_lines.get(station_name, [])) > 1

    # ---- edge management ---------------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge (stored in both directions)."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.source != edge.dest:
            self.graph[edge.dest].append(edge.reversed())
        self._edge_count += 1

    def remove_edge(self, source, dest, line=None):
        """Remove edges between source and dest (optionally only on ``line``).

        :return: number of undirected edges removed
        """
        removed = 0
        for a, b in ((source, dest), (dest, source)):
            if a not in self.graph:
                continue
            kept = []
            for e in self.graph[a]:
                if e.dest == b and (line is None or e.line == line):
                    if a == source:
                        removed += 1
                    continue
                kept.append(e)
            self.graph[a] = kept
        self._edge_count -= removed
        return removed

    def adj(self, v):
        """Return the edges incident to vertex ``v``."""
        return self.graph.get(v, [])

    def num_edges(self):
        return self._edge_count

    def edges(self):
        """Return each undirected edge once."""
        seen = set()
        result = []
        for v, lst in self.graph.items():
            for e in lst:
                key = (min(e.source, e.dest, key=str), max(e.source, e.dest, key=str), e.line, e.distance)
                if key in seen:
                    continue
                seen.add(key)
                result.append(e)
        return result

    def __repr__(self):
        return f"Graph(V={self.num_vertices()}, E={self.num_edges()})"
