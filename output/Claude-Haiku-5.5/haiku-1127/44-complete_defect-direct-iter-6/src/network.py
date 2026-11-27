"""Builds the weighted subway graph from the raw dataset.

Assigns station numbers, creates the Graph, records line membership and
transfer stations, and provides official station-name standardization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models import Edge, Graph


class NetworkDataError(ValueError):
    """Raised when the raw dataset cannot be converted into a network."""


def _normalize_name(text: str) -> str:
    """Normalize a station name for lenient matching.

    Lower-cases, removes whitespace and strips trailing '站' characters so
    that e.g. 'Xizhimen station' style inputs in Chinese still match.
    """
    value = "".join(text.strip().lower().split())
    while value.endswith("站"):
        value = value[:-1]
    return value


@dataclass
class SubwayNetwork:
    """The fully built network used by path queries.

    Attributes:
        graph: weighted undirected graph keyed by station numbers.
        station_to_number: official station name -> station number.
        number_to_station: station number -> official station name.
        line_stations: line name -> names of stations served by that line.
        transfer_stations: names of stations served by more than one line.
        normalized_index: normalized name -> official name (for lenient lookup).
    """

    graph: Graph
    station_to_number: Dict[str, int]
    number_to_station: Dict[int, str]
    line_stations: Dict[str, List[str]]
    transfer_stations: List[str]
    normalized_index: Dict[str, str] = field(default_factory=dict)

    def number_of(self, name: str) -> int:
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def resolve_station(self, text: Any) -> Optional[str]:
        """Map user input to an official station name, or None if unknown."""
        if not isinstance(text, str):
            return None
        stripped = text.strip()
        if not stripped:
            return None
        if stripped in self.station_to_number:
            return stripped
        return self.normalized_index.get(_normalize_name(stripped))

    def line_names(self) -> List[str]:
        """Return all line names in the network."""
        return list(self.line_stations.keys())


def _require_str(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NetworkDataError(f"{what} must be a non-empty string")
    return value.strip()


def _require_distance(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NetworkDataError(f"{what} must be a number of meters")
    if value < 0:
        raise NetworkDataError(f"{what} must be non-negative")
    return int(round(value))


def build_network(data: Dict[str, Any]) -> SubwayNetwork:
    """Convert the raw subway dataset into a SubwayNetwork.

    Stations referenced only by connections are added automatically, and each
    connection's line is recorded on both of its endpoint stations.

    Raises:
        NetworkDataError: if the dataset is structurally invalid.
    """
    if not isinstance(data, dict):
        raise NetworkDataError("subway data must be a JSON object")
    stations_raw = data.get("stations")
    connections_raw = data.get("connections")
    if not isinstance(stations_raw, list):
        raise NetworkDataError("'stations' must be a list")
    if not isinstance(connections_raw, list):
        raise NetworkDataError("'connections' must be a list")

    # Station name -> ordered list of lines.
    station_lines: Dict[str, List[str]] = {}
    for index, entry in enumerate(stations_raw):
        if not isinstance(entry, dict):
            raise NetworkDataError(f"stations[{index}] must be an object")
        name = _require_str(entry.get("name"), f"stations[{index}].name")
        lines_raw = entry.get("lines", [])
        if not isinstance(lines_raw, list):
            raise NetworkDataError(f"stations[{index}].lines must be a list")
        bucket = station_lines.setdefault(name, [])
        for line in lines_raw:
            line_name = _require_str(line, f"stations[{index}] line")
            if line_name not in bucket:
                bucket.append(line_name)

    connections = []
    for index, entry in enumerate(connections_raw):
        if not isinstance(entry, dict):
            raise NetworkDataError(f"connections[{index}] must be an object")
        source = _require_str(entry.get("source"), f"connections[{index}].source")
        dest = _require_str(entry.get("dest"), f"connections[{index}].dest")
        distance = _require_distance(entry.get("distance"), f"connections[{index}].distance")
        line = _require_str(entry.get("line"), f"connections[{index}].line")
        if source == dest:
            raise NetworkDataError(f"connections[{index}] is a self-loop at '{source}'")
        connections.append((source, dest, distance, line))
        for name in (source, dest):
            bucket = station_lines.setdefault(name, [])
            if line not in bucket:
                bucket.append(line)

    # Assign station numbers in dataset order.
    station_to_number = {name: number for number, name in enumerate(station_lines)}
    number_to_station = {number: name for name, number in station_to_number.items()}

    graph = Graph()
    for name, number in station_to_number.items():
        graph.add_station(number)
        graph.set_station_lines(name, station_lines[name])

    line_stations: Dict[str, List[str]] = {}
    for source, dest, distance, line in connections:
        graph.add_edge(
            Edge(station_to_number[source], station_to_number[dest], distance, line)
        )
        members = line_stations.setdefault(line, [])
        for name in (source, dest):
            if name not in members:
                members.append(name)

    transfer_stations = [name for name, lines in station_lines.items() if len(lines) > 1]

    normalized_index: Dict[str, str] = {}
    for name in station_lines:
        normalized_index.setdefault(_normalize_name(name), name)

    return SubwayNetwork(
        graph=graph,
        station_to_number=station_to_number,
        number_to_station=number_to_station,
        line_stations=line_stations,
        transfer_stations=transfer_stations,
        normalized_index=normalized_index,
    )
