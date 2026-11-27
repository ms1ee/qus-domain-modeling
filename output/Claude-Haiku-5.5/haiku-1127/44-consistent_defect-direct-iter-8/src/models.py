"""Graph data structures used to model the subway network.

The network is a weighted *directed* graph: every ``Edge`` can only be
traversed from its ``source`` station to its ``dest`` station. Station numbers
(vertices) are assigned by the caller, the graph only stores them.
"""


class Edge:
    """A directed, weighted connection between two stations.

    Attributes:
        source: Station number the edge starts from.
        dest: Station number the edge leads to.
        distance: Distance in meters (also used as the edge weight).
        line: Name of the subway line the connection belongs to.
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

    def __repr__(self) -> str:
        return (f"Edge(source={self.source!r}, dest={self.dest!r}, "
                f"distance={self.distance!r}, line={self.line!r})")


class Graph:
    """Weighted directed graph with adjacency lists.

    Attributes:
        station_lines: Mapping from station name to the list of line names
            serving that station (used for transfer detection and reports).
    """

    def __init__(self):
        self._adjacency = {}  # station number -> list[Edge]
        self.station_lines = {}  # station name -> list[str]

    def add_vertex(self, vertex):
        """Register a station number as a vertex (no-op if already present)."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex) -> bool:
        """Return True if the station number is part of the graph."""
        return vertex in self._adjacency

    def vertices(self) -> list:
        """Return all station numbers in insertion order."""
        return list(self._adjacency.keys())

    def vertex_count(self) -> int:
        """Return the number of vertices."""
        return len(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Store the lines serving a station (by name)."""
        self.station_lines[station_name] = list(lines)

    def lines_of(self, station_name) -> list:
        """Return the lines serving a station name (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoints if necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)

    def adjacent(self, vertex) -> list:
        """Return the outgoing edges of a station number."""
        return self._adjacency.get(vertex, [])

    def edges(self):
        """Yield every edge in the graph."""
        for edge_list in self._adjacency.values():
            for edge in edge_list:
                yield edge

    def edge_count(self) -> int:
        """Return the total number of directed edges."""
        return sum(len(edge_list) for edge_list in self._adjacency.values())

    def has_edge(self, source, dest, line=None) -> bool:
        """Return True if a directed edge source->dest exists (optionally on a line)."""
        for edge in self.adjacent(source):
            if edge.dest == dest and (line is None or edge.line == line):
                return True
        return False
