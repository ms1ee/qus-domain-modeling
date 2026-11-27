"""Graph data models for the Beijing Subway network.

The network is a weighted undirected graph. Station numbers (integers) are
assigned by the caller (see ``network.build_graph``); the ``Graph`` class only
stores and looks them up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass(frozen=True)
class Edge:
    """An undirected connection between two stations on one line.

    Attributes:
        source: Station number of one endpoint.
        dest: Station number of the other endpoint.
        distance: Physical distance in meters (used as the edge weight).
        line: Name of the subway line operating this connection.
    """

    source: int
    dest: int
    distance: float
    line: str

    @property
    def weight(self) -> float:
        """Edge weight used by path algorithms (equal to the distance)."""
        return self.distance

    def other(self, vertex: int) -> int:
        """Return the endpoint opposite to ``vertex``.

        Raises:
            ValueError: If ``vertex`` is not an endpoint of this edge.
        """
        if vertex == self.source:
            return self.dest
        if vertex == self.dest:
            return self.source
        raise ValueError(f"Vertex {vertex} is not an endpoint of this edge")


@dataclass
class Station:
    """Descriptive information about a station."""

    station_id: str
    name: str
    is_transfer_station: bool = False


@dataclass(frozen=True)
class Transfer:
    """A line change performed at a station."""

    station_name: str
    from_line: str
    to_line: str


@dataclass(frozen=True)
class PathSegment:
    """A continuous run of stations on a single line."""

    start_station: str
    end_station: str
    distance_m: float
    line: str


class Graph:
    """Weighted undirected graph of subway stations.

    Attributes:
        station_to_number: Mapping from station name to station number.
        number_to_station: Mapping from station number to station name.
        station_lines: Mapping from station name to the lines serving it.
        adjacency: Mapping from station number to incident edges.
    """

    def __init__(self) -> None:
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self.station_lines: Dict[str, List[str]] = {}
        self.adjacency: Dict[int, List[Edge]] = {}

    # ------------------------------------------------------------------ #
    # Station management
    # ------------------------------------------------------------------ #
    def register_station(self, name: str, number: int) -> None:
        """Register a station with a caller-assigned number.

        Raises:
            ValueError: On empty/duplicate names or duplicate numbers.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Station name must be a non-empty string")
        if name in self.station_to_number:
            raise ValueError(f"Duplicate station name: {name}")
        if number in self.number_to_station:
            raise ValueError(f"Duplicate station number: {number}")
        self.station_to_number[name] = number
        self.number_to_station[number] = name
        self.station_lines[name] = []
        self.adjacency[number] = []

    def set_station_lines(self, station_name: str, lines: List[str]) -> None:
        """Set the (de-duplicated, ordered) lines serving a station.

        Raises:
            KeyError: If the station is unknown.
        """
        if station_name not in self.station_to_number:
            raise KeyError(f"Unknown station: {station_name}")
        cleaned = [line for line in lines if isinstance(line, str) and line.strip()]
        self.station_lines[station_name] = list(dict.fromkeys(cleaned))

    def has_station(self, name: str) -> bool:
        """Return True if a station with this name exists."""
        return name in self.station_to_number

    def number_of(self, name: str) -> int:
        """Return the station number for a station name.

        Raises:
            KeyError: If the station is unknown.
        """
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise KeyError(f"Unknown station: {name}") from exc

    def name_of(self, number: int) -> str:
        """Return the station name for a station number.

        Raises:
            KeyError: If the number is unknown.
        """
        try:
            return self.number_to_station[number]
        except KeyError as exc:
            raise KeyError(f"Unknown station number: {number}") from exc

    def get_station(self, name: str) -> Station:
        """Return descriptive information about a station."""
        number = self.number_of(name)
        lines = self.station_lines.get(name, [])
        return Station(
            station_id=str(number),
            name=name,
            is_transfer_station=len(lines) > 1,
        )

    def station_numbers(self) -> List[int]:
        """Return all station numbers in ascending order."""
        return sorted(self.number_to_station)

    # ------------------------------------------------------------------ #
    # Edge management
    # ------------------------------------------------------------------ #
    def add_edge(self, edge: Edge) -> None:
        """Add an undirected edge to the graph.

        Raises:
            ValueError: If the edge is a self loop.
            KeyError: If an endpoint station number is unknown.
        """
        if edge.source == edge.dest:
            raise ValueError("Self-loop edges are not allowed")
        for vertex in (edge.source, edge.dest):
            if vertex not in self.adjacency:
                raise KeyError(f"Unknown station number: {vertex}")
        self.adjacency[edge.source].append(edge)
        self.adjacency[edge.dest].append(edge)

    def neighbors(self, number: int) -> List[Edge]:
        """Return the edges incident to a station (treat as read-only)."""
        return self.adjacency.get(number, [])

    def edges(self) -> List[Edge]:
        """Return every edge exactly once."""
        result: List[Edge] = []
        for number, incident in self.adjacency.items():
            for edge in incident:
                if edge.source == number:
                    result.append(edge)
        return result

    def lines(self) -> List[str]:
        """Return the sorted set of all line names in the network."""
        names: Set[str] = set()
        for station_lines in self.station_lines.values():
            names.update(station_lines)
        for edge in self.edges():
            names.add(edge.line)
        return sorted(names)
