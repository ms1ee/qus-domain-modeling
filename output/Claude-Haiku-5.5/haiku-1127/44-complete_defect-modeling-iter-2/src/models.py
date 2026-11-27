"""
Core graph data model for the subway network.

Stations are identified by integer numbers assigned by the caller
(see ``network_builder.build_graph``); the ``Graph`` keeps the mapping
between station names and numbers, the lines serving each station, and
an undirected adjacency list of ``Edge`` objects.
"""


class Edge:
    """
    An undirected, weighted connection between two adjacent stations.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance between the stations in meters.
        line: Name of the subway line operating this connection.
    """

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = distance
        self.line = line

    @property
    def weight(self):
        """Edge weight used by path algorithms (equal to the distance in meters)."""
        return self.distance

    def other_end(self, node):
        """
        Return the endpoint opposite to ``node``.

        Raises:
            ValueError: If ``node`` is not an endpoint of this edge.
        """
        if node == self.source:
            return self.dest
        if node == self.dest:
            return self.source
        raise ValueError(f"node {node} is not an endpoint of edge {self!r}")

    def __repr__(self):
        return f"Edge({self.source!r}, {self.dest!r}, {self.distance!r}, {self.line!r})"


class Graph:
    """
    Weighted undirected graph of subway stations.

    Attributes:
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        station_lines: dict mapping station name -> list of line names.
        adjacency: dict mapping station number -> list of incident ``Edge``.
    """

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}
        self.adjacency = {}
        self._edges = []

    # ----------------------------------------------------------- stations
    def add_station(self, station_name, number):
        """
        Register a station under a caller-assigned number.

        Re-registering the same name with the same number is a no-op.

        Raises:
            TypeError: If ``number`` is not an integer.
            ValueError: If the name or number is already bound to a different station.
        """
        if not isinstance(number, int) or isinstance(number, bool):
            raise TypeError("station number must be an integer")

        if station_name in self.station_to_number:
            if self.station_to_number[station_name] != number:
                raise ValueError(f"station '{station_name}' is already registered with another number")
            return

        if number in self.number_to_station:
            raise ValueError(f"station number {number} is already used by '{self.number_to_station[number]}'")

        self.station_to_number[station_name] = number
        self.number_to_station[number] = station_name
        self.adjacency.setdefault(number, [])
        self.station_lines.setdefault(station_name, [])

    def set_station_lines(self, station_name, lines):
        """Set the (de-duplicated, order-preserving) list of lines serving a station."""
        self.station_lines[station_name] = list(dict.fromkeys(str(line) for line in lines))

    def has_station(self, station_name):
        """Return True if a station with this name is registered."""
        return station_name in self.station_to_number

    def get_number(self, station_name):
        """Return the number of a station by name."""
        return self.station_to_number[station_name]

    def get_name(self, number):
        """Return the name of a station by number."""
        return self.number_to_station[number]

    def lines_of(self, station_name):
        """Return a copy of the list of lines serving the station."""
        return list(self.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        """A station served by two or more lines is a transfer (interchange) station."""
        return len(self.lines_of(station_name)) >= 2

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number)

    def all_lines(self):
        """Return all distinct line names in the network, sorted."""
        lines = set()
        for line_list in self.station_lines.values():
            lines.update(line_list)
        return sorted(lines)

    def station_count(self):
        """Return the number of registered stations."""
        return len(self.station_to_number)

    # -------------------------------------------------------------- edges
    def add_edge(self, edge):
        """
        Add an undirected edge. Both endpoint numbers must be registered.

        Raises:
            KeyError: If an endpoint station number is unknown.
        """
        for number in (edge.source, edge.dest):
            if number not in self.adjacency:
                raise KeyError(f"station number {number} is not registered in the graph")

        self.adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self.adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def neighbors(self, number):
        """Return the list of edges incident to the station with this number."""
        return self.adjacency.get(number, [])

    def edges(self):
        """Return a copy of the list of all unique edges."""
        return list(self._edges)

    def edge_count(self):
        """Return the number of unique edges."""
        return len(self._edges)
