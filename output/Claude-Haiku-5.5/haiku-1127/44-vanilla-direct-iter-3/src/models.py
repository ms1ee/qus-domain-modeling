"""Core graph data structures: Edge and Graph (weighted undirected graph)."""

from numbers import Number


class Edge:
    """A weighted, line-tagged connection between two stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: actual distance between the stations in meters.
        line: name of the subway line the connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, Number):
            raise TypeError("Edge distance must be a number")
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to the distance)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return (
            f"Edge(source={self.source}, dest={self.dest}, "
            f"distance={self.distance}, line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. The graph also keeps the
    mapping ``station_lines`` from station name to the list of lines it belongs to.
    Each undirected edge object is stored in the adjacency lists of both endpoints,
    so updating an edge object updates both directions at once.
    """

    def __init__(self):
        self.adj = {}  # station number -> list[Edge]
        self.station_lines = {}  # station name -> list[str]

    # ----- vertices -----
    def add_node(self, vertex):
        """Register a station number as a vertex (no-op if already present)."""
        self.adj.setdefault(vertex, [])

    def has_node(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self.adj

    def vertices(self):
        """Return the list of station numbers in the graph."""
        return list(self.adj.keys())

    def V(self):
        """Return the number of vertices."""
        return len(self.adj)

    # ----- edges -----
    def add_edge(self, edge):
        """Add an undirected edge to the graph."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adj[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adj[edge.dest].append(edge)

    def neighbors(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return self.adj.get(vertex, [])

    def edges(self):
        """Return every distinct edge object in the graph once."""
        seen = set()
        result = []
        for incident in self.adj.values():
            for edge in incident:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def E(self):
        """Return the number of distinct edges."""
        return len(self.edges())

    # ----- station line information -----
    def set_station_lines(self, station_name, lines):
        """Set the lines of a station (duplicates removed, order preserved)."""
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    def get_station_lines(self, station_name):
        """Return the lines of a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
