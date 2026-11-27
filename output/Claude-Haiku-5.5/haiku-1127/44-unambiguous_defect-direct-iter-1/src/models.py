"""Core graph data structures for the subway network.

Stations are represented by integer numbers inside the graph. The mapping between
station names and numbers is maintained by the caller (see subway_network.py).
"""


class Edge:
    """An undirected, weighted connection between two stations on a given line.

    Attributes:
        source: number of the first station.
        dest: number of the second station.
        weight: distance in meters (same as `distance`).
        line: name of the subway line operating this connection.
    """

    def __init__(self, source, dest, distance, line):
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.source = source
        self.dest = dest
        self.weight = distance
        self.line = line

    @property
    def distance(self):
        """Distance in meters (alias of weight)."""
        return self.weight

    @distance.setter
    def distance(self, value):
        if value < 0:
            raise ValueError("Edge distance must be non-negative")
        self.weight = value

    def other(self, vertex):
        """Return the endpoint of this edge opposite to `vertex`."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.weight!r}, {self.line!r})"


class Graph:
    """Weighted undirected graph stored as adjacency lists.

    Vertices are station numbers. `station_lines` maps station names to the list of
    lines serving that station (used for transfer-station detection and reporting).
    """

    def __init__(self):
        self._adj = {}          # station number -> list[Edge]
        self._edges = []        # every edge exactly once
        self.station_lines = {}  # station name -> list[str]

    @property
    def graph(self):
        """Adjacency-list dictionary (station number -> list of Edge)."""
        return self._adj

    def add_vertex(self, vertex):
        """Ensure a vertex exists in the graph."""
        self._adj.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists."""
        return vertex in self._adj

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self._adj.keys())

    def neighbors(self, vertex):
        """Return the list of edges incident to `vertex` (empty if unknown)."""
        return self._adj.get(vertex, [])

    def add_edge(self, edge):
        """Add an undirected edge; both endpoints are registered as vertices."""
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def edges(self):
        """Return the list of all edges (each undirected edge appears once)."""
        return list(self._edges)

    def num_vertices(self):
        """Number of vertices."""
        return len(self._adj)

    def num_edges(self):
        """Number of undirected edges."""
        return len(self._edges)

    def set_station_lines(self, station_name, lines):
        """Set the lines serving a station, removing duplicates while keeping order."""
        self.station_lines[station_name] = list(dict.fromkeys(str(line) for line in lines))

    def get_station_lines(self, station_name):
        """Return the lines serving a station (copy; empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))
