"""Graph data models for the Beijing Subway network.

The network is a weighted undirected graph. Station names are mapped to
integer station numbers by ``SubwayNetwork``; the ``Graph`` itself works only
with station numbers, as required by the interface.
"""


class Edge:
    """An undirected weighted edge between two station numbers.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
        weight: Alias of ``distance`` used as the graph weight.
    """

    __slots__ = ("source", "dest", "_distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self._distance = self._validate_distance(distance)
        self.line = line

    @staticmethod
    def _validate_distance(distance):
        """Ensure the distance is a non-negative number."""
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise TypeError("distance must be a number of meters")
        if distance < 0:
            raise ValueError("distance must be non-negative")
        return distance

    @property
    def distance(self):
        """Distance between the endpoints in meters."""
        return self._distance

    @distance.setter
    def distance(self, value):
        self._distance = self._validate_distance(value)

    @property
    def weight(self):
        """Graph weight of the edge (equal to the distance in meters)."""
        return self._distance

    @weight.setter
    def weight(self, value):
        self._distance = self._validate_distance(value)

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of this edge")

    def __repr__(self):
        return (f"Edge({self.source}, {self.dest}, distance={self._distance}, "
                f"line={self.line!r})")


class Graph:
    """Weighted undirected graph with adjacency lists.

    Station numbers are assigned by the caller. The graph also keeps a
    ``station_lines`` mapping from station name to the lines serving it, which
    is used to identify transfer stations.
    """

    def __init__(self):
        self._adj = {}          # station number -> list[Edge]
        self._edges = []        # all edges, in insertion order
        self.station_lines = {}  # station name -> list[str]

    # ----- station metadata ---------------------------------------------

    def set_station_lines(self, station_name, lines):
        """Record the subway lines serving a station."""
        self.station_lines[station_name] = list(lines)

    # ----- vertices and edges -------------------------------------------

    def add_vertex(self, v):
        """Add a station number to the graph if it is not already present."""
        self._adj.setdefault(v, [])

    def has_vertex(self, v):
        """Return True if the station number is part of the graph."""
        return v in self._adj

    def add_edge(self, edge):
        """Add an undirected edge, creating its endpoints if necessary."""
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adj[edge.source].append(edge)
        self._adj[edge.dest].append(edge)
        self._edges.append(edge)

    def adj(self, v):
        """Return a copy of the list of edges incident to station ``v``."""
        return list(self._adj.get(v, []))

    def vertices(self):
        """Return the list of station numbers in the graph."""
        return list(self._adj.keys())

    def edges(self):
        """Return the list of all edges."""
        return list(self._edges)

    def num_vertices(self):
        """Return the number of stations in the graph."""
        return len(self._adj)

    def num_edges(self):
        """Return the number of edges in the graph."""
        return len(self._edges)

    def find_edge(self, u, v, line=None):
        """Find an edge between ``u`` and ``v`` (optionally on a given line).

        Returns:
            Edge or None: The first matching edge, or None if none exists.
        """
        for edge in self._adj.get(u, []):
            if edge.other(u) == v and (line is None or edge.line == line):
                return edge
        return None

    def remove_edge(self, u, v, line=None):
        """Remove the first edge between ``u`` and ``v`` matching ``line``.

        Returns:
            bool: True if an edge was removed, False otherwise.
        """
        edge = self.find_edge(u, v, line)
        if edge is None:
            return False
        self._adj[edge.source].remove(edge)
        if edge.dest != edge.source:
            self._adj[edge.dest].remove(edge)
        self._edges.remove(edge)
        return True


class SubwayNetwork:
    """Subway network combining the graph with name/number mappings.

    Attributes:
        graph: The ``Graph`` holding the station connections.
        station_to_number: Mapping from station name to station number.
        number_to_station: Mapping from station number to station name.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}

    def add_station(self, name, lines=()):
        """Add a station if needed and merge the given lines into it.

        Returns:
            int: The station number of the (new or existing) station.
        """
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
        current = self.graph.station_lines[name]
        for line in lines:
            if line not in current:
                current.append(line)
        return self.station_to_number[name]

    def has_station(self, name):
        """Return True if a station with this exact name exists."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for a station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def lines_of(self, name):
        """Return the lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def lines(self):
        """Return all subway line names in sorted order."""
        found = set()
        for line_list in self.graph.station_lines.values():
            found.update(line_list)
        return sorted(found)

    def is_transfer_station(self, name):
        """Return True if the station is served by more than one line."""
        return len(self.lines_of(name)) > 1

    def stations_on_line(self, line):
        """Return the names of stations served by ``line``, sorted by number."""
        result = []
        for number in sorted(self.number_to_station):
            name = self.number_to_station[number]
            if line in self.graph.station_lines.get(name, []):
                result.append(name)
        return result


def build_network(data):
    """Build a ``SubwayNetwork`` from the parsed subway dataset.

    Stations are numbered in the order of first appearance. Duplicate
    connections between the same stations on the same line (for example the
    two directions of one track segment) are merged into a single undirected
    edge.

    Args:
        data: dict with ``stations`` and ``connections`` lists.

    Returns:
        SubwayNetwork: The constructed network.
    """
    network = SubwayNetwork()
    for station in data.get("stations", []):
        network.add_station(station["name"], station.get("lines", []))

    for conn in data.get("connections", []):
        line = conn["line"]
        src = network.add_station(conn["source"], [line])
        dst = network.add_station(conn["dest"], [line])
        if network.graph.find_edge(src, dst, line) is None:
            network.graph.add_edge(Edge(src, dst, conn["distance"], line))
    return network
