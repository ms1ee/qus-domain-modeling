"""Subway network model: stations, lines and connections.

``SubwayNetwork`` owns the station-number mapping (``station_to_number``),
the weighted undirected graph (``graph``) and provides lookup, validation and
data-update operations.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from errors import DataError, StationNotFoundError
from models import Edge, Graph


def normalize_station_name(name: str) -> str:
    """Normalise a station name for case- and whitespace-insensitive matching."""
    return " ".join(str(name).split()).casefold()


def _clean_name(name: str, what: str) -> str:
    cleaned = " ".join(str(name).split())
    if not cleaned:
        raise DataError(f"{what} must not be empty")
    return cleaned


def _validate_distance(distance: Any) -> int:
    if isinstance(distance, bool):
        raise DataError("distance must be a positive integer number of metres")
    if isinstance(distance, float) and distance.is_integer():
        distance = int(distance)
    if not isinstance(distance, int) or distance <= 0:
        raise DataError("distance must be a positive integer number of metres")
    return distance


class SubwayNetwork:
    """Container for the Beijing Subway network."""

    def __init__(self) -> None:
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.graph = Graph()
        self.issues: List[str] = []  # problems found while building the network
        self._normalized: Dict[str, str] = {}
        self._next_number = 0

    # ------------------------------------------------------------------ lookup
    def station_names(self) -> List[str]:
        return list(self.station_to_number)

    def standardize_name(self, raw: str) -> Optional[str]:
        """Return the official station name matching ``raw``, or None."""
        return self._normalized.get(normalize_station_name(raw))

    def station_exists(self, raw: str) -> bool:
        return self.standardize_name(raw) is not None

    def require_station(self, raw: str, role: str = "Target") -> str:
        """Return the official name for ``raw`` or raise ``StationNotFoundError``."""
        name = self.standardize_name(raw)
        if name is None:
            raise StationNotFoundError(str(raw).strip(), role)
        return name

    def number_of(self, name: str) -> int:
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        return self.number_to_station[number]

    def lines_of(self, name: str) -> List[str]:
        return self.graph.get_station_lines(name)

    def connection_line_names(self) -> List[str]:
        """Names of all lines that have at least one connection."""
        return list(dict.fromkeys(e.line for e in self.graph.edges()))

    def line_names(self) -> List[str]:
        """Names of all lines known from station data or connections."""
        names: Dict[str, None] = {}
        for lines in self.graph.station_lines.values():
            for line in lines:
                names.setdefault(line, None)
        for edge in self.graph.edges():
            names.setdefault(edge.line, None)
        return list(names)

    def stations_on_line(self, line: str) -> List[str]:
        """Stations served by ``line`` (from connections or station data)."""
        names: Dict[str, None] = {}
        for edge in self.graph.edges():
            if edge.line == line:
                names.setdefault(self.name_of(edge.source), None)
                names.setdefault(self.name_of(edge.dest), None)
        for name, lines in self.graph.station_lines.items():
            if line in lines:
                names.setdefault(name, None)
        return list(names)

    def connections(self) -> List[Edge]:
        return self.graph.edges()

    # ---------------------------------------------------------------- updates
    def _merge_lines(self, name: str, lines: Iterable[str]) -> None:
        current = self.graph.get_station_lines(name)
        for line in lines:
            if line and line not in current:
                current.append(line)
        self.graph.set_station_lines(name, current)

    def add_station(self, name: str, lines: Iterable[str] = ()) -> int:
        """Add a station (or merge lines into an existing one); return its number."""
        clean = _clean_name(name, "station name")
        key = normalize_station_name(clean)
        if key in self._normalized:
            existing = self._normalized[key]
            self._merge_lines(existing, lines)
            return self.station_to_number[existing]

        number = self._next_number
        self._next_number += 1
        self.station_to_number[clean] = number
        self.number_to_station[number] = clean
        self._normalized[key] = clean
        self.graph.add_vertex(number)
        self.graph.set_station_lines(clean, [])
        self._merge_lines(clean, lines)
        return number

    def add_connection(
        self, source_name: str, dest_name: str, distance: Any, line: str
    ) -> Edge:
        """Add an undirected connection between two existing stations."""
        source = self.require_station(source_name, "Starting")
        dest = self.require_station(dest_name, "Ending")
        if source == dest:
            raise DataError(f"station '{source}' cannot connect to itself")
        metres = _validate_distance(distance)
        if not str(line).strip():
            raise DataError("connection line must not be empty")
        a, b = self.number_of(source), self.number_of(dest)
        if self.graph.edges_between(a, b, line):
            raise DataError(
                f"duplicate connection between '{source}' and '{dest}' on '{line}'"
            )
        edge = Edge(a, b, metres, line)
        self.graph.add_edge(edge)
        return edge

    def add_line(
        self, line_name: str, station_names: Sequence[str], distances: Sequence[Any]
    ) -> List[Edge]:
        """Add a new line from an ordered list of stations and segment distances."""
        line = _clean_name(line_name, "line name")
        if line in self.line_names():
            raise DataError(f"line '{line}' already exists")
        if len(station_names) < 2:
            raise DataError("a line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise DataError("number of distances must equal number of stations - 1")
        checked = [_validate_distance(d) for d in distances]

        for name in station_names:
            self.add_station(name, [line])
        edges = []
        for i, metres in enumerate(checked):
            edges.append(
                self.add_connection(station_names[i], station_names[i + 1], metres, line)
            )
        return edges

    def update_station(
        self,
        name: str,
        new_name: Optional[str] = None,
        lines: Optional[Sequence[str]] = None,
    ) -> str:
        """Rename a station and/or replace its line list. Returns the final name."""
        current = self.require_station(name)
        if new_name is not None:
            clean = _clean_name(new_name, "station name")
            new_key = normalize_station_name(clean)
            old_key = normalize_station_name(current)
            if new_key != old_key and new_key in self._normalized:
                raise DataError(f"station '{clean}' already exists")
            number = self.station_to_number.pop(current)
            self._normalized.pop(old_key, None)
            station_lines = self.graph.station_lines.pop(current)
            self.station_to_number[clean] = number
            self.number_to_station[number] = clean
            self._normalized[new_key] = clean
            self.graph.station_lines[clean] = station_lines
            current = clean
        if lines is not None:
            cleaned = [str(x).strip() for x in lines if str(x).strip()]
            self.graph.set_station_lines(current, list(dict.fromkeys(cleaned)))
        return current

    def update_distance(
        self, source_name: str, dest_name: str, distance: Any, line: Optional[str] = None
    ) -> int:
        """Update the distance of connection(s) between two stations.

        Returns the number of connections updated.
        """
        a = self.number_of(self.require_station(source_name, "Starting"))
        b = self.number_of(self.require_station(dest_name, "Ending"))
        metres = _validate_distance(distance)
        edges = self.graph.edges_between(a, b, line)
        if not edges:
            raise DataError(
                f"no connection between '{source_name}' and '{dest_name}'"
                + (f" on line '{line}'" if line else "")
            )
        for edge in edges:
            edge.distance = metres
        return len(edges)


def build_network(data: Dict[str, Any]) -> SubwayNetwork:
    """Build a ``SubwayNetwork`` from the parsed subway data dictionary.

    Malformed or inconsistent entries are skipped and recorded in
    ``network.issues`` so that the integrity check can report them.
    """
    if not isinstance(data, dict):
        raise DataError("subway data must be a dictionary")

    network = SubwayNetwork()
    stations = data.get("stations", [])
    connections = data.get("connections", [])
    if not isinstance(stations, list) or not isinstance(connections, list):
        raise DataError("'stations' and 'connections' must be lists")

    for index, entry in enumerate(stations):
        if not isinstance(entry, dict) or "name" not in entry:
            network.issues.append(f"station entry #{index} is malformed and was skipped")
            continue
        raw_lines = entry.get("lines", [])
        if not isinstance(raw_lines, list):
            network.issues.append(f"station '{entry['name']}' has invalid line list")
            raw_lines = []
        try:
            network.add_station(str(entry["name"]), [str(x) for x in raw_lines])
        except DataError as exc:
            network.issues.append(f"station entry #{index} skipped: {exc}")

    for index, entry in enumerate(connections):
        if not isinstance(entry, dict):
            network.issues.append(f"connection #{index} is malformed and was skipped")
            continue
        try:
            source = str(entry["source"])
            dest = str(entry["dest"])
            line = str(entry["line"])
            distance = _validate_distance(entry["distance"])
        except (KeyError, DataError) as exc:
            network.issues.append(f"connection #{index} skipped: {exc}")
            continue

        for name in (source, dest):
            if not network.station_exists(name):
                network.issues.append(
                    f"connection #{index}: station '{name}' is not declared in stations"
                )
                try:
                    network.add_station(name, [])
                except DataError as exc:
                    network.issues.append(f"connection #{index} skipped: {exc}")
                    break
        else:
            try:
                network.add_connection(source, dest, distance, line)
            except DataError as exc:
                network.issues.append(f"connection #{index} skipped: {exc}")

    return network


def network_to_data(network: SubwayNetwork) -> Dict[str, Any]:
    """Export the network back into the ``subway_data.json`` schema."""
    stations = [
        {"name": name, "lines": network.lines_of(name)}
        for name in network.station_to_number
    ]
    connections = [
        {
            "source": network.name_of(e.source),
            "dest": network.name_of(e.dest),
            "distance": e.distance,
            "line": e.line,
        }
        for e in network.graph.edges()
    ]
    return {"stations": stations, "connections": connections}
