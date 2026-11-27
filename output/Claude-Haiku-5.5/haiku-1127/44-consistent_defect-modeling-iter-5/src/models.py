"""Graph data structures for the subway network.

The network is a weighted DIRECTED graph: every connection is usable only in its
listed direction. Station numbers are assigned by the caller (see data_manager).
"""


class Edge:
    """A directed connection between two stations.

    Attributes:
        source: Station number of the departure station.
        dest: Station number of the arrival station.
        distance: Physical distance in meters (used as the edge weight).
        line: Name of the subway line operating this connection.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to the distance in meters)."""
        return self.distance

    def __repr__(self):
        return f"Edge({self.source}->{self.dest}, {self.distance}m, {self.line!r})"


class Graph:
    """Weighted directed graph of subway stations.

    Attributes:
        station_to_number: dict mapping station name -> station number.
        number_to_station: dict mapping station number -> station name.
        station_lines: dict mapping station name -> list of line names serving it.
        adjacency: dict mapping station number -> list of outgoing Edge objects.
    """

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = {}
        self.station_lines = {}
        self.adjacency = {}

    # ----- station management -------------------------------------------------
    def add_station(self, name, number):
        """Register a station with an externally assigned number.

        Raises:
            ValueError: If the name or number is already registered to a different station.
        """
        existing = self.station_to_number.get(name)
        if existing is not None:
            if existing != number:
                raise ValueError(f"Station '{name}' already registered with number {existing}")
            return
        if number in self.number_to_station:
            raise ValueError(f"Station number {number} already used by '{self.number_to_station[number]}'")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.station_lines.setdefault(name, [])
        self.adjacency.setdefault(number, [])

    def set_station_lines(self, station_name, lines):
        """Set the list of lines serving a station."""
        self.station_lines[station_name] = list(lines)

    def number_of(self, name):
        """Return the station number for a station name (KeyError if unknown)."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name for a station number (KeyError if unknown)."""
        return self.number_to_station[number]

    def has_station(self, name):
        """Return True if the station name is registered."""
        return name in self.station_to_number

    def lines_of(self, name):
        """Return the list of lines serving the given station."""
        return list(self.station_lines.get(name, []))

    def is_transfer_station(self, name):
        """Return True if the station is served by more than one line."""
        return len(self.station_lines.get(name, [])) > 1

    # ----- connection management ----------------------------------------------
    def add_edge(self, edge):
        """Add a directed edge. Both endpoint numbers must already be registered."""
        if edge.source not in self.number_to_station or edge.dest not in self.number_to_station:
            raise ValueError(f"Edge endpoints must be registered stations: {edge}")
        self.adjacency.setdefault(edge.source, []).append(edge)
        self.adjacency.setdefault(edge.dest, [])

    def neighbors(self, number):
        """Return the outgoing edges of a station number."""
        return self.adjacency.get(number, [])

    def edges(self):
        """Iterate over all directed edges in the graph."""
        for edge_list in self.adjacency.values():
            for edge in edge_list:
                yield edge

    @property
    def vertex_count(self):
        """Number of stations in the graph."""
        return len(self.number_to_station)

    @property
    def edge_count(self):
        """Number of directed edges in the graph."""
        return sum(len(edge_list) for edge_list in self.adjacency.values())
