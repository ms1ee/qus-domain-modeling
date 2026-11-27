"""Builds the weighted undirected subway graph from the dataset and offers
station-name lookup and standardization."""

import re

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


def normalize_name(text):
    """Return a comparison key: lower-case, without spaces, apostrophes, hyphens, dots."""
    return re.sub(r"[\s'\u2019\-_.]+", "", str(text).lower())


def build_graph(data):
    """Create a Graph from the dataset dictionary.

    Station numbers are assigned here (the Graph never assigns them). Stations
    referenced only by connections are registered as well. Each station's lines
    are the union of the lines declared for it and the lines of its connections.

    Raises:
        ValueError: If a station or connection entry is malformed.
    """
    graph = Graph()
    declared = {}

    for station in data.get("stations", []):
        if not isinstance(station, dict) or "name" not in station:
            raise ValueError(f"malformed station entry: {station!r}")
        name = str(station["name"]).strip()
        lines = [str(line) for line in station.get("lines", [])]
        declared[name] = list(dict.fromkeys(declared.get(name, []) + lines))

    connections = data.get("connections", [])
    for connection in connections:
        for key in ("source", "dest", "distance", "line"):
            if key not in connection:
                raise ValueError(f"connection missing field '{key}': {connection!r}")
        for endpoint in (connection["source"], connection["dest"]):
            declared.setdefault(str(endpoint).strip(), [])
        line = str(connection["line"])
        for endpoint in (connection["source"], connection["dest"]):
            name = str(endpoint).strip()
            if line not in declared[name]:
                declared[name].append(line)

    for number, name in enumerate(declared):
        graph.register_station(name, number)
        graph.set_station_lines(name, declared[name])

    for connection in connections:
        source = graph.number_of(str(connection["source"]).strip())
        dest = graph.number_of(str(connection["dest"]).strip())
        distance = float(connection["distance"])
        graph.add_edge(Edge(source, dest, distance, str(connection["line"])))
    return graph


class SubwayNetwork:
    """The loaded subway network: graph plus name lookup helpers.

    Attributes:
        data: The raw dataset dictionary.
        graph: The Graph built from the dataset.
        station_names: Official station names in graph order.
        line_names: Sorted list of all line names.
    """

    def __init__(self, data):
        self.data = data
        self.graph = build_graph(data)
        self.station_names = list(self.graph.station_to_number.keys())
        self._station_set = set(self.station_names)
        self._normalized = {}
        for name in self.station_names:
            self._normalized.setdefault(normalize_name(name), name)
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        self.line_names = sorted(lines)

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Load the dataset from ``path`` and build the network."""
        return cls(load_subway_data(path))

    def has_station(self, name):
        """Return True if ``name`` is an official station name."""
        return name in self._station_set

    def standardize_station_name(self, name):
        """Map user input to the official station name.

        Exact matches win; otherwise a match ignoring case, spacing and
        punctuation is used. Returns None if no station matches.
        """
        if name is None:
            return None
        stripped = " ".join(str(name).split())
        if stripped in self._station_set:
            return stripped
        return self._normalized.get(normalize_name(stripped))

    def station_lines(self, name):
        """Return the lines serving the station ``name``."""
        return self.graph.lines_of(name)
