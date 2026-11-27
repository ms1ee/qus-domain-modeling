"""Subway network model: station registry, graph construction and data updates.

This module maps official station names to integer station numbers, builds the
weighted graph from the raw dataset, and offers data-management operations
(adding lines, modifying stations, updating distances).
"""

import math

from models import Edge, Graph

LOAD_CATEGORY_DATA = "data"
LOAD_CATEGORY_CONNECTIVITY = "connectivity"
LOAD_CATEGORY_DISTANCE = "distance"


def clean_name(value):
    """Normalize a name: non-strings become '', and whitespace is collapsed."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def is_valid_distance(value):
    """Return True if ``value`` is a finite, positive, non-boolean number."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    Attributes:
        name: display name of the network.
        data_source: description of the data source.
        raw_data: the original dataset dict (used by integrity checks).
        graph: the weighted undirected ``Graph`` keyed by station numbers.
        station_to_number: official station name -> station number.
        number_to_station: station number -> official station name.
        load_warnings: list of (category, message) for skipped/bad records.
    """

    def __init__(self, data, name="Beijing Subway", data_source="subway_data.json"):
        if not isinstance(data, dict):
            raise TypeError("subway data must be a dict")
        self.name = name
        self.data_source = data_source
        self.raw_data = data
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self.load_warnings = []
        self._line_names = []
        self._next_number = 0
        self._build(data)

    # ----- construction ------------------------------------------------------
    def _build(self, data):
        """Populate stations and connections from the raw dataset."""
        for item in data.get("stations") or []:
            if not isinstance(item, dict):
                self.load_warnings.append((LOAD_CATEGORY_DATA, "Malformed station record skipped: {!r}".format(item)))
                continue
            name = clean_name(item.get("name"))
            if not name:
                self.load_warnings.append((LOAD_CATEGORY_DATA, "Station record without a name skipped"))
                continue
            lines = item.get("lines") or []
            if not isinstance(lines, list):
                lines = []
            self._add_station(name, lines)

        for conn in data.get("connections") or []:
            if not isinstance(conn, dict):
                self.load_warnings.append((LOAD_CATEGORY_DATA, "Malformed connection record skipped: {!r}".format(conn)))
                continue
            src = clean_name(conn.get("source"))
            dst = clean_name(conn.get("dest"))
            line = clean_name(conn.get("line"))
            if not src or not dst or not line:
                self.load_warnings.append((LOAD_CATEGORY_CONNECTIVITY, "Incomplete connection record skipped: {!r}".format(conn)))
                continue
            if src == dst:
                self.load_warnings.append((LOAD_CATEGORY_CONNECTIVITY, "Self-loop connection at '{}' skipped".format(src)))
                continue
            distance = conn.get("distance")
            if not is_valid_distance(distance):
                self.load_warnings.append((LOAD_CATEGORY_DISTANCE, "Invalid distance {!r} between '{}' and '{}' skipped".format(distance, src, dst)))
                continue
            a = self._add_station(src, [line])
            b = self._add_station(dst, [line])
            if self.graph.find_edge(a, b, line) is not None:
                self.load_warnings.append((LOAD_CATEGORY_DATA, "Duplicate connection '{}' - '{}' on {} ignored".format(src, dst, line)))
                continue
            self.graph.add_edge(Edge(a, b, distance, line))

    def _add_station(self, name, lines=()):
        """Create a station if needed, merge in the given lines, return its number."""
        if name not in self.station_to_number:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, [])
        current = self.graph.station_lines[name]
        for line in lines:
            line = clean_name(line)
            if not line:
                continue
            self.register_line(line)
            if line not in current:
                current.append(line)
        return self.station_to_number[name]

    def register_line(self, line):
        """Register a line name (kept in first-seen order)."""
        if line and line not in self._line_names:
            self._line_names.append(line)

    # ----- queries -----------------------------------------------------------
    @property
    def station_count(self):
        """Number of stations in the network."""
        return len(self.station_to_number)

    @property
    def line_count(self):
        """Number of lines in the network."""
        return len(self._line_names)

    @property
    def line_names(self):
        """List of all line names."""
        return list(self._line_names)

    def has_station(self, name):
        """Return True if the exact official name exists."""
        return name in self.station_to_number

    def standardize_station_name(self, name):
        """Map user input to an official station name (case-insensitive).

        Returns:
            The official name, or None if no station matches.
        """
        cleaned = clean_name(name)
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        folded = cleaned.casefold()
        for official in self.station_to_number:
            if official.casefold() == folded:
                return official
        return None

    def station_name(self, number):
        """Return the official name of a station number."""
        return self.number_to_station[number]

    def get_lines(self, name):
        """Return a copy of the list of lines serving a station."""
        official = self._require_station(name)
        return list(self.graph.station_lines[official])

    def is_transfer_station(self, name):
        """Return True if the station is served by two or more lines."""
        return len(self.get_lines(name)) >= 2

    def transfer_stations(self):
        """Return a sorted list of all transfer (interchange) station names."""
        return sorted(name for name in self.station_to_number if len(self.graph.station_lines[name]) >= 2)

    def stations_on_line(self, line):
        """Return the stations of a line, ordered by station number."""
        result = []
        for number in sorted(self.number_to_station):
            name = self.number_to_station[number]
            if line in self.graph.station_lines[name]:
                result.append(name)
        return result

    def _require_station(self, name):
        """Return the official name for ``name`` or raise KeyError."""
        official = self.standardize_station_name(name)
        if official is None:
            raise KeyError("Station '{}' does not exist".format(name))
        return official

    # ----- data management ---------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: name of the new line (must not already exist).
            station_names: ordered list of station names (at least two).
            distances: list of distances in meters, one per consecutive pair.

        Raises:
            ValueError: on invalid input.
        """
        line = clean_name(line_name)
        if not line:
            raise ValueError("Line name must not be empty")
        if line in self._line_names:
            raise ValueError("Line '{}' already exists".format(line))
        names = [clean_name(n) for n in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not n for n in names):
            raise ValueError("Station names must not be empty")
        if len(set(names)) != len(names):
            raise ValueError("A station may appear only once on a new line")
        if len(distances) != len(names) - 1:
            raise ValueError("Expected {} distances, got {}".format(len(names) - 1, len(distances)))
        for distance in distances:
            if not is_valid_distance(distance):
                raise ValueError("Invalid distance {!r}".format(distance))

        self.register_line(line)
        numbers = []
        for name in names:
            official = self.standardize_station_name(name) or name
            numbers.append(self._add_station(official, [line]))
        for a, b, distance in zip(numbers, numbers[1:], distances):
            self.graph.add_edge(Edge(a, b, distance, line))

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line affiliations.

        Returns:
            The official name of the station after modification.
        """
        old = self._require_station(old_name)
        number = self.station_to_number[old]
        target = old
        if new_name is not None:
            new = clean_name(new_name)
            if not new:
                raise ValueError("New station name must not be empty")
            existing = self.standardize_station_name(new)
            if existing is not None and existing != old:
                raise ValueError("Station '{}' already exists".format(existing))
            target = new

        if target != old:
            del self.station_to_number[old]
            self.station_to_number[target] = number
            self.number_to_station[number] = target
            self.graph.station_lines[target] = self.graph.station_lines.pop(old)

        if lines is not None:
            cleaned = []
            for line in lines:
                line = clean_name(line)
                if line and line not in cleaned:
                    cleaned.append(line)
                    self.register_line(line)
            self.graph.station_lines[target] = cleaned
        return target

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance (meters) of an existing connection.

        Returns:
            The updated Edge.

        Raises:
            ValueError: if the distance is invalid.
            KeyError: if no matching connection exists.
        """
        if not is_valid_distance(distance):
            raise ValueError("distance must be a positive number of meters")
        src = self._require_station(source)
        dst = self._require_station(dest)
        edge = self.graph.find_edge(self.station_to_number[src], self.station_to_number[dst], line)
        if edge is None:
            suffix = " on {}".format(line) if line else ""
            raise KeyError("No connection between '{}' and '{}'{}".format(src, dst, suffix))
        edge.distance = distance
        return edge
