"""Graph data structures used to model the subway network.

The network is a weighted undirected graph. Station numbers (vertices) are
assigned by the caller; Graph only stores the mapping that the caller registers.
"""


class Edge:
    """A weighted, undirected connection between two stations.

    Attributes:
        source: station number of one endpoint.
        dest: station number of the other endpoint.
        distance: physical distance between the stations, in meters.
        line: name of the subway line that operates this connection.
        weight: edge weight used by path algorithms (equal to distance).
    """

    __slots__ = ("source", "dest", "_distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self._distance = None
        self.distance = distance
        self.line = line

    @property
    def distance(self):
        """Distance between the two stations in meters."""
        return self._distance

    @distance.setter
    def distance(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("distance must be a number of meters")
        if value <= 0:
            raise ValueError("distance must be positive")
        self._distance = value

    @property
    def weight(self):
        """Edge weight used by shortest path computation (= distance in meters)."""
        return self._distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``."""
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return (
            f"Edge({self.source!r}, {self.dest!r}, "
            f"distance={self._distance!r}, line={self.line!r})"
        )


class Graph:
    """Weighted undirected graph of subway stations.

    Besides the adjacency structure, the graph keeps the station name <-> number
    mappings and the set of lines each station belongs to.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
    """

    def __init__(self):
        self._adjacency = {}  # station number -> list of incident Edge objects
        self._edges = []
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}

    # ----- vertex management ------------------------------------------------

    def register_station(self, station_name, number):
        """Register a station name under a caller-assigned station number."""
        existing = self.station_to_number.get(station_name)
        if existing is not None and existing != number:
            raise ValueError(f"station '{station_name}' already has number {existing}")
        owner = self.number_to_station.get(number)
        if owner is not None and owner != station_name:
            raise ValueError(f"number {number} is already used by '{owner}'")
        self.station_to_number[station_name] = number
        self.number_to_station[number] = station_name
        self._adjacency.setdefault(number, [])
        self.station_lines.setdefault(station_name, [])

    def set_station_lines(self, station_name, lines):
        """Set the list of lines that serve a station."""
        self.station_lines[station_name] = list(lines)

    def get_station_lines(self, station_name):
        """Return the lines serving a station (empty list if unknown)."""
        return list(self.station_lines.get(station_name, []))

    def has_vertex(self, number):
        """True if a station number is registered in the graph."""
        return number in self._adjacency

    def vertices(self):
        """Sorted list of all station numbers."""
        return sorted(self._adjacency)

    @property
    def num_vertices(self):
        return len(self._adjacency)

    # ----- edge management --------------------------------------------------

    def add_edge(self, edge):
        """Add an undirected edge between two registered stations."""
        if not self.has_vertex(edge.source) or not self.has_vertex(edge.dest):
            raise ValueError("both endpoints of an edge must be registered stations")
        if edge.source == edge.dest:
            raise ValueError("self-loops are not allowed in the subway network")
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, number):
        """Return the list of edges incident to a station number."""
        return self._adjacency.get(number, [])

    def edges(self):
        """Return a copy of the list of all edges."""
        return list(self._edges)

    @property
    def num_edges(self):
        return len(self._edges)

    def find_edge(self, a, b, line=None):
        """Return the first edge between stations a and b (optionally on a line)."""
        for edge in self.adjacent(a):
            if edge.other(a) == b and (line is None or edge.line == line):
                return edge
        return None
