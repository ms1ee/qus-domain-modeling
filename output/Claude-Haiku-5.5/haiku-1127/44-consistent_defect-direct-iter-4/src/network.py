"""Builds the weighted directed subway network from the dataset.

Responsibilities:
    * Assign station numbers (the Graph itself does not assign numbers).
    * Maintain the station_to_number mapping and the graph.
    * Resolve user-supplied station names to official names.
"""

import difflib
import unicodedata

from data_loader import DataLoadError
from models import Edge, Graph

FUZZY_MATCH_CUTOFF = 0.6


def normalize_station_name(name):
    """Standardize a station name: NFKC normalization and collapsed whitespace."""
    if name is None:
        return ""
    text = unicodedata.normalize("NFKC", str(name))
    return " ".join(text.split())


class SubwayNetwork:
    """The subway network: graph plus station name/number mappings.

    Attributes:
        graph: models.Graph with directed edges between station numbers.
        station_to_number: dict mapping official station name to station number.
        number_to_name: list mapping station number to official station name.
    """

    def __init__(self, data):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = []
        self._lower_map = {}
        self._build(data)

    def _register_station(self, name):
        """Return the number of a station, assigning a new one if needed."""
        number = self.station_to_number.get(name)
        if number is None:
            number = len(self.number_to_name)
            self.number_to_name.append(name)
            self.station_to_number[name] = number
            self._lower_map[name.lower()] = name
        return number

    def _build(self, data):
        """Populate the graph from the dataset."""
        for entry in data.get("stations", []):
            name = normalize_station_name(entry.get("name"))
            if not name:
                continue
            self._register_station(name)
            lines = [str(line) for line in entry.get("lines", [])]
            self.graph.set_station_lines(name, lines)

        for conn in data.get("connections", []):
            source = normalize_station_name(conn.get("source"))
            dest = normalize_station_name(conn.get("dest"))
            line = str(conn.get("line", "")).strip()
            if not source or not dest:
                continue
            try:
                distance = int(conn.get("distance"))
            except (TypeError, ValueError) as exc:
                raise DataLoadError(
                    f"Invalid distance for connection {source} -> {dest}: "
                    f"{conn.get('distance')!r}"
                ) from exc

            source_no = self._register_station(source)
            dest_no = self._register_station(dest)
            for name in (source, dest):
                lines = self.graph.station_lines.setdefault(name, [])
                if line and line not in lines:
                    lines.append(line)
            self.graph.add_edge(Edge(source_no, dest_no, distance, line))

    def station_names(self):
        """Return all official station names."""
        return list(self.number_to_name)

    def resolve_station(self, name):
        """Match a user-supplied name to an official station name.

        Returns:
            (official_name, exact_match) or None if no station is close enough.
            exact_match is False when the name was matched to the nearest station.
        """
        normalized = normalize_station_name(name)
        if not normalized:
            return None
        if normalized in self.station_to_number:
            return normalized, True
        official = self._lower_map.get(normalized.lower())
        if official is not None:
            return official, True
        matches = difflib.get_close_matches(
            normalized, self.number_to_name, n=1, cutoff=FUZZY_MATCH_CUTOFF
        )
        if matches:
            return matches[0], False
        return None

    def transfer_stations(self):
        """Return names of stations served by more than one line."""
        return [
            name for name in self.number_to_name
            if len(self.graph.station_lines.get(name, [])) > 1
        ]

    def line_names(self):
        """Return the sorted list of all line names in the network."""
        lines = set()
        for edge in self.graph.edges():
            if edge.line:
                lines.add(edge.line)
        return sorted(lines)
