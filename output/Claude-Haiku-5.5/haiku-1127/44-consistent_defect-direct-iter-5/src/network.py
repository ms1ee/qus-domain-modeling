"""Subway network model and data management.

``SubwayNetwork`` owns the station-number mapping (``station_to_number``), the
directed weighted graph, and the operations used for data maintenance: adding
lines, modifying stations and updating distances.
"""

import difflib
import unicodedata

from data_loader import load_subway_data
from models import Edge, Graph


class StationNotFoundError(Exception):
    """Raised when a station name cannot be resolved to any known station."""


def _normalize(name) -> str:
    """Normalise a station name for lenient comparison."""
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    text = "".join(text.split())
    if text.endswith("站") and len(text) > 1:
        text = text[:-1]
    return text


class SubwayNetwork:
    """Beijing Subway network built from the dataset dictionary.

    Attributes:
        graph: The directed weighted ``Graph``.
        station_to_number: Mapping of official station name to station number.
        number_to_name: Reverse mapping of station number to station name.
    """

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data()
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_name = {}
        self._next_number = 0

        for station in data.get("stations", []):
            self.add_station(station["name"], station.get("lines", []))

        for conn in data.get("connections", []):
            source = self._ensure_station(conn["source"])
            dest = self._ensure_station(conn["dest"])
            self.graph.add_edge(Edge(source, dest, int(conn["distance"]), conn["line"]))

    # ----- station management ----------------------------------------------
    def add_station(self, name, lines=()) -> int:
        """Add a station (or merge lines into an existing one); return its number."""
        name = str(name).strip()
        if not name:
            raise ValueError("Station name must not be empty")
        if name in self.station_to_number:
            number = self.station_to_number[name]
            merged = list(self.graph.station_lines.get(name, []))
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.add_vertex(number)
            merged = []
        for line in lines:
            if line not in merged:
                merged.append(line)
        self.graph.set_station_lines(name, merged)
        return number

    def _ensure_station(self, name) -> int:
        """Return the number of a station, creating it without lines if needed."""
        if name in self.station_to_number:
            return self.station_to_number[name]
        return self.add_station(name, [])

    def number_of(self, name) -> int:
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def name_of(self, number) -> str:
        """Return the official station name for a station number."""
        return self.number_to_name[number]

    def station_names(self) -> list:
        """Return all official station names in numeric order."""
        return [self.number_to_name[n] for n in sorted(self.number_to_name)]

    def lines_of(self, name) -> list:
        """Return the lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def is_transfer_station(self, name) -> bool:
        """Return True if the station is served by more than one line."""
        return len(self.lines_of(name)) > 1

    def transfer_stations(self) -> list:
        """Return the names of all multi-line interchange stations."""
        return [n for n in self.station_names() if self.is_transfer_station(n)]

    def line_names(self) -> list:
        """Return the sorted names of all lines known to the network."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines)

    def stations_on_line(self, line) -> list:
        """Return the names of the stations served by a line, in numeric order."""
        numbers = set()
        for name, station_lines in self.graph.station_lines.items():
            if line in station_lines:
                numbers.add(self.station_to_number[name])
        for edge in self.graph.edges():
            if edge.line == line:
                numbers.add(edge.source)
                numbers.add(edge.dest)
        return [self.number_to_name[n] for n in sorted(numbers)]

    def resolve_station(self, name):
        """Standardise a user-supplied station name.

        Returns:
            ``(official_name, exact)``. ``exact`` is False when the name was
            matched to the nearest known station instead of matching exactly.

        Raises:
            StationNotFoundError: If no sufficiently similar station exists.
        """
        text = (name or "").strip()
        if not text:
            raise StationNotFoundError(name)
        if text in self.station_to_number:
            return text, True

        normalized = _normalize(text)
        candidates = {}
        for official in self.station_to_number:
            candidates.setdefault(_normalize(official), official)
        if normalized in candidates:
            return candidates[normalized], True

        close = difflib.get_close_matches(normalized, list(candidates), n=1, cutoff=0.6)
        if close:
            return candidates[close[0]], False
        raise StationNotFoundError(text)

    def modify_station(self, old_name, new_name=None, lines=None) -> str:
        """Rename a station and/or replace its line list.

        Returns:
            The (possibly new) official name of the station.
        """
        if old_name not in self.station_to_number:
            raise StationNotFoundError(old_name)
        number = self.station_to_number[old_name]
        current = old_name

        if new_name is not None and new_name.strip() and new_name.strip() != old_name:
            new = new_name.strip()
            if new in self.station_to_number:
                raise ValueError(f"Station '{new}' already exists")
            del self.station_to_number[old_name]
            self.station_to_number[new] = number
            self.number_to_name[number] = new
            self.graph.station_lines[new] = self.graph.station_lines.pop(old_name, [])
            current = new

        if lines is not None:
            self.graph.set_station_lines(current, list(lines))
        return current

    # ----- connection and line management ----------------------------------
    def _upsert_edge(self, source_name, dest_name, distance, line):
        """Create or update the connection source->dest on the given line."""
        source = self.number_of(source_name)
        dest = self.number_of(dest_name)
        for edge in self.graph.get_edges_between(source, dest):
            if edge.line == line:
                edge.distance = distance
                return edge
        edge = Edge(source, dest, distance, line)
        self.graph.add_edge(edge)
        return edge

    def add_line(self, line_name, station_names, distances, bidirectional=True) -> int:
        """Add a new line described by an ordered station sequence.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names along the line.
            distances: Distances in meters between consecutive stations.
            bidirectional: If True, also add the reverse direction.

        Returns:
            Number of directed connections created or updated.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Expected one distance per pair of consecutive stations")
        for distance in distances:
            if int(distance) <= 0:
                raise ValueError("Distances must be positive")

        for name in station_names:
            self.add_station(name, [line_name])

        count = 0
        for i, distance in enumerate(distances):
            first, second = station_names[i], station_names[i + 1]
            self._upsert_edge(first, second, int(distance), line_name)
            count += 1
            if bidirectional:
                self._upsert_edge(second, first, int(distance), line_name)
                count += 1
        return count

    def update_distance(self, source_name, dest_name, distance, bidirectional=False) -> int:
        """Update the distance of existing connections between two stations.

        Returns:
            Number of connections updated.

        Raises:
            StationNotFoundError: If a station is unknown.
            ValueError: If the distance is invalid or no connection exists.
        """
        if source_name not in self.station_to_number:
            raise StationNotFoundError(source_name)
        if dest_name not in self.station_to_number:
            raise StationNotFoundError(dest_name)
        if int(distance) <= 0:
            raise ValueError("Distance must be positive")

        source = self.number_of(source_name)
        dest = self.number_of(dest_name)
        edges = list(self.graph.get_edges_between(source, dest))
        if bidirectional:
            edges.extend(self.graph.get_edges_between(dest, source))
        if not edges:
            raise ValueError(f"No connection between '{source_name}' and '{dest_name}'")
        for edge in edges:
            edge.distance = int(distance)
        return len(edges)
