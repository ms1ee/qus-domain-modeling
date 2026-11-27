"""Graph data structures and subway network modeling.

The subway network is a weighted directed graph. Every station is a vertex
identified by an integer station number assigned by ``SubwayNetwork``; every
listed connection is an ``Edge`` that can only be traversed in its listed
direction.
"""


class Edge:
    """A directed, weighted connection between two station numbers.

    Attributes:
        source: Station number of the origin vertex.
        dest: Station number of the destination vertex.
        distance: Actual distance between the stations in meters.
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
        """Base weight of the edge (the distance in meters)."""
        return self.distance

    def __repr__(self):
        return (f"Edge({self.source!r} -> {self.dest!r}, "
                f"{self.distance} m, {self.line!r})")


class Graph:
    """Weighted directed graph with adjacency lists.

    Station numbers are assigned by the caller. The graph also keeps a
    ``station_lines`` mapping from station name to the lines serving it.
    """

    def __init__(self):
        self._adjacency = {}
        self._edge_count = 0
        self.station_lines = {}

    # ----- vertices -----------------------------------------------------

    def add_vertex(self, vertex):
        """Register a vertex (station number) if it is not present yet."""
        self._adjacency.setdefault(vertex, [])

    def has_vertex(self, vertex):
        """Return True if the vertex exists in the graph."""
        return vertex in self._adjacency

    def vertices(self):
        """Return the list of all vertex numbers."""
        return list(self._adjacency)

    def num_vertices(self):
        """Return the number of vertices."""
        return len(self._adjacency)

    def set_station_lines(self, station_name, lines):
        """Record the lines serving a station, removing duplicates in order.

        Args:
            station_name: Official station name.
            lines: Iterable of line names.
        """
        self.station_lines[station_name] = list(dict.fromkeys(lines))

    # ----- edges --------------------------------------------------------

    def add_edge(self, edge):
        """Add a directed edge, creating its endpoints if necessary.

        Raises:
            TypeError: If ``edge`` is not an ``Edge``.
            ValueError: If the distance is negative.
        """
        if not isinstance(edge, Edge):
            raise TypeError("add_edge expects an Edge instance")
        if edge.distance < 0:
            raise ValueError("edge distance must not be negative")
        self.add_vertex(edge.source)
        self.add_vertex(edge.dest)
        self._adjacency[edge.source].append(edge)
        self._edge_count += 1

    def adj(self, vertex):
        """Return the outgoing edges of a vertex (empty list if unknown)."""
        return self._adjacency.get(vertex, [])

    def edges(self):
        """Yield every edge in the graph."""
        for outgoing in self._adjacency.values():
            yield from outgoing

    def num_edges(self):
        """Return the number of directed edges."""
        return self._edge_count

    def update_edge_distance(self, source, dest, distance, line=None):
        """Update the distance of matching edges.

        Returns:
            int: Number of edges updated.
        """
        if distance <= 0:
            raise ValueError("distance must be positive")
        updated = 0
        for edge in self.adj(source):
            if edge.dest == dest and (line is None or edge.line == line):
                edge.distance = distance
                updated += 1
        return updated

    def remove_edges(self, source, dest, line=None):
        """Remove matching edges from the graph.

        Returns:
            int: Number of edges removed.
        """
        if source not in self._adjacency:
            return 0
        kept = []
        removed = 0
        for edge in self._adjacency[source]:
            if edge.dest == dest and (line is None or edge.line == line):
                removed += 1
            else:
                kept.append(edge)
        self._adjacency[source] = kept
        self._edge_count -= removed
        return removed


def _clean_name(value):
    """Normalize a station or line name by collapsing whitespace."""
    if not isinstance(value, str):
        raise ValueError(f"name must be a string, got {value!r}")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("name must not be empty")
    return cleaned


class SubwayNetwork:
    """Subway network built from the dataset dictionary.

    Attributes:
        graph: The ``Graph`` holding stations and directed connections.
        station_to_number: Mapping from station name to station number.
        number_to_station: List mapping station number to station name.
        line_stations: Mapping from line name to the stations it serves,
            in the order they were first encountered in the connections.
    """

    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = []
        self.line_stations = {}
        self._build(data)

    # ----- construction -------------------------------------------------

    def _assign_number(self, name):
        """Return the number of a station, assigning a new one if needed."""
        if name not in self.station_to_number:
            number = len(self.number_to_station)
            self.station_to_number[name] = number
            self.number_to_station.append(name)
            self.graph.add_vertex(number)
        return self.station_to_number[name]

    def _register_station_lines(self, name, lines):
        """Merge lines into the station's recorded line list."""
        current = list(self.graph.station_lines.get(name, []))
        for line in lines:
            if line not in current:
                current.append(line)
        self.graph.set_station_lines(name, current)

    def _build(self, data):
        for station in data.get("stations", []):
            name = _clean_name(station.get("name"))
            self._assign_number(name)
            lines = [str(line).strip() for line in station.get("lines", [])]
            self._register_station_lines(name, lines)

        for conn in data.get("connections", []):
            source = _clean_name(conn.get("source"))
            dest = _clean_name(conn.get("dest"))
            distance = int(conn.get("distance"))
            line = _clean_name(conn.get("line"))
            source_no = self._assign_number(source)
            dest_no = self._assign_number(dest)
            self.graph.add_edge(Edge(source_no, dest_no, distance, line))
            self._register_station_lines(source, [line])
            self._register_station_lines(dest, [line])
            stations = self.line_stations.setdefault(line, [])
            for name in (source, dest):
                if name not in stations:
                    stations.append(name)

    # ----- queries ------------------------------------------------------

    def number(self, name):
        """Return the station number for a station name.

        Raises:
            KeyError: If the station is unknown.
        """
        return self.station_to_number[_clean_name(name)]

    def name_of(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def has_station(self, name):
        """Return True if the station exists in the network."""
        return _clean_name(name) in self.station_to_number

    def stations(self):
        """Return all station names in numbering order."""
        return list(self.number_to_station)

    def lines_of(self, name):
        """Return the lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def transfer_stations(self):
        """Return a mapping of interchange stations to their lines."""
        return {name: list(lines)
                for name, lines in self.graph.station_lines.items()
                if len(lines) > 1}

    def all_lines(self):
        """Return the sorted list of all line names in the network."""
        return sorted(self.line_stations)


def build_network(data):
    """Build a ``SubwayNetwork`` from the raw dataset dictionary."""
    return SubwayNetwork(data)
