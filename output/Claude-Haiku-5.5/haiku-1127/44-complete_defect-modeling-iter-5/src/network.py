"""Subway network management.

``SubwayNetwork`` owns the station-name <-> station-number mapping, the weighted
``Graph`` and provides name validation and data-update operations (adding lines,
modifying station information and updating distances).
"""

import difflib

from models import Edge, Graph


class NetworkError(Exception):
    """Raised for invalid network operations or data."""


class UnknownStationError(NetworkError):
    """Raised when a station name does not exist in the network.

    Attributes:
        suggestions: List of close station names that may have been intended.
    """

    def __init__(self, message, suggestions=None):
        super().__init__(message)
        self.suggestions = list(suggestions or [])


def _clean(value):
    """Normalize a name: collapse internal whitespace and strip the ends."""
    return " ".join(str(value).split())


def _validate_distance(distance):
    """Validate a distance in meters and return it as a positive int."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise NetworkError(f"Distance must be a number, got {distance!r}")
    if distance <= 0:
        raise NetworkError(f"Distance must be positive, got {distance!r}")
    return int(round(distance))


class SubwayNetwork:
    """Subway network model: stations, lines, connections and their numbering."""

    def __init__(self):
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._next_number = 0

    @classmethod
    def from_data(cls, data):
        """Build a network from the dictionary produced by ``load_subway_data``.

        Duplicate connections (for example the same segment listed in both
        directions) are silently merged.
        """
        network = cls()
        for station in data.get("stations", []):
            network.add_station(station["name"], station.get("lines", []))
        for conn in data.get("connections", []):
            source = _clean(conn["source"])
            dest = _clean(conn["dest"])
            line = _clean(conn["line"])
            if network.has_connection(source, dest, line):
                continue
            network.add_connection(source, dest, conn["distance"], line)
        return network

    # ------------------------------------------------------------------ queries
    def has_station(self, name):
        """Return True if the station name exists in the network."""
        return _clean(name) in self.station_to_number

    def station_number(self, name):
        """Return the station number for ``name``.

        Raises:
            UnknownStationError: If the station does not exist.
        """
        cleaned = _clean(name)
        if cleaned not in self.station_to_number:
            raise UnknownStationError(f"Station '{cleaned}' does not exist")
        return self.station_to_number[cleaned]

    def station_name(self, number):
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return a sorted list of all station names."""
        return sorted(self.station_to_number)

    def station_lines(self, name):
        """Return a copy of the list of lines a station belongs to."""
        return list(self.graph.station_lines.get(_clean(name), []))

    def line_names(self):
        """Return a sorted list of all line names in the network."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        return sorted(lines)

    def stations_on_line(self, line):
        """Return a sorted list of station names operating on ``line``."""
        return [
            name
            for name in self.station_names()
            if line in self.graph.station_lines.get(name, [])
        ]

    def transfer_stations(self):
        """Return a sorted list of station names that belong to more than one line."""
        return [
            name
            for name in self.station_names()
            if len(self.graph.station_lines.get(name, [])) > 1
        ]

    def has_connection(self, source, dest, line=None):
        """Return True if a connection between two station names exists."""
        source = _clean(source)
        dest = _clean(dest)
        if source not in self.station_to_number or dest not in self.station_to_number:
            return False
        return self.graph.has_edge(
            self.station_to_number[source], self.station_to_number[dest], line
        )

    # --------------------------------------------------------- name validation
    def resolve_station_name(self, raw, role="Station"):
        """Standardize a user-entered station name against official names.

        Matching is whitespace-tolerant and case-insensitive.

        Args:
            raw: Name entered by the user.
            role: Prefix used in the error message, e.g. "Starting station".

        Returns:
            str: The official station name.

        Raises:
            UnknownStationError: If no matching station exists.
        """
        cleaned = _clean(raw)
        if cleaned in self.station_to_number:
            return cleaned
        folded = {name.casefold(): name for name in self.station_to_number}
        if cleaned.casefold() in folded:
            return folded[cleaned.casefold()]
        suggestions = difflib.get_close_matches(
            cleaned, self.station_names(), n=3, cutoff=0.6
        )
        raise UnknownStationError(
            f"{role} '{cleaned}' does not exist, please check the station name",
            suggestions,
        )

    def resolve_line_name(self, raw):
        """Standardize a user-entered line name against the network's line names.

        Raises:
            NetworkError: If no matching line exists.
        """
        cleaned = _clean(raw)
        lines = self.line_names()
        if cleaned in lines:
            return cleaned
        folded = {line.casefold(): line for line in lines}
        if cleaned.casefold() in folded:
            return folded[cleaned.casefold()]
        raise NetworkError(f"Line '{cleaned}' does not exist")

    # ----------------------------------------------------------- data updates
    def add_station(self, name, lines=()):
        """Add a station (or merge new lines into an existing station).

        Returns:
            int: The station number.
        """
        cleaned = _clean(name)
        if not cleaned:
            raise NetworkError("Station name must not be empty")
        if cleaned not in self.station_to_number:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[cleaned] = number
            self.number_to_station[number] = cleaned
            self.graph.add_node(number)
            self.graph.set_station_lines(cleaned, [])
        merged = list(self.graph.station_lines.get(cleaned, []))
        for line in lines:
            line_name = _clean(line)
            if line_name and line_name not in merged:
                merged.append(line_name)
        self.graph.set_station_lines(cleaned, merged)
        return self.station_to_number[cleaned]

    def update_station_lines(self, name, lines):
        """Replace the line affiliation of an existing station.

        Raises:
            UnknownStationError: If the station does not exist.
            NetworkError: If no valid line is provided.
        """
        cleaned = _clean(name)
        if cleaned not in self.station_to_number:
            raise UnknownStationError(f"Station '{cleaned}' does not exist")
        new_lines = [_clean(line) for line in lines if _clean(line)]
        if not new_lines:
            raise NetworkError("A station must belong to at least one line")
        self.graph.set_station_lines(cleaned, new_lines)

    def add_connection(self, source, dest, distance, line):
        """Add a connection between two stations on a line.

        Missing endpoints are created automatically and the line is attached to them.

        Returns:
            Edge: The newly created edge.

        Raises:
            NetworkError: For invalid input or a duplicate connection.
        """
        source = _clean(source)
        dest = _clean(dest)
        line = _clean(line)
        if not source or not dest:
            raise NetworkError("Connection endpoints must not be empty")
        if source == dest:
            raise NetworkError("Connection endpoints must be different stations")
        if not line:
            raise NetworkError("Connection must belong to a line")
        dist = _validate_distance(distance)
        if self.has_connection(source, dest, line):
            raise NetworkError(
                f"Connection between '{source}' and '{dest}' on '{line}' already exists"
            )
        a = self.add_station(source, [line])
        b = self.add_station(dest, [line])
        edge = Edge(a, b, dist, line)
        self.graph.add_edge(edge)
        return edge

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of an existing connection.

        Raises:
            NetworkError: If no matching connection exists or the distance is invalid.
        """
        source = _clean(source)
        dest = _clean(dest)
        dist = _validate_distance(distance)
        if source not in self.station_to_number or dest not in self.station_to_number:
            raise NetworkError(f"No connection between '{source}' and '{dest}'")
        count = self.graph.update_edge_distance(
            self.station_to_number[source],
            self.station_to_number[dest],
            dist,
            _clean(line) if line else None,
        )
        if count == 0:
            raise NetworkError(f"No connection between '{source}' and '{dest}'")
        return count

    def add_line(self, line_name, station_names, distances):
        """Add a new line from an ordered list of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered station names along the line (at least 2).
            distances: Distances in meters between consecutive stations
                (``len(station_names) - 1`` values).

        Raises:
            NetworkError: If the input is invalid.
        """
        line = _clean(line_name)
        if not line:
            raise NetworkError("Line name must not be empty")
        if line in self.line_names():
            raise NetworkError(f"Line '{line}' already exists")
        names = [_clean(name) for name in station_names]
        if len(names) < 2:
            raise NetworkError("A line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise NetworkError("Number of distances must be one less than number of stations")
        checked = [_validate_distance(d) for d in distances]
        for name in names:
            self.add_station(name, [line])
        for index, dist in enumerate(checked):
            self.add_connection(names[index], names[index + 1], dist, line)

    def __repr__(self):
        return (
            f"SubwayNetwork(stations={len(self.station_to_number)}, "
            f"connections={self.graph.num_edges()})"
        )
