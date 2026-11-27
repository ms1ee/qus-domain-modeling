"""
Graph data structures for the subway network.

Stations are identified by integer numbers that are assigned by the caller
(see ``data_manager.DataManager``). The graph is a weighted undirected
multigraph: each edge carries the inter-station distance in meters and the
name of the line it belongs to.
"""


class Edge:
    """
    A connection between two stations on a single subway line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        weight: Edge weight, equal to the distance in meters.
        line: Name of the subway line this connection belongs to.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.weight = float(distance)
        self.line = line

    @property
    def distance(self):
        """Distance in meters (alias of ``weight``)."""
        return self.weight

    @distance.setter
    def distance(self, value):
        self.weight = float(value)

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")

    def connects(self, a, b):
        """Return True if this edge joins stations ``a`` and ``b`` (any order)."""
        return {self.source, self.dest} == {a, b}

    def __repr__(self):
        return (f"Edge({self.source}, {self.dest}, "
                f"{self.weight:.1f}m, line={self.line!r})")


class Graph:
    """
    Weighted undirected graph of subway stations.

    Attributes:
        adjacency_list: dict mapping station number -> list of incident Edge objects.
        station_lines: dict mapping station name -> list of line names it serves.
        edge_count: Number of edges added to the graph.
    """

    def __init__(self):
        self.adjacency_list = {}
        self.station_lines = {}
        self.edge_count = 0

    @property
    def node_count(self):
        """Number of stations (nodes) in the graph."""
        return len(self.adjacency_list)

    def add_node(self, vertex):
        """Ensure that ``vertex`` exists in the adjacency list."""
        self.adjacency_list.setdefault(vertex, [])

    def has_node(self, vertex):
        """Return True if ``vertex`` is a node of the graph."""
        return vertex in self.adjacency_list

    def set_station_lines(self, station_name, lines):
        """Record the lines served by a station (keyed by station name)."""
        self.station_lines[station_name] = list(lines) if lines else []

    def add_edge(self, edge):
        """Add an undirected edge to the graph."""
        self.add_node(edge.source)
        self.add_node(edge.dest)
        self.adjacency_list[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adjacency_list[edge.dest].append(edge)
        self.edge_count += 1

    def adjacent(self, vertex):
        """Return the list of edges incident to ``vertex``."""
        return list(self.adjacency_list.get(vertex, []))

    def find_edge(self, a, b, line=None):
        """
        Find an edge between stations ``a`` and ``b``.

        Args:
            a: First station number.
            b: Second station number.
            line: Optional line name to match.

        Returns:
            Edge or None if no matching edge exists.
        """
        for edge in self.adjacency_list.get(a, []):
            if edge.connects(a, b) and (line is None or edge.line == line):
                return edge
        return None

    def edges(self):
        """Return every distinct edge in the graph exactly once."""
        seen = set()
        result = []
        for edge_list in self.adjacency_list.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result
