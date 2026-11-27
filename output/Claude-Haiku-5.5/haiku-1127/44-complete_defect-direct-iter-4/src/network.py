"""Subway network management: station registry, lines, and data updates.

This module maps station names to integer station numbers, builds the
``Graph`` from the loaded dataset, and provides update operations such as
adding a new line, modifying a station, and updating a distance.
"""

import re
from typing import Any, Dict, List, Optional

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


class UnknownStationError(ValueError):
    """Raised when a station name does not exist in the network."""


def normalize_name(name: Any) -> str:
    """Collapse internal whitespace and strip leading/trailing spaces."""
    return re.sub(r"\s+", " ", str(name)).strip()


class SubwayNetwork:
    """Container for the subway graph plus name/number mappings.

    Attributes:
        station_to_number: mapping from canonical station name to station number.
        number_to_name: mapping from station number to canonical station name.
        graph: the weighted undirected ``Graph``.
        load_warnings: messages produced while loading (e.g., unknown stations
            referenced only by connections).
    """

    def __init__(self) -> None:
        self.station_to_number: Dict[str, int] = {}
        self.number_to_name: Dict[int, str] = {}
        self.graph = Graph()
        self.load_warnings: List[str] = []
        self._next_number = 0
        self._fold_index: Dict[str, str] = {}

    # ----- construction -------------------------------------------------
    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "SubwayNetwork":
        """Build a network from a dataset dictionary."""
        network = cls()
        network._load(data)
        return network

    @classmethod
    def from_file(cls, path: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Build a network from the JSON data file."""
        return cls.from_data(load_subway_data(path))

    def _load(self, data: Dict[str, Any]) -> None:
        for station in data.get("stations", []):
            self._add_station(station["name"], station.get("lines", []))

        for conn in data.get("connections", []):
            source = normalize_name(conn["source"])
            dest = normalize_name(conn["dest"])
            line = normalize_name(conn["line"])
            for name in (source, dest):
                if name not in self.station_to_number:
                    self._add_station(name, [])
                    self.load_warnings.append(
                        f"Station '{name}' appears only in connections, not in the station list"
                    )
            self.graph.add_edge(
                Edge(
                    self.station_to_number[source],
                    self.station_to_number[dest],
                    int(round(float(conn["distance"]))),
                    line,
                )
            )

    # ----- internal helpers ---------------------------------------------
    def _add_station(self, name: Any, lines: List[str]) -> int:
        """Register a station (merging lines if it already exists)."""
        canonical = normalize_name(name)
        if canonical in self.station_to_number:
            number = self.station_to_number[canonical]
            current = self.graph.station_lines.setdefault(canonical, [])
            for line in lines:
                line = normalize_name(line)
                if line and line not in current:
                    current.append(line)
            return number

        number = self._next_number
        self._next_number += 1
        self.station_to_number[canonical] = number
        self.number_to_name[number] = canonical
        self._fold_index[canonical.casefold()] = canonical
        self.graph.set_station_lines(canonical, [normalize_name(l) for l in lines if normalize_name(l)])
        self.graph.add_vertex(number)
        return number

    @staticmethod
    def _validate_distance(distance: Any) -> int:
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError(f"Distance must be a number of meters, got {distance!r}")
        if distance <= 0:
            raise ValueError(f"Distance must be positive, got {distance}")
        return int(round(distance))

    # ----- queries ------------------------------------------------------
    def resolve_station(self, name: Any) -> Optional[str]:
        """Return the canonical station name for ``name`` or None if unknown.

        Matching order: exact name, case-insensitive name, name with a
        trailing "站" (station) suffix removed.
        """
        norm = normalize_name(name)
        if not norm:
            return None
        if norm in self.station_to_number:
            return norm
        found = self._fold_index.get(norm.casefold())
        if found is not None:
            return found
        if norm.endswith("站"):
            base = norm[:-1].strip()
            if base in self.station_to_number:
                return base
            return self._fold_index.get(base.casefold())
        return None

    def has_station(self, name: Any) -> bool:
        """Return True if the station exists (after standardization)."""
        return self.resolve_station(name) is not None

    def number_of(self, name: Any) -> int:
        """Return the station number of ``name``.

        Raises:
            UnknownStationError: if the station does not exist.
        """
        canonical = self.resolve_station(name)
        if canonical is None:
            raise UnknownStationError(f"Station '{name}' does not exist")
        return self.station_to_number[canonical]

    def name_of(self, number: int) -> str:
        """Return the canonical station name for a station number."""
        return self.number_to_name[number]

    def station_names(self) -> List[str]:
        """Return all station names sorted alphabetically."""
        return sorted(self.station_to_number.keys())

    def lines_of(self, name: Any) -> List[str]:
        """Return the lines a station belongs to."""
        canonical = self.resolve_station(name)
        if canonical is None:
            raise UnknownStationError(f"Station '{name}' does not exist")
        return list(self.graph.station_lines.get(canonical, []))

    def transfer_stations(self) -> List[str]:
        """Return names of stations served by two or more lines, sorted."""
        return sorted(
            name for name, lines in self.graph.station_lines.items() if len(set(lines)) >= 2
        )

    def all_lines(self) -> List[str]:
        """Return all known line names (from stations and connections), sorted."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for edge in self.graph.edges():
            lines.add(edge.line)
        return sorted(lines)

    def resolve_line(self, name: Any) -> Optional[str]:
        """Return the canonical line name matching ``name`` (case-insensitive)."""
        norm = normalize_name(name)
        if not norm:
            return None
        for line in self.all_lines():
            if line == norm or line.casefold() == norm.casefold():
                return line
        return None

    def stations_on_line(self, line: str) -> List[str]:
        """Return sorted names of stations served by ``line``."""
        canonical = self.resolve_line(line)
        if canonical is None:
            return []
        numbers = set()
        for edge in self.graph.edges():
            if edge.line == canonical:
                numbers.add(edge.source)
                numbers.add(edge.dest)
        names = {self.number_to_name[n] for n in numbers}
        names.update(
            name for name, lines in self.graph.station_lines.items() if canonical in lines
        )
        return sorted(names)

    def edge_count(self) -> int:
        """Return the number of connections in the network."""
        return self.graph.edge_count()

    # ----- data update operations ---------------------------------------
    def add_line(self, line_name: Any, stations: List[Any], distances: List[Any]) -> int:
        """Add a new subway line as an ordered sequence of stations.

        Existing stations are reused (the new line is added to their line
        list); unknown stations are created.

        Args:
            line_name: name of the new line.
            stations: ordered list of station names on the line (at least 2).
            distances: distances in meters between consecutive stations
                (length must be ``len(stations) - 1``).

        Returns:
            Number of connections added.

        Raises:
            ValueError: on duplicate line names or invalid input.
        """
        name = normalize_name(line_name)
        if not name:
            raise ValueError("Line name must not be empty")
        if self.resolve_line(name) is not None:
            raise ValueError(f"Line '{name}' already exists")
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must equal number of stations minus one")

        validated = [self._validate_distance(d) for d in distances]
        canonical_names = []
        for station in stations:
            canonical = self.resolve_station(station) or normalize_name(station)
            canonical_names.append(canonical)
            self._add_station(canonical, [name])

        for index, distance in enumerate(validated):
            a = self.station_to_number[canonical_names[index]]
            b = self.station_to_number[canonical_names[index + 1]]
            self.graph.add_edge(Edge(a, b, distance, name))
        return len(validated)

    def update_distance(self, station_a: Any, station_b: Any, distance: Any,
                        line: Optional[str] = None) -> int:
        """Update the distance of the connection(s) between two stations.

        Args:
            station_a: first station name.
            station_b: second station name.
            distance: new distance in meters (positive).
            line: optionally restrict the update to connections of this line.

        Returns:
            Number of connections updated.

        Raises:
            UnknownStationError: if a station does not exist.
            ValueError: if no matching connection exists or distance is invalid.
        """
        new_distance = self._validate_distance(distance)
        a = self.number_of(station_a)
        b = self.number_of(station_b)
        updated = 0
        for edge in self.graph.neighbors(a):
            if edge.other(a) == b and (line is None or edge.line == line):
                edge.distance = new_distance
                updated += 1
        if updated == 0:
            raise ValueError(
                f"No connection between '{station_a}' and '{station_b}'"
                + (f" on line '{line}'" if line else "")
            )
        return updated

    def modify_station(self, old_name: Any, new_name: Optional[str] = None,
                       lines: Optional[List[str]] = None) -> str:
        """Rename a station and/or replace its line affiliations.

        Returns:
            The canonical name of the station after modification.

        Raises:
            UnknownStationError: if ``old_name`` does not exist.
            ValueError: if the new name is already used by another station.
        """
        canonical = self.resolve_station(old_name)
        if canonical is None:
            raise UnknownStationError(f"Station '{old_name}' does not exist")

        if new_name is not None:
            target = normalize_name(new_name)
            if not target:
                raise ValueError("New station name must not be empty")
            if target != canonical:
                existing = self.resolve_station(target)
                if existing is not None and existing != canonical:
                    raise ValueError(f"Station '{existing}' already exists")
                number = self.station_to_number.pop(canonical)
                self.station_to_number[target] = number
                self.number_to_name[number] = target
                self._fold_index.pop(canonical.casefold(), None)
                self._fold_index[target.casefold()] = target
                self.graph.station_lines[target] = self.graph.station_lines.pop(canonical, [])
                canonical = target

        if lines is not None:
            self.graph.set_station_lines(canonical, [normalize_name(l) for l in lines])
        return canonical
