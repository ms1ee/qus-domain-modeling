"""Graph data structures for the Beijing Subway network.

The network is a weighted undirected graph. Stations are identified by
integer numbers that are assigned by the caller (see ``data_manager``), and
each edge stores the subway line it belongs to.
"""


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    def other(self, node):
        """Return the endpoint opposite to ``node``.

        Raises:
            ValueError: If ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"node {node} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph of subway stations.

    Station numbers are assigned by the caller through ``register_station``.
    The graph keeps the mapping between station names and numbers, the lines
    serving each station, and adjacency lists of edges.
    """

    def __init__(self):
        self.station_to_number = {}
        self.station_lines = {}
        self._number_to_station = {}
        self._adjacency = {}
        self._edges = []

    # ----- station management -------------------------------------------
    def register_station(self, station_name, number):
        """Register a station name with its number (a graph node).

        Raises:
            ValueError: If the name or number is already registered.
        """
        if station_name in self.station_to_number:
            raise ValueError(f"station '{station_name}' is already registered")
        if number in self._adjacency:
            raise ValueError(f"station number {number} is already in use")
        self.station_to_number[station_name] = number
        self._number_to_station[number] = station_name
        self._adjacency[number] = []
        self.station_lines.setdefault(station_name, [])

    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station.

        Raises:
            KeyError: If the station is not registered.
        """
        if station_name not in self.station_to_number:
            raise KeyError(f"unknown station '{station_name}'")
        self.station_lines[station_name] = list(lines)

    def has_station(self, station_name):
        """Return True if the station name is registered."""
        return station_name in self.station_to_number

    def contains_number(self, number):
        """Return True if the station number is a node of this graph."""
        return number in self._adjacency

    def get_number(self, station_name):
        """Return the station number for a station name."""
        return self.station_to_number[station_name]

    def get_name(self, number):
        """Return the station name for a station number."""
        return self._number_to_station[number]

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def is_transfer_station(self, station_name):
        """Return True if more than one line serves the station."""
        return len(self.station_lines.get(station_name, [])) > 1

    # ----- edge management -----------------------------------------------
    def add_edge(self, edge):
        """Add an undirected edge to the graph.

        Raises:
            KeyError: If an endpoint is not a registered station number.
            ValueError: If the edge is a self-loop.
        """
        if edge.source not in self._adjacency or edge.dest not in self._adjacency:
            raise KeyError(f"edge endpoints {edge.source}, {edge.dest} are not registered")
        if edge.source == edge.dest:
            raise ValueError("self-loop edges are not allowed")
        self._adjacency[edge.source].append(edge)
        self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent(self, number):
        """Return the list of edges incident to a station number."""
        return self._adjacency.get(number, [])

    def neighbors(self, number):
        """Return the station numbers adjacent to a station number."""
        return [edge.other(number) for edge in self.adjacent(number)]

    def edges(self):
        """Return a copy of the list of all edges."""
        return list(self._edges)

    def find_edges(self, number_a, number_b):
        """Return all edges connecting two station numbers (any order)."""
        return [
            edge
            for edge in self.adjacent(number_a)
            if {edge.source, edge.dest} == {number_a, number_b}
        ]

    @property
    def node_count(self):
        """Number of stations (nodes) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of connections (edges) in the graph."""
        return len(self._edges)
