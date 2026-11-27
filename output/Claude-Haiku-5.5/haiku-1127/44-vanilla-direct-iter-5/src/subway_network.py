"""Subway network model: station registry, line registry and graph building.

The network maps official station names to integer station numbers, which are
used as vertices of the ``Graph``. It also provides data-update operations:
adding lines, modifying stations and updating inter-station distances.
"""
from __future__ import annotations

from models import DataError, Edge, Graph, SubwayError, UnknownStationError


class SubwayNetwork:
    """Subway network built from the dataset.

    Attributes:
        graph: the weighted undirected ``Graph``.
        station_to_number: mapping official station name -> station number.
        number_to_name: mapping station number -> official station name.
        line_stations: mapping line name -> ordered list of station names.
    """

    def __init__(self) -> None:
        self.graph = Graph()
        self.station_to_number: dict[str, int] = {}
        self.number_to_name: dict[int, str] = {}
        self.line_stations: dict[str, list[str]] = {}
        self._next_number = 0

    # ----- construction ---------------------------------------------------
    @classmethod
    def from_data(cls, data: dict) -> "SubwayNetwork":
        """Build the network from the parsed ``subway_data.json`` content."""
        network = cls()
        try:
            for station in data.get("stations", []):
                network.add_station(station["name"], station.get("lines", []))
            for conn in data.get("connections", []):
                network.add_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])
        except (KeyError, TypeError) as exc:
            raise DataError(f"Malformed subway data: {exc}") from exc
        return network

    def _register(self, line: str, station_name: str) -> None:
        members = self.line_stations.setdefault(line, [])
        if station_name not in members:
            members.append(station_name)

    def add_station(self, name: str, lines: list[str] | tuple = ()) -> int:
        """Add a station (or merge lines into an existing one); return its number."""
        name = str(name).strip()
        if not name:
            raise DataError("Station name must not be empty")
        lines = [str(line).strip() for line in lines if str(line).strip()]
        if name in self.station_to_number:
            number = self.station_to_number[name]
            existing = self.graph.lines_of(name)
            merged = existing + [line for line in lines if line not in existing]
            self.graph.set_station_lines(name, merged)
        else:
            number = self._next_number
            self._next_number += 1
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, lines)
        for line in lines:
            self._register(line, name)
        return number

    def add_connection(self, source: str, dest: str, distance: int, line: str) -> Edge:
        """Add a connection between two stations; unknown stations are created."""
        line = str(line).strip()
        for name in (source, dest):
            if name not in self.station_to_number:
                self.add_station(name, [line])
        s = self.number_for(source)
        d = self.number_for(dest)
        edge = Edge(s, d, int(distance), line)
        self.graph.add_edge(edge)
        self._register(line, source)
        self._register(line, dest)
        return edge

    # ----- lookups --------------------------------------------------------
    def has_station(self, name: str) -> bool:
        return name in self.station_to_number

    def number_for(self, name: str) -> int:
        """Return the station number for an official name."""
        try:
            return self.station_to_number[name]
        except KeyError:
            raise UnknownStationError(f"Station '{name}' does not exist") from None

    def name_for(self, number: int) -> str:
        """Return the official name for a station number."""
        try:
            return self.number_to_name[number]
        except KeyError:
            raise UnknownStationError(f"No station with number {number}") from None

    def stations(self) -> list[str]:
        """All official station names."""
        return list(self.station_to_number.keys())

    def lines(self) -> list[str]:
        """All line names."""
        return list(self.line_stations.keys())

    def normalize_station_name(self, raw: str) -> str | None:
        """Map user input to an official station name, or None if not found.

        Matching order: exact name, case-insensitive name, then with or
        without the Chinese suffix "站" (station).
        """
        text = " ".join(str(raw).split())
        if not text:
            return None
        if text in self.station_to_number:
            return text
        folded = text.casefold()
        for name in self.station_to_number:
            if name.casefold() == folded:
                return name
        if text.endswith("站"):
            stripped = text[:-1].strip()
            if stripped in self.station_to_number:
                return stripped
        candidate = text + "站"
        if candidate in self.station_to_number:
            return candidate
        return None

    # ----- data updates ---------------------------------------------------
    def add_line(self, line_name: str, station_names: list[str], distances: list[int]) -> list[Edge]:
        """Add a new line as an ordered station sequence with consecutive distances.

        Raises:
            DataError: if the line already exists or the inputs are inconsistent.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise DataError("Line name must not be empty")
        if line_name in self.line_stations:
            raise DataError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise DataError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise DataError("Number of distances must equal number of stations minus one")
        for name in station_names:
            self.add_station(name, [line_name])
        return [
            self.add_connection(station_names[i], station_names[i + 1], distances[i], line_name)
            for i in range(len(distances))
        ]

    def modify_station(self, name: str, new_name: str | None = None,
                       lines: list[str] | None = None) -> None:
        """Rename a station and/or replace its list of lines."""
        number = self.number_for(name)
        current = name
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                raise DataError("New station name must not be empty")
            if new_name != name:
                if new_name in self.station_to_number:
                    raise DataError(f"Station '{new_name}' already exists")
                del self.station_to_number[name]
                self.station_to_number[new_name] = number
                self.number_to_name[number] = new_name
                self.graph.station_lines[new_name] = self.graph.station_lines.pop(name, [])
                for members in self.line_stations.values():
                    for i, member in enumerate(members):
                        if member == name:
                            members[i] = new_name
                current = new_name
        if lines is not None:
            new_lines = list(dict.fromkeys(str(l).strip() for l in lines if str(l).strip()))
            self.graph.set_station_lines(current, new_lines)
            for line in new_lines:
                self._register(line, current)
            for line, members in self.line_stations.items():
                if line not in new_lines and current in members:
                    members.remove(current)

    def update_distance(self, source: str, dest: str, distance: int, line: str | None = None) -> int:
        """Update the distance between two adjacent stations.

        Returns:
            Number of connection records updated.

        Raises:
            SubwayError: if no matching connection exists.
            ValueError: if the distance is negative.
        """
        if distance < 0:
            raise ValueError("Distance must be non-negative")
        a = self.number_for(source)
        b = self.number_for(dest)
        edges = [e for e in self.graph.edges_between(a, b) if line is None or e.line == line]
        if not edges:
            raise SubwayError(f"No connection between '{source}' and '{dest}'")
        for edge in edges:
            edge.weight = int(distance)
        return len(edges)
