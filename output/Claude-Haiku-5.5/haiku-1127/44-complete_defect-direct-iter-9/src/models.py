"""Graph data structures and the subway network model.

Station numbers are assigned by the caller (here: SubwayNetwork), not by Graph.
"""


class NetworkBuildError(ValueError):
    """Raised when the raw dataset cannot be turned into a subway network."""


class Edge:
    """A weighted connection between two stations (identified by station numbers).

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters.
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
        """Edge weight used by shortest path search (equal to the distance in meters)."""
        return self.distance

    def other(self, vertex):
        """Return the endpoint opposite to ``vertex``.

        Args:
            vertex: One endpoint station number.

        Returns:
            int: The other endpoint station number.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"vertex {vertex} is not an endpoint of {self!r}")

    def __repr__(self):
        return f"Edge({self.source}, {self.dest}, {self.distance}, {self.line!r})"


class Graph:
    """Weighted undirected graph with adjacency lists.

    Vertices are station numbers. Each edge is stored in the adjacency list of
    both of its endpoints. The mapping ``station_lines`` maps station names to the
    list of lines that serve them.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    def add_vertex(self, vertex):
        """Add a vertex if it does not already exist."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station.

        Args:
            station_name: Official station name.
            lines: Iterable of line names.
        """
        self.station_lines[station_name] = list(lines)

    def add_edge(self, edge):
        """Add an undirected edge, creating missing endpoint vertices.

        Args:
            edge: An Edge instance whose endpoints are station numbers.

        Raises:
            TypeError: If ``edge`` is not an Edge.
        """
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)

    def adjacent_edges(self, vertex):
        """Return the edges incident to ``vertex``.

        The returned list is the internal adjacency list and must not be modified.

        Raises:
            KeyError: If the vertex does not exist.
        """
        return self._adjacency[vertex]

    def degree(self, vertex):
        """Return the number of edges incident to ``vertex``."""
        return len(self._adjacency[vertex])

    def vertices(self):
        """Return a list of all vertex numbers."""
        return list(self._adjacency.keys())

    def edges(self):
        """Return a list of all edges (each counted once)."""
        return list(self._edges)

    @property
    def num_vertices(self):
        """Number of vertices in the graph."""
        return len(self._adjacency)

    @property
    def num_edges(self):
        """Number of edges in the graph."""
        return len(self._edges)


class SubwayNetwork:
    """The Beijing Subway network: a graph plus station name/number mappings.

    Attributes:
        graph: The weighted undirected Graph.
        station_to_number: dict mapping station names to station numbers.
        number_to_name: dict mapping station numbers to station names.
        lines: Ordered list of all known line names.
        warnings: Non-fatal problems detected while building the network.
    """

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = {}
        self.lines = []
        self.warnings = []

    @property
    def station_lines(self):
        """dict mapping station names to lists of line names."""
        return self.graph.station_lines

    def _register_line(self, line):
        if line not in self.lines:
            self.lines.append(line)

    def add_station(self, name, lines=()):
        """Add a station if it is new and return its number.

        Args:
            name: Official station name.
            lines: Lines serving the station (used only when the station is new).

        Returns:
            int: The station number.
        """
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_name)
        self.station_to_number[name] = number
        self.number_to_name[number] = name
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, lines)
        for line in lines:
            self._register_line(line)
        return number

    def number_of(self, name):
        """Return the station number of a station name (KeyError if unknown)."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the station name of a station number (KeyError if unknown)."""
        return self.number_to_name[number]

    def station_names(self):
        """Return the sorted list of all station names."""
        return sorted(self.station_to_number)

    @classmethod
    def from_data(cls, data):
        """Build a network from the raw dataset dictionary.

        Args:
            data: dict with 'stations' ([{name, lines}]) and
                'connections' ([{source, dest, distance, line}]) lists.

        Returns:
            SubwayNetwork: The constructed network.

        Raises:
            NetworkBuildError: If the data is malformed.
        """
        if not isinstance(data, dict):
            raise NetworkBuildError("subway data must be a JSON object")
        stations = data.get("stations", [])
        connections = data.get("connections", [])
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise NetworkBuildError("'stations' and 'connections' must be lists")

        network = cls()
        for entry in stations:
            if not isinstance(entry, dict) or "name" not in entry:
                raise NetworkBuildError(f"invalid station entry: {entry!r}")
            name = str(entry["name"]).strip()
            if not name:
                raise NetworkBuildError("station name must not be empty")
            lines = [str(line) for line in entry.get("lines", [])]
            if name in network.station_to_number:
                network.warnings.append(f"station '{name}' is listed more than once; line lists merged")
                existing = network.graph.station_lines[name]
                for line in lines:
                    if line not in existing:
                        existing.append(line)
                    network._register_line(line)
            else:
                network.add_station(name, lines)

        for entry in connections:
            try:
                source = str(entry["source"]).strip()
                dest = str(entry["dest"]).strip()
                distance_raw = entry["distance"]
                line = str(entry["line"]).strip()
            except (KeyError, TypeError) as exc:
                raise NetworkBuildError(f"invalid connection entry: {entry!r}") from exc
            if isinstance(distance_raw, bool) or not isinstance(distance_raw, (int, float)) or distance_raw <= 0:
                raise NetworkBuildError(f"invalid distance in connection: {entry!r}")
            for name in (source, dest):
                if name not in network.station_to_number:
                    network.warnings.append(f"station '{name}' appears in connections but not in the station list")
                    network.add_station(name, [line])
            network._register_line(line)
            network.graph.add_edge(
                Edge(
                    network.station_to_number[source],
                    network.station_to_number[dest],
                    int(round(distance_raw)),
                    line,
                )
            )
        return network
