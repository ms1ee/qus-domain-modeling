"""Subway network modelling and data management.

``SubwayNetwork`` converts the JSON dataset into a ``Graph`` whose vertices are
station numbers, keeps the name/number mappings (``station_to_number``), and
offers data update and integrity-check operations.
"""

import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

from models import Edge, Graph

# Main lines that must be present in the dataset.
MAIN_LINES: List[str] = [
    "Line 1",
    "Line 2",
    "Line 4",
    "Line 5",
    "Line 6",
    "Line 8",
    "Line 10",
    "Line 13",
    "Line 14",
    "Line 15",
    "Changping Line",
    "Yizhuang Line",
    "Fangshan Line",
    "Airport Line",
]

# Representative stations expected on some main lines (used for coverage checks).
REPRESENTATIVE_STATIONS: Dict[str, List[str]] = {
    "Line 1": ["Pingguoyuan", "Tiananmen East"],
    "Line 2": ["Xizhimen", "Dongzhimen"],
    "Line 10": ["Shuangjing"],
}

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000

_DIGITS = re.compile(r"\d+")


def _normalize(text: str) -> str:
    """Lower-case and remove all whitespace."""
    return re.sub(r"\s+", "", text).lower()


def _station_key(text: str) -> str:
    """Normalized key used for station-name standardization."""
    key = _normalize(text)
    if key.endswith("站"):
        key = key[:-1]
    return key


def _line_sort_key(line: str):
    """Sort 'Line 2' before 'Line 10', and named lines after numbered lines."""
    match = _DIGITS.search(line)
    if match:
        return (0, int(match.group()), line)
    return (1, 0, line)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _count_components(nodes: Iterable[int], neighbors: Callable[[int], Iterable[int]]) -> int:
    """Count connected components among ``nodes`` using ``neighbors``."""
    visited: Set[int] = set()
    count = 0
    for start in nodes:
        if start in visited:
            continue
        count += 1
        visited.add(start)
        stack = [start]
        while stack:
            current = stack.pop()
            for nxt in neighbors(current):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
    return count


class SubwayNetwork:
    """In-memory model of the subway network.

    Attributes:
        graph: Weighted undirected ``Graph`` keyed by station numbers.
        station_to_number: Mapping from official station name to station number.
        number_to_station: Reverse mapping from station number to name.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self.graph = Graph()
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self._line_stations: Dict[str, Set[str]] = {}
        self._next_number = 0
        if data is not None:
            self._load(data)

    # ----- loading ---------------------------------------------------------
    def _load(self, data: Dict[str, Any]) -> None:
        """Populate the network from a parsed dataset."""
        if not isinstance(data, dict):
            raise ValueError("Subway data must be a JSON object")
        stations = data.get("stations")
        connections = data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise ValueError("Subway data must contain 'stations' and 'connections' lists")

        for entry in stations:
            if not isinstance(entry, dict):
                raise ValueError("Each station entry must be an object")
            name = entry.get("name")
            lines = entry.get("lines", [])
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Every station needs a non-empty 'name'")
            if not isinstance(lines, list) or not all(isinstance(l, str) for l in lines):
                raise ValueError(f"Station '{name}' has an invalid 'lines' value")
            self.add_station(name, lines)

        for entry in connections:
            if not isinstance(entry, dict):
                raise ValueError("Each connection entry must be an object")
            try:
                self.add_connection(
                    entry["source"], entry["dest"], entry["distance"], entry["line"]
                )
            except KeyError as exc:
                raise ValueError(f"Connection entry is missing field {exc}") from exc

    # ----- internal helpers ------------------------------------------------
    def _require_number(self, name: str) -> int:
        """Return the station number for an exact official name."""
        if not isinstance(name, str) or name.strip() not in self.station_to_number:
            raise ValueError(f"Unknown station '{name}'")
        return self.station_to_number[name.strip()]

    def _index_line(self, line: str, *station_names: str) -> None:
        self._line_stations.setdefault(line, set()).update(station_names)

    def _rebuild_line_index(self) -> None:
        """Recompute the line -> stations index from graph data."""
        self._line_stations = {}
        for name in self.station_to_number:
            for line in self.graph.get_station_lines(name):
                self._index_line(line, name)
        for edge in self.graph.edges():
            self._index_line(
                edge.line,
                self.number_to_station[edge.source],
                self.number_to_station[edge.dest],
            )

    # ----- station and connection management -------------------------------
    def add_station(self, name: str, lines: Sequence[str] = ()) -> int:
        """Add a station (or merge lines into an existing one).

        Returns:
            The station number.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Station name must be a non-empty string")
        name = name.strip()
        clean_lines = list(dict.fromkeys(l.strip() for l in lines if l and l.strip()))

        if name in self.station_to_number:
            number = self.station_to_number[name]
            current = self.graph.get_station_lines(name)
            for line in clean_lines:
                if line not in current:
                    current.append(line)
            self.graph.set_station_lines(name, current)
        else:
            number = self._next_number
            self._next_number += 1
            self.graph.add_node(number)
            self.graph.set_station_lines(name, clean_lines)
            self.station_to_number[name] = number
            self.number_to_station[number] = name

        for line in clean_lines:
            self._index_line(line, name)
        return number

    def add_connection(self, source: str, dest: str, distance, line: str) -> bool:
        """Add a connection between two existing stations.

        Returns:
            True if added, False if an identical connection already exists.
        """
        u = self._require_number(source)
        v = self._require_number(dest)
        if u == v:
            raise ValueError("A connection cannot join a station to itself")
        if not _is_number(distance) or distance <= 0:
            raise ValueError(f"Invalid distance {distance!r} for connection")
        if not isinstance(line, str) or not line.strip():
            raise ValueError("Connection line must be a non-empty string")
        line = line.strip()
        if self.graph.find_edges(u, v, line):
            return False
        self.graph.add_edge(Edge(u, v, distance, line))
        self._index_line(line, self.number_to_station[u], self.number_to_station[v])
        return True

    def add_line(self, line_name: str, station_names: Sequence[str], distances: Sequence[float]) -> None:
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered station names; unknown names are created.
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent.
        """
        if not isinstance(line_name, str) or not line_name.strip():
            raise ValueError("Line name must be a non-empty string")
        name = line_name.strip()
        if self.resolve_line(name) is not None:
            raise ValueError(f"Line '{name}' already exists")

        stations = [s.strip() if isinstance(s, str) else "" for s in station_names]
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if any(not s for s in stations):
            raise ValueError("Station names must be non-empty")
        if len(set(stations)) != len(stations):
            raise ValueError("A line cannot contain duplicate stations")
        if len(distances) != len(stations) - 1:
            raise ValueError("Expected one distance per pair of consecutive stations")
        for distance in distances:
            if not _is_number(distance) or distance <= 0:
                raise ValueError(f"Invalid distance {distance!r}")

        for station in stations:
            self.add_station(station, [name])
        for index, distance in enumerate(distances):
            self.add_connection(stations[index], stations[index + 1], distance, name)

    def modify_station(self, name: str, new_name: Optional[str] = None,
                       lines: Optional[Sequence[str]] = None) -> str:
        """Rename a station and/or replace its list of lines.

        Returns:
            The final station name.
        """
        number = self._require_number(name)
        old = self.number_to_station[number]
        final = old
        if new_name is not None:
            candidate = new_name.strip() if isinstance(new_name, str) else ""
            if not candidate:
                raise ValueError("New station name must be a non-empty string")
            if candidate != old and candidate in self.station_to_number:
                raise ValueError(f"Station '{candidate}' already exists")
            final = candidate
        if lines is not None:
            if not all(isinstance(l, str) for l in lines):
                raise ValueError("Lines must be a list of strings")
            new_lines = list(dict.fromkeys(l.strip() for l in lines if l.strip()))
        else:
            new_lines = self.graph.get_station_lines(old)

        if final != old:
            del self.station_to_number[old]
            self.station_to_number[final] = number
            self.number_to_station[number] = final
            self.graph.station_lines.pop(old, None)
        self.graph.set_station_lines(final, new_lines)
        self._rebuild_line_index()
        return final

    def update_distance(self, source: str, dest: str, distance, line: Optional[str] = None) -> int:
        """Update the distance of the connection(s) between two stations.

        Returns:
            The number of connections updated.

        Raises:
            ValueError: If no connection exists, the distance is invalid, or the
                pair is connected by several lines and ``line`` was not given.
        """
        u = self._require_number(source)
        v = self._require_number(dest)
        if not _is_number(distance) or distance <= 0:
            raise ValueError(f"Invalid distance {distance!r}")
        edges = self.graph.find_edges(u, v, line.strip() if line else None)
        if not edges:
            raise ValueError(f"No connection between '{source}' and '{dest}'")
        if line is None and len({e.line for e in edges}) > 1:
            raise ValueError("Several lines connect these stations; specify the line")
        for edge in edges:
            edge.distance = distance
        return len(edges)

    def resolve_station(self, name: str) -> Optional[str]:
        """Standardize a user-entered station name to its official form.

        Matching ignores case, whitespace and a trailing '站'.

        Returns:
            The official name, or None if no unique match exists.
        """
        if not isinstance(name, str):
            return None
        stripped = name.strip()
        if stripped in self.station_to_number:
            return stripped
        key = _station_key(stripped)
        if not key:
            return None
        matches = [official for official in self.station_to_number if _station_key(official) == key]
        return matches[0] if len(matches) == 1 else None

    def resolve_line(self, name: str) -> Optional[str]:
        """Standardize a user-entered line name, or return None if unknown."""
        if not isinstance(name, str):
            return None
        stripped = name.strip()
        if stripped in self._line_stations:
            return stripped
        key = _normalize(stripped)
        matches = [line for line in self._line_stations if _normalize(line) == key]
        return matches[0] if len(matches) == 1 else None

    def has_station(self, name: str) -> bool:
        """Return True if the exact official name exists."""
        return isinstance(name, str) and name.strip() in self.station_to_number

    def station_number(self, name: str) -> int:
        """Return the station number for an official name."""
        return self._require_number(name)

    def station_name(self, number: int) -> str:
        """Return the official name for a station number."""
        return self.number_to_station[number]

    def station_names(self) -> List[str]:
        """Return all official station names, sorted."""
        return sorted(self.station_to_number)

    def line_names(self) -> List[str]:
        """Return all line names in natural order."""
        return sorted(self._line_stations, key=_line_sort_key)

    def line_station_names(self, line: str) -> List[str]:
        """Return the sorted names of stations served by a line."""
        return sorted(self._line_stations.get(line, set()))

    def lines_of_station(self, name: str) -> List[str]:
        """Return the lines serving a station."""
        return self.graph.get_station_lines(self._require_number_name(name))

    def is_transfer_station(self, name: str) -> bool:
        """Return True if a station is served by more than one line."""
        return len(self.lines_of_station(name)) > 1

    def _require_number_name(self, name: str) -> str:
        self._require_number(name)
        return name.strip()

    # ----- data integrity --------------------------------------------------
    def check_integrity(
        self,
        required_lines: Optional[Sequence[str]] = None,
        representative_stations: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """Run data integrity checks.

        Checks station coverage of main lines and representative stations,
        station line assignments, connection consistency, distance accuracy and
        line/network connectivity.

        Returns:
            A list of human-readable issue descriptions (empty if healthy).
        """
        required = MAIN_LINES if required_lines is None else list(required_lines)
        representative = (
            REPRESENTATIVE_STATIONS if representative_stations is None else representative_stations
        )
        issues: List[str] = []

        # Coverage of main lines.
        known_lines = set(self._line_stations)
        for line in required:
            if line not in known_lines:
                issues.append(f"Coverage: main line '{line}' is missing")
            elif len(self._line_stations[line]) < 2:
                issues.append(f"Coverage: main line '{line}' has fewer than 2 stations")

        # Representative stations.
        for line, stations in representative.items():
            for station in stations:
                if station not in self.station_to_number:
                    issues.append(f"Coverage: representative station '{station}' of {line} is missing")
                elif line not in self.graph.get_station_lines(station):
                    issues.append(f"Coverage: station '{station}' is not listed on {line}")

        # Station data.
        for name in sorted(self.station_to_number):
            if not self.graph.get_station_lines(name):
                issues.append(f"Station data: '{name}' has no line assignment")

        # Connection integrity and distance accuracy.
        for edge in self.graph.edges():
            a = self.number_to_station[edge.source]
            b = self.number_to_station[edge.dest]
            label = f"{a} - {b} ({edge.line})"
            for end in (a, b):
                if edge.line not in self.graph.get_station_lines(end):
                    issues.append(f"Connection: '{end}' is not listed on the line of {label}")
            if not _is_number(edge.distance) or edge.distance <= 0:
                issues.append(f"Distance: {label} has invalid distance {edge.distance!r}")
            elif not MIN_PLAUSIBLE_DISTANCE_M <= edge.distance <= MAX_PLAUSIBLE_DISTANCE_M:
                issues.append(
                    f"Distance: {label} distance {edge.distance} m is outside the plausible range"
                )

        # Per-line connectivity.
        for line in self.line_names():
            numbers = [self.station_to_number[s] for s in self.line_station_names(line)]
            count = _count_components(
                numbers,
                lambda n, ln=line: [e.other(n) for e in self.graph.adj(n) if e.line == ln],
            )
            if count > 1:
                issues.append(f"Connectivity: {line} is split into {count} disconnected segments")

        # Whole-network connectivity.
        all_nodes = self.graph.nodes()
        if all_nodes:
            count = _count_components(all_nodes, lambda n: [e.other(n) for e in self.graph.adj(n)])
            if count > 1:
                issues.append(f"Connectivity: network is split into {count} disconnected components")

        return issues

    def to_data(self) -> Dict[str, Any]:
        """Export the current network in the dataset JSON structure."""
        stations = [
            {"name": name, "lines": self.graph.get_station_lines(name)}
            for name in sorted(self.station_to_number)
        ]
        connections = [
            {
                "source": self.number_to_station[edge.source],
                "dest": self.number_to_station[edge.dest],
                "distance": edge.distance,
                "line": edge.line,
            }
            for edge in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}
