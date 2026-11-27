"""Subway network management: station registry, graph construction and data updates."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from .data_loader import load_subway_data
from .models import Edge, Graph


class UnknownStationError(LookupError):
    """Raised when a station name does not exist in the network."""


def _normalize(name: str) -> str:
    """Normalize a station name for lenient matching (ignore whitespace and case)."""
    return "".join(name.split()).casefold()


def _natural_key(text: str) -> list[Any]:
    """Sort key that orders embedded numbers numerically ("Line 2" < "Line 10")."""
    parts = re.split(r"(\d+)", text)
    return [int(part) if index % 2 else part.casefold() for index, part in enumerate(parts)]


class SubwayNetwork:
    """Owns the weighted graph of the subway network and the name <-> number mappings.

    Attributes:
        graph: the weighted undirected Graph (vertices are station numbers).
        station_to_number: mapping station name -> station number.
        number_to_station: mapping station number -> station name.
        declared_stations: names explicitly listed in the station data.
    """

    def __init__(self, data: Optional[dict] = None) -> None:
        self.graph = Graph()
        self.station_to_number: dict[str, int] = {}
        self.number_to_station: dict[int, str] = {}
        self.declared_stations: set[str] = set()
        if data is None:
            data = load_subway_data()
        self._build(data)

    # ----------------------------------------------------------------- building
    def _build(self, data: dict) -> None:
        """Populate the network from the dataset dictionary."""
        for station in data.get("stations", []):
            name = station["name"]
            self.add_station(name, station.get("lines", []))
            self.declared_stations.add(name.strip())
        for conn in data.get("connections", []):
            self.add_connection(conn["source"], conn["dest"], conn["distance"], conn["line"])

    def add_station(self, name: str, lines: Iterable[str] = ()) -> int:
        """Register a station (or merge new lines into an existing one).

        Returns:
            The station number assigned to the station.
        """
        name = name.strip()
        if not name:
            raise ValueError("station name cannot be empty")
        new_lines = list(lines)
        if name in self.station_to_number:
            number = self.station_to_number[name]
            merged = self.graph.get_station_lines(name)
            merged += [line for line in new_lines if line not in merged]
        else:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            merged = new_lines
        self.graph.add_vertex(number)
        self.graph.set_station_lines(name, merged)
        return number

    def add_connection(self, source: str, dest: str, distance: float, line: str) -> Edge:
        """Add a connection between two stations, creating missing stations if needed.

        Raises:
            ValueError: if the stations are identical or the distance is not positive.
        """
        for name in (source, dest):
            if name.strip() not in self.station_to_number:
                self.add_station(name, [line])
        src = self.station_to_number[source.strip()]
        dst = self.station_to_number[dest.strip()]
        edge = Edge(src, dst, distance, line)
        self.graph.add_edge(edge)
        return edge

    def add_line(self, line_name: str, stations: list[str], distances: list[float]) -> None:
        """Add a new line with its ordered station sequence and inter-station distances.

        Raises:
            ValueError: on duplicate line, too few stations, or mismatched distance count.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("line name cannot be empty")
        if line_name in self.lines():
            raise ValueError(f"line '{line_name}' already exists")
        if len(stations) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("number of distances must be one less than number of stations")
        for name in stations:
            self.add_station(name, [line_name])
            self.declared_stations.add(name.strip())
        for index, distance in enumerate(distances):
            self.add_connection(stations[index], stations[index + 1], distance, line_name)

    # ------------------------------------------------------------------ queries
    def standard_name(self, name: str) -> Optional[str]:
        """Return the official station name matching ``name``, or None if unknown."""
        if not isinstance(name, str):
            return None
        cleaned = name.strip()
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        key = _normalize(cleaned)
        for official in self.station_to_number:
            if _normalize(official) == key:
                return official
        return None

    def station_number(self, name: str) -> int:
        """Return the station number of ``name``.

        Raises:
            UnknownStationError: if the station does not exist.
        """
        official = self.standard_name(name)
        if official is None:
            raise UnknownStationError(name)
        return self.station_to_number[official]

    def station_name(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.number_to_station[number]

    def lines(self) -> list[str]:
        """Return all line names in the network (naturally sorted)."""
        found: set[str] = set()
        for lines in self.graph.station_lines.values():
            found.update(lines)
        return sorted(found, key=_natural_key)

    def stations_on_line(self, line: str) -> list[str]:
        """Return the names of stations served by ``line``."""
        return [name for name, lines in self.graph.station_lines.items() if line in lines]

    def is_transfer_station(self, name: str) -> bool:
        """Return True if the station is served by more than one line."""
        return len(self.graph.get_station_lines(name)) > 1

    # ------------------------------------------------------------ data updates
    def update_station(
        self, old_name: str, new_name: Optional[str] = None, lines: Optional[list[str]] = None
    ) -> None:
        """Rename a station and/or replace its line affiliation.

        Raises:
            UnknownStationError: if ``old_name`` does not exist.
            ValueError: if the new name is taken or no lines remain.
        """
        number = self.station_number(old_name)
        old = self.number_to_station[number]
        new = (new_name or old).strip()
        if new != old and new in self.station_to_number:
            raise ValueError(f"station '{new}' already exists")
        new_lines = list(lines) if lines is not None else self.graph.get_station_lines(old)
        if not new_lines:
            raise ValueError("a station must belong to at least one line")
        if new != old:
            del self.station_to_number[old]
            self.station_to_number[new] = number
            self.number_to_station[number] = new
            self.graph.station_lines.pop(old, None)
            if old in self.declared_stations:
                self.declared_stations.discard(old)
                self.declared_stations.add(new)
        self.graph.set_station_lines(new, new_lines)

    def update_distance(
        self, name_a: str, name_b: str, distance: float, line: Optional[str] = None
    ) -> int:
        """Update the distance of the connection(s) between two stations.

        Returns:
            The number of connections updated.

        Raises:
            UnknownStationError: if a station does not exist.
            ValueError: if no matching connection exists or the distance is invalid.
        """
        if distance <= 0:
            raise ValueError("distance must be positive")
        a = self.station_number(name_a)
        b = self.station_number(name_b)
        edges = [e for e in self.graph.find_edges(a, b) if line is None or e.line == line]
        if not edges:
            raise ValueError(f"no connection between '{name_a}' and '{name_b}'")
        for edge in edges:
            edge.distance = float(distance)
        return len(edges)

    def to_data(self) -> dict:
        """Export the network back into the dataset format."""
        stations = [
            {"name": name, "lines": list(self.graph.get_station_lines(name))}
            for name in self.station_to_number
        ]
        connections = []
        for edge in self.graph.edges():
            distance = edge.distance
            connections.append(
                {
                    "source": self.number_to_station[edge.source],
                    "dest": self.number_to_station[edge.dest],
                    "distance": int(distance) if float(distance).is_integer() else distance,
                    "line": edge.line,
                }
            )
        return {"stations": stations, "connections": connections}
