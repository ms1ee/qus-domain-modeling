"""Graph data structures used to model the subway network.

The network is a weighted undirected graph. Vertices are station numbers
(assigned by the caller, e.g. via a ``station_to_number`` dictionary) and
edges carry the inter-station distance in meters and the line name.
"""


class Edge:
    """A weighted undirected edge between two stations on a given line."""

    def __init__(self, source, dest, distance, line):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError(f"Edge distance must be numeric, got {distance!r}")
        if distance < 0:
            raise ValueError(f"Edge distance must be non-negative, got {distance}")
        self.source = source
        self.dest = dest
        self.distance = distance
        self.weight = distance
        self.line = line

    def either(self):
        """Return one endpoint of the edge."""
        return self.source

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex!r} is not an endpoint of {self!r}")

    def set_distance(self, distance):
        """Update the edge distance (keeps ``weight`` in sync)."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError(f"Edge distance must be numeric, got {distance!r}")
        if distance < 0:
            raise ValueError("Edge distance must be non-negative")
        self.distance = distance
        self.weight = distance

    def __repr__(self):
        return (
            f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"
        )


class Graph:
    """Weighted undirected graph with adjacency lists.

    ``graph`` maps a station number to the list of incident edges.
    ``station_lines`` maps a station name to the list of lines it belongs to.
    """

    def __init__(self):
        self.graph = {}
        self.station_lines = {}
        self._edge_count = 0

    @property
    def adj(self):
        return self.graph

    def add_vertex(self, vertex):
        """Ensure ``vertex`` exists in the graph."""
        if vertex not in self.graph:
            self.graph[vertex] = []

    def add_edge(self, edge):
        """Add an undirected edge."""
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self.graph[edge.source].append(edge)
        if edge.dest != edge.source:
            self.graph[edge.dest].append(edge)
        self._edge_count += 1

    def remove_edge(self, source, dest, line=None):
        """Remove edges between source and dest (optionally on a given line).

        :return: number of edges removed.
        """
        removed = []
        for edge in list(self.graph.get(source, [])):
            if {edge.source, edge.dest} == {source, dest} and (
                line is None or edge.line == line
            ):
                removed.append(edge)
        for edge in removed:
            for vertex in {edge.source, edge.dest}:
                if edge in self.graph.get(vertex, []):
                    self.graph[vertex].remove(edge)
            self._edge_count -= 1
        return len(removed)

    def adjacent(self, vertex):
        """Return the edges incident to ``vertex``."""
        return self.graph.get(vertex, [])

    def vertices(self):
        return list(self.graph.keys())

    def edges(self):
        """Return each edge exactly once."""
        seen = set()
        result = []
        for edge_list in self.graph.values():
            for edge in edge_list:
                if id(edge) not in seen:
                    seen.add(id(edge))
                    result.append(edge)
        return result

    def V(self):
        return len(self.graph)

    def E(self):
        return self._edge_count

    def set_station_lines(self, station_name, lines):
        """Record the lines that a station belongs to."""
        self.station_lines[station_name] = list(lines) if lines else []

    def get_station_lines(self, station_name):
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return len(set(self.station_lines.get(station_name, []))) > 1

    def __repr__(self):
        return f"Graph(V={self.V()}, E={self.E()})"
