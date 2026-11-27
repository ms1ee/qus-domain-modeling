"""Subway network modelling: station numbering, graph construction, lines,
transfer stations, station name resolution and data update operations."""

import copy
import difflib
import re
from typing import Dict, List, Optional, Tuple

from .data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from .models import Edge, Graph

# Average time spent on each transfer, in minutes.
TRANSFER_TIME_MINUTES = 5.0


def _normalize(text: str) -> str:
    """Normalise a station or line name for lenient matching."""
    return re.sub(r"[\s\-_·'’]+", "", str(text)).lower()


def _append_unique(items: List[str], value: str) -> None:
    """Append a value to a list only if it is not already present."""
    if value not in items:
        items.append(value)


def _order_line(adjacency: Dict[str, set]) -> List[str]:
    """Order the stations of one line by walking its undirected adjacency.

    Starts from an endpoint (a station with at most one neighbour) and follows
    unvisited neighbours. Any stations not reached by the walk (e.g. branches)
    are appended in sorted order.
    """
    if not adjacency:
        return []
    ends = sorted(n for n, nb in adjacency.items() if len(nb) <= 1)
    current: Optional[str] = ends[0] if ends else sorted(adjacency)[0]
    ordered: List[str] = []
    visited = set()
    while current is not None and current not in visited:
        ordered.append(current)
        visited.add(current)
        nxt = [n for n in sorted(adjacency[current]) if n not in visited]
        current = nxt[0] if nxt else None
    for name in sorted(adjacency):
        if name not in visited:
            ordered.append(name)
    return ordered


class SubwayNetwork:
    """In-memory model of the Beijing Subway network.

    The network is built from the raw dataset dictionary. Station numbers are
    assigned here (in first-seen order) and used as graph vertex identifiers.
    After any data update the graph is rebuilt.
    """

    def __init__(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise ValueError("subway data must be a dictionary")
        self._raw = copy.deepcopy(data)
        for key in ("stations", "connections"):
            if not isinstance(self._raw.get(key), list):
                raise ValueError(f"subway data is missing the '{key}' list")
        self.station_to_number: Dict[str, int] = {}
        self.number_to_name: Dict[int, str] = {}
        self.graph = Graph()
        self.lines: Dict[str, List[str]] = {}
        self._normalized_index: Dict[str, str] = {}
        self._build()

    @classmethod
    def from_file(cls, path: str = DATA_FILE_PATH) -> "SubwayNetwork":
        """Create a network from the JSON data file."""
        return cls(load_subway_data(path))

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _register(self, name: str) -> int:
        """Assign a number to a station name if it has none yet."""
        if name not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self._normalized_index.setdefault(_normalize(name), name)
        return self.station_to_number[name]

    def _build(self) -> None:
        """(Re)build station numbers, graph, line sequences from raw data."""
        stations = self._raw["stations"]
        connections = self._raw["connections"]

        self.station_to_number = {}
        self.number_to_name = {}
        self._normalized_index = {}
        self.graph = Graph()
        self.lines = {}

        for st in stations:
            self._register(st["name"])
        for conn in connections:
            self._register(conn["source"])
            self._register(conn["dest"])

        # Station -> lines, combining declared lines and connection lines.
        station_lines: Dict[str, List[str]] = {name: [] for name in self.station_to_number}
        for st in stations:
            for line in st.get("lines", []):
                _append_unique(station_lines[st["name"]], line)
        for conn in connections:
            for end in (conn["source"], conn["dest"]):
                _append_unique(station_lines[end], conn["line"])
        for name, lines in station_lines.items():
            self.graph.set_station_lines(name, lines)

        for number in self.number_to_name:
            self.graph.add_vertex(number)
        for conn in connections:
            self.graph.add_edge(
                Edge(
                    self.station_to_number[conn["source"]],
                    self.station_to_number[conn["dest"]],
                    float(conn["distance"]),
                    conn["line"],
                )
            )

        # Line station sequences derived from the connection topology.
        line_adjacency: Dict[str, Dict[str, set]] = {}
        for conn in connections:
            adj = line_adjacency.setdefault(conn["line"], {})
            adj.setdefault(conn["source"], set()).add(conn["dest"])
            adj.setdefault(conn["dest"], set()).add(conn["source"])
        for line, adj in line_adjacency.items():
            self.lines[line] = _order_line(adj)
        for name, lines in station_lines.items():
            for line in lines:
                sequence = self.lines.setdefault(line, [])
                if name not in sequence:
                    sequence.append(name)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_station(self, name: str) -> bool:
        """Return True if the exact station name exists."""
        return name in self.station_to_number

    def station_number(self, name: str) -> int:
        """Return the number assigned to a station name.

        Raises:
            ValueError: If the station is unknown.
        """
        if name not in self.station_to_number:
            raise ValueError(f"Unknown station: '{name}'")
        return self.station_to_number[name]

    def station_name(self, number: int) -> str:
        """Return the station name for a station number."""
        return self.number_to_name[number]

    def station_names(self) -> List[str]:
        """Return all station names in numbering order."""
        return list(self.station_to_number)

    def line_names(self) -> List[str]:
        """Return all line names, sorted."""
        return sorted(self.lines)

    def stations_on_line(self, line: str) -> List[str]:
        """Return the ordered station names of a line."""
        return list(self.lines.get(line, []))

    def lines_of_station(self, name: str) -> List[str]:
        """Return the line names serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def transfer_stations(self) -> Dict[str, List[str]]:
        """Return interchange stations (served by two or more lines)."""
        return {
            name: list(lines)
            for name, lines in self.graph.station_lines.items()
            if len(lines) >= 2
        }

    def transfer_time_minutes(self) -> float:
        """Return the assumed time for one transfer in minutes."""
        return TRANSFER_TIME_MINUTES

    def resolve_station(self, text: str) -> Optional[Tuple[str, bool]]:
        """Standardise a user-entered station name.

        Returns:
            (official name, exact) where ``exact`` is False when the input was
            matched to the nearest station by fuzzy matching, or None when no
            reasonable match exists.
        """
        text = str(text).strip()
        if not text:
            return None
        if text in self.station_to_number:
            return text, True
        key = _normalize(text)
        if key in self._normalized_index:
            return self._normalized_index[key], True
        matches = difflib.get_close_matches(
            key, list(self._normalized_index), n=1, cutoff=0.5
        )
        if matches:
            return self._normalized_index[matches[0]], False
        return None

    def raw_data(self) -> dict:
        """Return a deep copy of the raw dataset dictionary."""
        return copy.deepcopy(self._raw)

    def save(self, path: str = DATA_FILE_PATH) -> None:
        """Persist the current dataset to a JSON file."""
        save_subway_data(self._raw, path)

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(
        self,
        line_name: str,
        station_names: List[str],
        distances: List[float],
        bidirectional: bool = True,
    ) -> None:
        """Add a new line made of consecutive stations.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names of the line.
            distances: Distances in meters between consecutive stations.
            bidirectional: If True, both travel directions are added.

        Raises:
            ValueError: If the input is inconsistent or the line exists.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self.lines:
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(set(station_names)) != len(station_names):
            raise ValueError("a line cannot contain duplicate stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have one entry per adjacent station pair")
        if any(d <= 0 for d in distances):
            raise ValueError("distances must be positive")

        stations = self._raw["stations"]
        by_name = {st["name"]: st for st in stations}
        for name in station_names:
            if name in by_name:
                lines = by_name[name].setdefault("lines", [])
                _append_unique(lines, line_name)
            else:
                new_station = {"name": name, "lines": [line_name]}
                stations.append(new_station)
                by_name[name] = new_station

        connections = self._raw["connections"]
        for i, distance in enumerate(distances):
            a, b = station_names[i], station_names[i + 1]
            connections.append(
                {"source": a, "dest": b, "distance": int(distance), "line": line_name}
            )
            if bidirectional:
                connections.append(
                    {"source": b, "dest": a, "distance": int(distance), "line": line_name}
                )
        self._build()

    def modify_station(
        self,
        name: str,
        new_name: Optional[str] = None,
        lines: Optional[List[str]] = None,
    ) -> None:
        """Rename a station and/or replace its line list.

        Raises:
            ValueError: If the station does not exist or the new name is taken.
        """
        stations = self._raw["stations"]
        target = next((st for st in stations if st["name"] == name), None)
        if target is None:
            raise ValueError(f"Unknown station: '{name}'")
        if new_name and new_name != name:
            if any(st["name"] == new_name for st in stations):
                raise ValueError(f"Station '{new_name}' already exists")
            target["name"] = new_name
            for conn in self._raw["connections"]:
                if conn["source"] == name:
                    conn["source"] = new_name
                if conn["dest"] == name:
                    conn["dest"] = new_name
        if lines is not None:
            target["lines"] = list(lines)
        self._build()

    def update_distance(self, station_a: str, station_b: str, distance: float) -> None:
        """Update the distance of every connection between two stations.

        Raises:
            ValueError: If no connection exists or the distance is invalid.
        """
        if distance <= 0:
            raise ValueError("distance must be positive")
        if station_a == station_b:
            raise ValueError("a station has no distance to itself")
        matched = 0
        for conn in self._raw["connections"]:
            if {conn["source"], conn["dest"]} == {station_a, station_b}:
                conn["distance"] = int(distance)
                matched += 1
        if matched == 0:
            raise ValueError(f"No connection between '{station_a}' and '{station_b}'")
        self._build()
