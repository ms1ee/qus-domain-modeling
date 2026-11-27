"""
Subway network construction and station name resolution.

``SubwayNetwork`` converts the raw data dictionary (from subway_data.json)
into a ``Graph`` and maintains the mapping between station names and
station numbers.
"""

import re

from models import Edge, Graph

_STATION_SUFFIX_RE = re.compile(r"(站|\s*station)$", re.IGNORECASE)


def normalize_station_name(name):
    """
    Produce a normalized key for station name matching.

    Collapses whitespace, removes a trailing "站" / "Station" suffix and
    compares case-insensitively.
    """
    text = " ".join(str(name).split())
    text = _STATION_SUFFIX_RE.sub("", text).strip()
    return text.casefold()


class SubwayNetwork:
    """
    The subway network as a graph plus station name/number mappings.

    Attributes:
        station_to_number: dict mapping official station name -> station number.
        number_to_station: dict mapping station number -> official station name.
        graph: The Graph instance holding edges and station lines.
    """

    def __init__(self, data):
        """
        Build the network from the raw data dictionary.

        Args:
            data: dict with "stations" and "connections" lists.

        Raises:
            ValueError: If a connection refers to an unknown station.
        """
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = Graph()
        self._normalized = {}
        self._lines = set()
        self._build(data)

    def _build(self, data):
        merged_lines = {}
        order = []
        for station in data.get("stations", []):
            name = station["name"]
            if name not in merged_lines:
                merged_lines[name] = []
                order.append(name)
            for line in station.get("lines", []):
                if line not in merged_lines[name]:
                    merged_lines[name].append(line)

        for name in order:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self._normalized.setdefault(normalize_station_name(name), name)
            self.graph.set_station_lines(name, merged_lines[name])
            self.graph.add_vertex(number)
            self._lines.update(merged_lines[name])

        for conn in data.get("connections", []):
            source = conn["source"]
            dest = conn["dest"]
            for name in (source, dest):
                if name not in self.station_to_number:
                    raise ValueError(f"Connection refers to unknown station '{name}'")
            line = conn["line"]
            self._lines.add(line)
            self.graph.add_edge(
                Edge(
                    self.station_to_number[source],
                    self.station_to_number[dest],
                    int(conn["distance"]),
                    line,
                )
            )

    def number_of(self, name):
        """Return the station number for an official station name (KeyError if unknown)."""
        return self.station_to_number[name]

    def name_of(self, number):
        """Return the official station name for a station number (KeyError if unknown)."""
        return self.number_to_station[number]

    def has_station(self, name):
        """Return True if the official station name exists."""
        return name in self.station_to_number

    def resolve_name(self, raw_name):
        """
        Standardize a user-entered station name against the official names.

        Returns:
            The official station name, or None if no station matches.
        """
        if raw_name in self.station_to_number:
            return raw_name
        return self._normalized.get(normalize_station_name(raw_name))

    def station_names(self):
        """Return the sorted list of official station names."""
        return sorted(self.station_to_number.keys())

    def lines(self):
        """Return the sorted list of all line names in the network."""
        return sorted(self._lines)
