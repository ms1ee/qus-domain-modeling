"""Subway network construction and station name resolution."""

import difflib
import re

from models import Edge, Graph

FUZZY_MATCH_CUTOFF = 0.6


class SubwayNetwork:
    """Subway network ready for path queries.

    Attributes:
        graph: The weighted directed ``Graph`` with station numbers as vertices.
        station_to_number: Official station name -> station number.
        number_to_station: Station number -> official station name.
        station_names: Sorted list of official station names.
    """

    def __init__(self, graph, station_to_number, number_to_station):
        self.graph = graph
        self.station_to_number = station_to_number
        self.number_to_station = number_to_station
        self.station_names = sorted(station_to_number.keys())
        self._normalized = {}
        for name in self.station_names:
            self._normalized.setdefault(_normalize(name), name)

    def number_of(self, name):
        """Return the station number of an official station name."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name of a station number."""
        return self.number_to_station[number]

    def lines_of(self, name):
        """Return the lines serving an official station name."""
        return self.graph.lines_of(name)

    def resolve_station(self, raw_name):
        """Standardise a user supplied station name.

        Matching order: exact name, normalised name (case, spaces and
        separators ignored), then the closest official name by similarity.

        Returns:
            A tuple ``(official_name, exact_match)``. ``exact_match`` is False
            when the name was matched to the nearest station.

        Raises:
            StationNotFoundError: If no reasonable match exists.
        """
        raw = (raw_name or "").strip()
        if not raw:
            raise StationNotFoundError("station name must not be empty")
        if raw in self.station_to_number:
            return raw, True
        normalized = _normalize(raw)
        if normalized in self._normalized:
            return self._normalized[normalized], True
        close = difflib.get_close_matches(raw, self.station_names, n=1, cutoff=FUZZY_MATCH_CUTOFF)
        if not close:
            close = difflib.get_close_matches(
                normalized, list(self._normalized.keys()), n=1, cutoff=FUZZY_MATCH_CUTOFF)
            if close:
                return self._normalized[close[0]], False
            raise StationNotFoundError(f"station '{raw}' does not exist")
        return close[0], False


class StationNotFoundError(Exception):
    """Raised when a station name cannot be resolved."""


def _normalize(name: str) -> str:
    """Normalise a station name for lenient comparison."""
    return re.sub(r"[\s\-_·]+", "", name).lower()


def build_network(data: dict) -> SubwayNetwork:
    """Build the routable subway network from the raw dataset.

    Station numbers are assigned by the caller (here: consecutive integers in
    dataset order). Connections are added as directed edges exactly as listed.
    Stations referenced only by connections are added automatically.

    Args:
        data: Dictionary with ``stations`` and ``connections`` lists.

    Returns:
        A ``SubwayNetwork`` instance.
    """
    lines_by_name = {}
    order = []

    for station in data.get("stations", []):
        name = str(station["name"]).strip()
        lines = [str(line) for line in station.get("lines", [])]
        if name not in lines_by_name:
            lines_by_name[name] = []
            order.append(name)
        for line in lines:
            if line not in lines_by_name[name]:
                lines_by_name[name].append(line)

    connections = data.get("connections", [])
    for connection in connections:
        source = str(connection["source"]).strip()
        dest = str(connection["dest"]).strip()
        line = str(connection["line"])
        for name in (source, dest):
            if name not in lines_by_name:
                lines_by_name[name] = []
                order.append(name)
            if line not in lines_by_name[name]:
                lines_by_name[name].append(line)

    graph = Graph()
    station_to_number = {}
    number_to_station = {}
    for number, name in enumerate(order):
        station_to_number[name] = number
        number_to_station[number] = name
        graph.add_vertex(number)
        graph.set_station_lines(name, lines_by_name[name])

    for connection in connections:
        source = station_to_number[str(connection["source"]).strip()]
        dest = station_to_number[str(connection["dest"]).strip()]
        graph.add_edge(Edge(source, dest, int(connection["distance"]), str(connection["line"])))

    return SubwayNetwork(graph, station_to_number, number_to_station)
