"""Domain models for the Beijing Subway network: edges, graph and network.

Station numbers are integers assigned by ``SubwayNetwork`` (the caller of
``Graph``); ``Graph`` itself never invents numbers.
"""

from datetime import datetime


def _clean_text(value, field):
    """Normalize a text field: convert to str, collapse whitespace, reject empties."""
    if not isinstance(value, str):
        raise ValueError(f"field '{field}' must be a string, got {type(value).__name__}")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"field '{field}' must not be empty")
    return cleaned


class Edge:
    """An undirected, weighted connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters (also used as the weight).
        line: Name of the subway line this connection belongs to.
    """

    __slots__ = ("source", "dest", "distance", "line")

    def __init__(self, source, dest, distance, line):
        self.source = source
        self.dest = dest
        self.distance = float(distance)
        self.line = line

    @property
    def weight(self):
        """Edge weight used by shortest-path algorithms (equal to distance)."""
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
    """Weighted undirected graph with adjacency lists.

    Attributes:
        station_lines: dict mapping station name -> list of line names.
    """

    def __init__(self):
        self._adjacency = {}
        self._edges = []
        self.station_lines = {}

    @property
    def node_count(self):
        """Number of nodes (stations) in the graph."""
        return len(self._adjacency)

    @property
    def edge_count(self):
        """Number of unique undirected edges in the graph."""
        return len(self._edges)

    def add_node(self, number):
        """Register a station number as a node (no-op if already present)."""
        self._adjacency.setdefault(number, [])

    def has_node(self, number):
        """Return True if the station number is a node of the graph."""
        return number in self._adjacency

    def set_station_lines(self, station_name, lines):
        """Record the (de-duplicated, order-preserving) lines serving a station."""
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        self.station_lines[station_name] = unique

    def add_edge(self, edge):
        """Add an undirected edge.

        A duplicate (same endpoints and same line, in either direction) is
        ignored so that bidirectional listings in the data do not double count.

        Returns:
            bool: True if the edge was added, False if it was a duplicate.
        """
        self.add_node(edge.source)
        self.add_node(edge.dest)
        for existing in self._adjacency[edge.source]:
            if existing.line == edge.line and existing.other(edge.source) == edge.dest:
                return False
        self._adjacency[edge.source].append(edge)
        if edge.dest != edge.source:
            self._adjacency[edge.dest].append(edge)
        self._edges.append(edge)
        return True

    def neighbors(self, node):
        """Return the list of edges incident to ``node`` (empty if unknown)."""
        return self._adjacency.get(node, [])

    def nodes(self):
        """Return a list of all station numbers in the graph."""
        return list(self._adjacency)

    def edges(self):
        """Return a list of all unique edges in the graph."""
        return list(self._edges)


class SubwayNetwork:
    """The modeled Beijing Subway network built from the raw dataset.

    Attributes:
        source_file: Where the data was loaded from.
        loaded_at: Timestamp of construction.
        declared_stations: station name -> lines as declared in the "stations" list.
        connections: normalized list of connection dicts with keys
            source, dest, distance, line.
        station_lines: effective station name -> lines (declared + connection lines).
        station_to_number: station name -> station number.
        number_to_station: station number -> station name.
        lines: line name -> list of station names serving it.
        graph: the Graph built from the network.
    """

    def __init__(self, source_file="<memory>"):
        self.source_file = source_file
        self.loaded_at = datetime.now()
        self.declared_stations = {}
        self.connections = []
        self.station_lines = {}
        self.station_to_number = {}
        self.number_to_station = {}
        self.lines = {}
        self.graph = Graph()
        self._casefold_stations = {}
        self._casefold_lines = {}

    @classmethod
    def from_data(cls, data, source_file="<memory>"):
        """Build a network from the dataset dict.

        Args:
            data: dict with ``stations`` ([{name, lines}]) and
                ``connections`` ([{source, dest, distance, line}]).
            source_file: Label recorded as the data source.

        Raises:
            ValueError: If the data structure or any field is invalid.
        """
        if not isinstance(data, dict):
            raise ValueError("subway data must be a JSON object")
        stations_raw = data.get("stations")
        connections_raw = data.get("connections")
        if not isinstance(stations_raw, list):
            raise ValueError("subway data must contain a 'stations' list")
        if not isinstance(connections_raw, list):
            raise ValueError("subway data must contain a 'connections' list")

        network = cls(source_file)
        for item in stations_raw:
            if not isinstance(item, dict) or "name" not in item:
                raise ValueError("each station entry must be an object with a 'name'")
            name = _clean_text(item["name"], "station name")
            raw_lines = item.get("lines", [])
            if not isinstance(raw_lines, list):
                raise ValueError(f"'lines' of station '{name}' must be a list")
            bucket = network.declared_stations.setdefault(name, [])
            for raw in raw_lines:
                line = _clean_text(raw, "line name")
                if line not in bucket:
                    bucket.append(line)

        for item in connections_raw:
            if not isinstance(item, dict):
                raise ValueError("each connection entry must be an object")
            for key in ("source", "dest", "distance", "line"):
                if key not in item:
                    raise ValueError(f"connection entry is missing field '{key}'")
            distance = item["distance"]
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                raise ValueError("connection 'distance' must be a number of meters")
            network.connections.append({
                "source": _clean_text(item["source"], "source"),
                "dest": _clean_text(item["dest"], "dest"),
                "distance": distance,
                "line": _clean_text(item["line"], "line"),
            })

        network._build()
        return network

    def _build(self):
        """Merge declared and connection data, number stations and build the graph."""
        self.station_lines = {name: list(lines) for name, lines in self.declared_stations.items()}
        for conn in self.connections:
            for end in (conn["source"], conn["dest"]):
                bucket = self.station_lines.setdefault(end, [])
                if conn["line"] not in bucket:
                    bucket.append(conn["line"])

        # Station numbers are assigned here (the caller), not by Graph.
        for number, name in enumerate(self.station_lines):
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_node(number)
            self.graph.set_station_lines(name, self.station_lines[name])

        for conn in self.connections:
            self.graph.add_edge(Edge(
                self.station_to_number[conn["source"]],
                self.station_to_number[conn["dest"]],
                conn["distance"],
                conn["line"],
            ))

        self.lines = {}
        for name, lines in self.station_lines.items():
            for line in lines:
                self.lines.setdefault(line, [])
                self.lines[line].append(name)

        self._casefold_stations = {name.casefold(): name for name in self.station_lines}
        self._casefold_lines = {line.casefold(): line for line in self.lines}

    # ----- lookup helpers -------------------------------------------------

    def has_station(self, name):
        """Return True if the exact station name exists."""
        return name in self.station_to_number

    def find_station(self, name):
        """Standardize a user-entered station name to the official name.

        Matching is whitespace-tolerant and case-insensitive; a trailing
        Chinese "站" suffix is tolerated.

        Returns:
            The canonical station name, or None if no station matches.
        """
        cleaned = " ".join(str(name).split())
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        key = cleaned.casefold()
        if key in self._casefold_stations:
            return self._casefold_stations[key]
        if cleaned.endswith("站") and len(cleaned) > 1:
            return self.find_station(cleaned[:-1])
        return None

    def find_line(self, name):
        """Standardize a user-entered line name; return canonical name or None."""
        cleaned = " ".join(str(name).split())
        if not cleaned:
            return None
        if cleaned in self.lines:
            return cleaned
        return self._casefold_lines.get(cleaned.casefold())

    def get_station_number(self, name):
        """Return the station number for an exact station name.

        Raises:
            KeyError: If the station does not exist.
        """
        return self.station_to_number[name]

    def get_station_name(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def lines_of_station(self, name):
        """Return the list of lines serving a station (empty if unknown)."""
        return list(self.station_lines.get(name, []))

    def station_names(self):
        """Return all station names sorted alphabetically."""
        return sorted(self.station_lines)

    def line_names(self):
        """Return all line names sorted alphabetically."""
        return sorted(self.lines)

    def transfer_stations(self):
        """Return names of stations served by more than one line."""
        return [name for name, lines in self.station_lines.items() if len(lines) > 1]
