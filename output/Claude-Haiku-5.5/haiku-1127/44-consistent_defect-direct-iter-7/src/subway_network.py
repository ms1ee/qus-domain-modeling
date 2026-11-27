"""Subway network model: station registry, graph construction, updates and data checks."""
from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from src.data_loader import DATA_FILE_PATH, load_subway_data
from src.models import Edge, Graph

# Main lines that must be represented in the dataset (PRD section 4.1).
REQUIRED_LINES: Tuple[str, ...] = (
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

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000
FUZZY_MATCH_CUTOFF = 0.5


class StationNotFoundError(ValueError):
    """Raised when a station name cannot be matched to any known station."""

    def __init__(self, name: str) -> None:
        super().__init__(f"station '{name}' not found")
        self.station_name = name


def normalize_station_name(name: str) -> str:
    """Normalize a station name for comparison (case, spacing and trailing '站')."""
    text = " ".join(str(name).split()).casefold()
    if text.endswith("站") and len(text) > 1:
        text = text[:-1]
    return text


class SubwayNetwork:
    """In-memory representation of the Beijing Subway network.

    Attributes:
        graph: weighted directed Graph keyed by station numbers.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, data_path: str = DATA_FILE_PATH) -> None:
        if data is None:
            data = load_subway_data(data_path)
        self.graph = Graph()
        self.station_to_number: Dict[str, int] = {}  # station name -> station number
        self._names: List[str] = []                  # station number -> station name
        self._norm_index: Dict[str, str] = {}        # normalized name -> official name
        self._line_members: Dict[str, Dict[str, None]] = {}  # line -> ordered set of stations
        self._build(data)

    # ------------------------------------------------------------ construction
    def _build(self, data: Dict[str, Any]) -> None:
        for station in data.get("stations", []):
            name = str(station["name"])
            lines = [str(line) for line in station.get("lines", [])]
            self._ensure_station(name)
            self.graph.set_station_lines(name, lines)
            for line in lines:
                self._register_member(line, name)

        for conn in data.get("connections", []):
            self.add_connection(
                str(conn["source"]),
                str(conn["dest"]),
                int(conn["distance"]),
                str(conn["line"]),
            )

    def _ensure_station(self, name: str) -> int:
        """Return the number of ``name``, creating the station if needed."""
        number = self.station_to_number.get(name)
        if number is None:
            number = len(self._names)
            self.station_to_number[name] = number
            self._names.append(name)
            self._norm_index[normalize_station_name(name)] = name
            self.graph.add_vertex(number)
            if name not in self.graph.station_lines:
                self.graph.set_station_lines(name, [])
        return number

    def _register_member(self, line: str, station: str) -> None:
        self._line_members.setdefault(line, {})[station] = None

    def add_connection(self, source: str, dest: str, distance: int, line: str) -> None:
        """Add a single directed connection between two stations."""
        if distance <= 0:
            raise ValueError("connection distance must be positive")
        src_num = self._ensure_station(source)
        dst_num = self._ensure_station(dest)
        self.graph.add_edge(Edge(src_num, dst_num, distance, line))
        self._register_member(line, source)
        self._register_member(line, dest)

    # ---------------------------------------------------------------- lookups
    def station_names(self) -> List[str]:
        """Return all official station names, sorted."""
        return sorted(self.station_to_number)

    def lines(self) -> List[str]:
        """Return all line names, sorted."""
        return sorted(self._line_members)

    def stations_on_line(self, line: str) -> List[str]:
        """Return the stations served by ``line`` in dataset order."""
        return list(self._line_members.get(line, {}).keys())

    def name_of(self, number: int) -> str:
        """Return the station name for a station number."""
        return self._names[number]

    def number_of(self, name: str) -> int:
        """Return the station number for an official station name."""
        return self.station_to_number[name]

    def resolve_station(self, name: str) -> Tuple[str, bool]:
        """Standardize a user-supplied station name.

        Returns:
            (official_name, exact_match). When there is no exact match, the
            nearest official name is returned with exact_match=False.

        Raises:
            StationNotFoundError: if no station is reasonably similar.
        """
        text = normalize_station_name(name)
        if not text:
            raise StationNotFoundError(name)
        if text in self._norm_index:
            return self._norm_index[text], True
        matches = difflib.get_close_matches(
            text, list(self._norm_index.keys()), n=1, cutoff=FUZZY_MATCH_CUTOFF
        )
        if not matches:
            raise StationNotFoundError(name)
        return self._norm_index[matches[0]], False

    def transfer_stations(self) -> List[str]:
        """Return stations served by more than one line."""
        return [name for name, lines in self.graph.station_lines.items() if len(set(lines)) > 1]

    def _exact_number(self, name: str) -> int:
        if name not in self.station_to_number:
            raise StationNotFoundError(name)
        return self.station_to_number[name]

    # ---------------------------------------------------------------- updates
    def add_line(self, line_name: str, station_names: Sequence[str], distances: Sequence[int]) -> None:
        """Add a new line as a sequence of stations joined by bidirectional connections.

        Args:
            line_name: name of the new line (must not already exist).
            station_names: ordered station names along the line (at least 2).
            distances: distance in meters between consecutive stations.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self._line_members:
            raise ValueError(f"line '{line_name}' already exists")
        names = [name.strip() for name in station_names]
        if len(names) < 2 or any(not name for name in names):
            raise ValueError("a line needs at least two named stations")
        if len(distances) != len(names) - 1:
            raise ValueError("expected one distance per pair of consecutive stations")

        for index, distance in enumerate(distances):
            a, b = names[index], names[index + 1]
            self.add_connection(a, b, int(distance), line_name)
            self.add_connection(b, a, int(distance), line_name)

        for name in names:
            lines = self.graph.get_station_lines(name)
            if line_name not in lines:
                lines.append(line_name)
                self.graph.set_station_lines(name, lines)

    def update_station_lines(self, name: str, lines: Sequence[str]) -> None:
        """Replace the list of lines serving an existing station."""
        official = self._names[self._exact_number(name)]
        new_lines = [str(line) for line in lines]
        self.graph.set_station_lines(official, new_lines)
        for line in new_lines:
            self._register_member(line, official)

    def rename_station(self, old_name: str, new_name: str) -> None:
        """Rename an existing station, keeping all connections."""
        new_name = new_name.strip()
        number = self._exact_number(old_name)
        if not new_name or new_name in self.station_to_number:
            raise ValueError(f"cannot rename to '{new_name}'")
        del self.station_to_number[old_name]
        self.station_to_number[new_name] = number
        self._names[number] = new_name
        self._norm_index.pop(normalize_station_name(old_name), None)
        self._norm_index[normalize_station_name(new_name)] = new_name
        self.graph.station_lines[new_name] = self.graph.station_lines.pop(old_name, [])
        for line, members in self._line_members.items():
            if old_name in members:
                self._line_members[line] = {
                    (new_name if member == old_name else member): None for member in members
                }

    def update_distance(self, source: str, dest: str, distance: int) -> int:
        """Update the distance between two adjacent stations in both directions.

        Returns:
            The number of edges updated.
        """
        if not isinstance(distance, int) or distance <= 0:
            raise ValueError("distance must be a positive integer number of meters")
        a = self._exact_number(source)
        b = self._exact_number(dest)
        count = 0
        for x, y in ((a, b), (b, a)):
            for edge in self.graph.edges_between(x, y):
                edge.distance = distance
                count += 1
        if count == 0:
            raise ValueError(f"no connection between '{source}' and '{dest}'")
        return count

    def to_data(self) -> Dict[str, Any]:
        """Export the current network in the subway_data.json structure."""
        stations = [
            {"name": name, "lines": self.graph.get_station_lines(name)}
            for name in self._names
        ]
        connections = [
            {
                "source": self._names[edge.source],
                "dest": self._names[edge.dest],
                "distance": int(round(edge.weight)),
                "line": edge.line,
            }
            for edge in self.graph.edges()
        ]
        return {"stations": stations, "connections": connections}

    # ------------------------------------------------------------- data checks
    def check_data(self) -> Tuple[bool, List[str]]:
        """Run data integrity checks.

        Checks station coverage of the main lines, connection integrity
        (duplicates, reverse links, distance plausibility) and consistency
        between declared station lines and actual connections.

        Returns:
            (passed, messages). ``passed`` is False when any error was found.
        """
        messages: List[str] = []
        errors = 0
        warnings = 0

        # 1. Station coverage of main lines.
        for line in REQUIRED_LINES:
            count = len(self.stations_on_line(line))
            if count < 2:
                messages.append(
                    f"[ERROR] coverage: line '{line}' has {count} station(s), expected at least 2"
                )
                errors += 1
            else:
                messages.append(f"[OK] coverage: line '{line}' has {count} stations")

        edges = list(self.graph.edges())
        keys = {(e.source, e.dest, e.line) for e in edges}
        incoming: Set[int] = {e.dest for e in edges}
        outgoing: Set[int] = {e.source for e in edges}
        for number, name in enumerate(self._names):
            if number not in incoming and number not in outgoing:
                messages.append(f"[WARN] connectivity: station '{name}' has no connections")
                warnings += 1

        # 2. Connection integrity.
        seen: Set[Tuple[int, int, str]] = set()
        for edge in edges:
            key = (edge.source, edge.dest, edge.line)
            src_name = self._names[edge.source]
            dst_name = self._names[edge.dest]
            if key in seen:
                messages.append(
                    f"[ERROR] connection: duplicate {src_name} -> {dst_name} on '{edge.line}'"
                )
                errors += 1
            seen.add(key)

            # 3. Distance accuracy.
            if not isinstance(edge.weight, (int, float)) or edge.weight <= 0:
                messages.append(
                    f"[ERROR] distance: {src_name} -> {dst_name} has invalid distance {edge.weight}"
                )
                errors += 1
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= edge.weight <= MAX_PLAUSIBLE_DISTANCE_M):
                messages.append(
                    f"[WARN] distance: {src_name} -> {dst_name} distance {edge.weight} m is outside "
                    f"the plausible range {MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )
                warnings += 1

            if (edge.dest, edge.source, edge.line) not in keys:
                messages.append(
                    f"[WARN] connection: no reverse connection {dst_name} -> {src_name} on '{edge.line}'"
                )
                warnings += 1

        # 4. Declared station lines versus actual connection lines.
        touching: Dict[str, Set[str]] = {}
        for edge in edges:
            touching.setdefault(self._names[edge.source], set()).add(edge.line)
            touching.setdefault(self._names[edge.dest], set()).add(edge.line)
        for name, declared in self.graph.station_lines.items():
            actual = touching.get(name, set())
            if actual and set(declared) != actual:
                messages.append(
                    f"[WARN] consistency: station '{name}' declares lines {sorted(set(declared))} "
                    f"but connections use {sorted(actual)}"
                )
                warnings += 1

        messages.append(
            f"Summary: {errors} error(s), {warnings} warning(s), "
            f"{len(self._names)} stations, {len(edges)} connections"
        )
        return errors == 0, messages
