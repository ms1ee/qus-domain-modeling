"""Builds the weighted graph model of the subway network from the data dictionary.

Each unique station name receives one station number. Transfer stations are
represented by a single node whose incident edges belong to several lines; a line
change along a path is counted as a transfer.
"""

from models import Edge, Graph


def _clean_name(value):
    """Normalize a station or line name (strip and collapse whitespace)."""
    if not isinstance(value, str):
        raise ValueError(f"Expected a string name, got {type(value).__name__}")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Names must not be empty")
    return cleaned


class SubwayNetwork:
    """Container for the subway graph and name lookup tables.

    Attributes:
        station_to_number: dict station name -> station number
        number_to_station: list where index is station number and value is name
        graph: the Graph instance holding edges between station numbers
    """

    def __init__(self):
        self.station_to_number = {}
        self.number_to_station = []
        self.graph = Graph()
        self._casefold_index = {}
        self._lines = {}

    def _register_station(self, name):
        """Register a station name (if new) and return its number."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        number = len(self.number_to_station)
        self.station_to_number[name] = number
        self.number_to_station.append(name)
        self._casefold_index.setdefault(name.casefold(), name)
        self.graph.add_node(number)
        return number

    def number_of(self, name):
        """Return the station number of an official station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def has_station(self, name):
        """Return True if ``name`` is an official station name."""
        return name in self.station_to_number

    def standardize_station(self, raw):
        """Map user input to an official station name, or None if it does not exist.

        Whitespace is normalized and matching is case-insensitive.
        """
        if raw is None:
            return None
        normalized = " ".join(str(raw).split())
        if not normalized:
            return None
        if normalized in self.station_to_number:
            return normalized
        return self._casefold_index.get(normalized.casefold())

    def standardize_line(self, raw):
        """Map user input to an official line name, or None if it does not exist."""
        if raw is None:
            return None
        normalized = " ".join(str(raw).split())
        for line in self._lines:
            if line == normalized or line.casefold() == normalized.casefold():
                return line
        return None

    def station_names(self):
        """Return a sorted list of all official station names."""
        return sorted(self.station_to_number)

    def lines_of(self, name):
        """Return the lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def line_names(self):
        """Return a sorted list of all line names."""
        return sorted(self._lines)

    def stations_on_line(self, line):
        """Return the stations served by ``line`` in data order."""
        return list(self._lines.get(line, []))

    def is_transfer_station(self, name):
        """Return True if the station is served by two or more lines."""
        return len(self.lines_of(name)) >= 2

    def transfer_stations(self):
        """Return a sorted list of transfer station names."""
        return sorted(name for name in self.station_to_number if self.is_transfer_station(name))


def build_network(data):
    """Build a SubwayNetwork from the dict loaded from subway_data.json."""
    network = SubwayNetwork()
    station_lines = {}

    def add_station_lines(name, lines):
        bucket = station_lines.setdefault(name, [])
        for line in lines:
            if line not in bucket:
                bucket.append(line)

    # Declared stations first, so station numbers follow the data file order.
    for station in data.get("stations", []):
        name = _clean_name(station["name"])
        network._register_station(name)
        add_station_lines(name, [_clean_name(line) for line in station.get("lines", [])])

    # Connections: register any undeclared station and collect the line information.
    parsed_connections = []
    for conn in data.get("connections", []):
        source = _clean_name(conn["source"])
        dest = _clean_name(conn["dest"])
        line = _clean_name(conn["line"])
        distance = int(conn["distance"])
        for name in (source, dest):
            network._register_station(name)
            add_station_lines(name, [line])
        parsed_connections.append((source, dest, distance, line))

    # Finalize station-to-line information.
    for name in network.number_to_station:
        network.graph.set_station_lines(name, station_lines.get(name, []))
        for line in network.graph.station_lines[name]:
            network._lines.setdefault(line, []).append(name)

    # Build undirected weighted edges between station numbers.
    for source, dest, distance, line in parsed_connections:
        network.graph.add_edge(
            Edge(network.number_of(source), network.number_of(dest), distance, line)
        )

    return network
