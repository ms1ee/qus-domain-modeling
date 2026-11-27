"""Subway network management.

This module converts the raw dataset into a graph model, maintains the
station-name/station-number mappings, supports data updates (adding lines,
modifying stations and distances) and performs data integrity checks.
"""

import copy
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Set

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Main lines that must be represented in the network.
REQUIRED_MAIN_LINES = (
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
)
MIN_STATIONS_PER_MAIN_LINE = 2
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


def normalize_name(name: str) -> str:
    """Normalize a station name for lenient matching (case and spaces ignored)."""
    return "".join(str(name).split()).lower()


class SubwayNetwork:
    """Holds the subway dataset, the derived graph and the name/number mappings.

    Attributes:
        data: Working copy of the dataset with 'stations' and 'connections'.
        graph: Graph built from the dataset (see models.Graph).
        station_to_number: Mapping official station name -> station number.
        number_to_station: Mapping station number -> official station name.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is None:
            data = load_subway_data(DATA_FILE_PATH)
        self.data: Dict[str, List[Dict[str, Any]]] = {
            "stations": copy.deepcopy(data.get("stations", [])),
            "connections": copy.deepcopy(data.get("connections", [])),
        }
        self.graph = Graph()
        self.station_to_number: Dict[str, int] = {}
        self.number_to_station: Dict[int, str] = {}
        self._normalized_index: Dict[str, str] = {}
        self.rebuild()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        """(Re)build the graph and the station mappings from the dataset."""
        graph = Graph()
        order: List[str] = []
        lines_by_station: Dict[str, List[str]] = {}

        def register(name: str, lines: Sequence[str]) -> None:
            if name not in lines_by_station:
                lines_by_station[name] = []
                order.append(name)
            for line in lines:
                if line not in lines_by_station[name]:
                    lines_by_station[name].append(line)

        for station in self.data["stations"]:
            register(station["name"], station.get("lines", []))
        for conn in self.data["connections"]:
            register(conn["source"], [conn["line"]])
            register(conn["dest"], [conn["line"]])

        station_to_number: Dict[str, int] = {}
        number_to_station: Dict[int, str] = {}
        normalized: Dict[str, str] = {}
        for number, name in enumerate(order):
            station_to_number[name] = number
            number_to_station[number] = name
            graph.add_vertex(number)
            graph.set_station_lines(name, lines_by_station[name])
            normalized.setdefault(normalize_name(name), name)

        for conn in self.data["connections"]:
            graph.add_edge(
                Edge(
                    station_to_number[conn["source"]],
                    station_to_number[conn["dest"]],
                    int(conn["distance"]),
                    conn["line"],
                )
            )

        self.graph = graph
        self.station_to_number = station_to_number
        self.number_to_station = number_to_station
        self._normalized_index = normalized

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    def has_station(self, name: str) -> bool:
        """Return True if the official station name exists."""
        return name in self.station_to_number

    def official_name(self, name: str) -> Optional[str]:
        """Map user input to the official station name.

        Exact matches are preferred; otherwise matching ignores case and
        whitespace. Returns None when no station matches.
        """
        if name in self.station_to_number:
            return name
        key = normalize_name(name)
        if not key:
            return None
        return self._normalized_index.get(key)

    def station_names(self) -> List[str]:
        """Return all official station names sorted alphabetically."""
        return sorted(self.station_to_number.keys())

    def lines(self) -> List[str]:
        """Return all line names present in the network, sorted."""
        names: Set[str] = set()
        for station in self.data["stations"]:
            names.update(station.get("lines", []))
        for conn in self.data["connections"]:
            names.add(conn.get("line"))
        names.discard(None)
        return sorted(names)

    def stations_on_line(self, line: str) -> List[str]:
        """Return the names of stations served by a line, in number order."""
        return [
            self.number_to_station[number]
            for number in sorted(self.number_to_station)
            if line in self.graph.get_station_lines(self.number_to_station[number])
        ]

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return a deep copy of the dataset suitable for saving."""
        return copy.deepcopy(self.data)

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def add_line(self, line_name: str, station_names: Sequence[str], distances: Sequence[int]) -> None:
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered station names along the line (at least 2).
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent.
        """
        if not line_name or not str(line_name).strip():
            raise ValueError("Line name must not be empty")
        if line_name in self.lines():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(station_names)) != len(station_names):
            raise ValueError("A line must not visit the same station twice")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        for distance in distances:
            self._validate_distance(distance)

        existing = {station["name"]: station for station in self.data["stations"]}
        for name in station_names:
            if name not in existing:
                entry = {"name": name, "lines": [line_name]}
                self.data["stations"].append(entry)
                existing[name] = entry
            elif line_name not in existing[name].setdefault("lines", []):
                existing[name]["lines"].append(line_name)

        for i, distance in enumerate(distances):
            self.data["connections"].append({
                "source": station_names[i],
                "dest": station_names[i + 1],
                "distance": int(distance),
                "line": line_name,
            })
        self.rebuild()

    def update_station(self, name: str, new_name: Optional[str] = None,
                       lines: Optional[Sequence[str]] = None) -> None:
        """Modify a station's name and/or line affiliation.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name is already used by another station.
        """
        entry = self._find_station_entry(name)
        if entry is None:
            entry = {"name": name, "lines": []}
            self.data["stations"].append(entry)

        if new_name and new_name != name:
            if new_name in self.station_to_number:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self.data["connections"]:
                if conn["source"] == name:
                    conn["source"] = new_name
                if conn["dest"] == name:
                    conn["dest"] = new_name

        if lines is not None:
            entry["lines"] = list(lines)
        self.rebuild()

    def update_distance(self, source: str, dest: str, distance: int,
                        line: Optional[str] = None) -> int:
        """Update the distance of the connection(s) between two adjacent stations.

        Args:
            source: One station name.
            dest: The adjacent station name.
            distance: New distance in meters (positive integer).
            line: Optional line restricting which connection(s) to update.

        Returns:
            Number of connections updated.

        Raises:
            KeyError: If no matching connection exists.
            ValueError: If the distance is invalid.
        """
        self._validate_distance(distance)
        matched = 0
        for conn in self.data["connections"]:
            if {conn["source"], conn["dest"]} == {source, dest} and (line is None or conn["line"] == line):
                conn["distance"] = int(distance)
                matched += 1
        if matched == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        self.rebuild()
        return matched

    # ------------------------------------------------------------------
    # Data integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self) -> Dict[str, List[str]]:
        """Run the data integrity checks.

        Returns:
            A dictionary with the keys 'coverage', 'connections' and 'distances',
            each mapping to a list of human-readable issue descriptions.
            All lists are empty when the data is clean.
        """
        report: Dict[str, List[str]] = {"coverage": [], "connections": [], "distances": []}
        stations = self.data["stations"]
        connections = self.data["connections"]
        station_names = {station["name"] for station in stations}
        declared = {station["name"]: set(station.get("lines", [])) for station in stations}

        # Coverage: every required main line must be represented.
        served: Dict[str, Set[str]] = {}
        for station in stations:
            for line in station.get("lines", []):
                served.setdefault(line, set()).add(station["name"])
        for conn in connections:
            for end in (conn.get("source"), conn.get("dest")):
                if end is not None:
                    served.setdefault(conn.get("line"), set()).add(end)
        for line in REQUIRED_MAIN_LINES:
            count = len(served.get(line, set()))
            if count < MIN_STATIONS_PER_MAIN_LINE:
                report["coverage"].append(
                    f"Line '{line}' has {count} station(s), expected at least {MIN_STATIONS_PER_MAIN_LINE}"
                )
        for station in stations:
            if not station.get("lines"):
                report["coverage"].append(f"Station '{station['name']}' has no line affiliation")

        # Connections: references, duplicates, self-loops, line consistency.
        seen: Set[tuple] = set()
        for index, conn in enumerate(connections):
            missing = [key for key in ("source", "dest", "distance", "line") if key not in conn]
            if missing:
                report["connections"].append(f"Connection #{index} is missing fields: {', '.join(missing)}")
                continue
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            for end in (src, dst):
                if end not in station_names:
                    report["connections"].append(f"Connection #{index} references unknown station '{end}'")
            if src == dst:
                report["connections"].append(f"Connection #{index} links station '{src}' to itself")
            key = (frozenset((src, dst)), line)
            if key in seen:
                report["connections"].append(f"Duplicate connection between '{src}' and '{dst}' on {line}")
            seen.add(key)
            for end in (src, dst):
                if end in declared and line not in declared[end]:
                    report["connections"].append(
                        f"Station '{end}' is linked on {line} but does not list that line"
                    )

        report["connections"].extend(self._connectivity_issues())

        # Distances: type, sign and plausibility.
        for index, conn in enumerate(connections):
            distance = conn.get("distance")
            label = f"{conn.get('source')} - {conn.get('dest')} ({conn.get('line')})"
            if isinstance(distance, bool) or not isinstance(distance, int):
                report["distances"].append(f"Distance of {label} must be an integer number of meters")
            elif distance <= 0:
                report["distances"].append(f"Distance of {label} must be positive, got {distance}")
            elif distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
                report["distances"].append(
                    f"WARNING: distance of {label} ({distance} m) is outside the plausible range "
                    f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )
        return report

    def _connectivity_issues(self) -> List[str]:
        """Check that every station is reachable from the first station."""
        vertices = self.graph.vertices()
        if not vertices:
            return ["The network contains no stations"]
        seen = {vertices[0]}
        queue = deque([vertices[0]])
        while queue:
            current = queue.popleft()
            for edge in self.graph.adj(current):
                nxt = edge.other(current)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        unreachable = sorted(self.number_to_station[v] for v in vertices if v not in seen)
        if unreachable:
            return [f"{len(unreachable)} station(s) not connected to the rest of the network: {', '.join(unreachable)}"]
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_station_entry(self, name: str) -> Optional[Dict[str, Any]]:
        for station in self.data["stations"]:
            if station["name"] == name:
                return station
        return None

    @staticmethod
    def _validate_distance(distance: Any) -> None:
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise ValueError(f"Distance must be a positive integer number of meters, got {distance!r}")
