"""
Subway network domain model.

Loads the dataset from subway_data.json, builds the weighted directed graph
with numeric station identifiers, resolves user-entered station names,
supports data updates and performs data integrity checks.
"""

from __future__ import annotations

import copy
import datetime
import difflib
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

# Representative main lines that must be covered by the dataset.
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

# Connections longer than this are reported as suspicious by the accuracy check.
MAX_REASONABLE_DISTANCE_M = 3000

# Minimum similarity for accepting a non-exact station name.
FUZZY_MATCH_CUTOFF = 0.6


class UnknownStationError(ValueError):
    """Raised when a station name cannot be matched to any known station."""


def normalize_station_name(name: str) -> str:
    """Normalise a station name for lenient comparison.

    Removes whitespace and separators, ignores case and the Chinese suffix "站".
    """
    cleaned = re.sub(r"[\s\-_·•]+", "", name)
    return cleaned.casefold().removesuffix("站")


class SubwayNetwork:
    """Beijing Subway network with station lookup and data management.

    Attributes:
        name: Network name.
        data_source: Path of the dataset the network was loaded from.
        version: Dataset version string.
        last_updated: Timestamp of the last modification.
        graph: Weighted directed graph keyed by station numbers.
        name_to_number: Mapping of station name to station number.
        number_to_name: Mapping of station number to station name.
        build_warnings: Problems found while building the graph.
    """

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        data_path: str = DATA_FILE_PATH,
    ) -> None:
        if data is None:
            data = load_subway_data(data_path)

        self.name = "Beijing Subway"
        self.data_source = os.fspath(data_path)
        self.version = str(data.get("version", "1.0"))
        self.last_updated = datetime.datetime.now()

        self._stations: List[Dict[str, Any]] = [
            {"name": str(s["name"]), "lines": [str(x) for x in s.get("lines", [])]}
            for s in data["stations"]
        ]
        self._connections: List[Dict[str, Any]] = [
            {
                "source": str(c["source"]),
                "dest": str(c["dest"]),
                "distance": int(c["distance"]),
                "line": str(c["line"]),
            }
            for c in data["connections"]
        ]

        self.graph: Graph = Graph()
        self.name_to_number: Dict[str, int] = {}
        self.number_to_name: Dict[int, str] = {}
        self.build_warnings: List[str] = []
        self._build()

    # ----- construction ------------------------------------------------------
    def _build(self) -> None:
        """(Re)build the graph and lookup tables from the raw dataset."""
        self.graph = Graph()
        self.name_to_number = {}
        self.number_to_name = {}
        self.build_warnings = []

        # Merge duplicate station entries and keep first-seen order.
        merged: Dict[str, List[str]] = {}
        order: List[str] = []
        for station in self._stations:
            name = station["name"]
            if name not in merged:
                merged[name] = []
                order.append(name)
            for line in station["lines"]:
                if line not in merged[name]:
                    merged[name].append(line)

        for number, name in enumerate(order, start=1):
            self.name_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.set_station_lines(name, merged[name])
            self.graph.add_vertex(number)

        for conn in self._connections:
            src = self.name_to_number.get(conn["source"])
            dst = self.name_to_number.get(conn["dest"])
            if src is None or dst is None:
                self.build_warnings.append(
                    f"Connection {conn['source']} -> {conn['dest']} ({conn['line']}) "
                    "references an unknown station"
                )
                continue
            self.graph.add_edge(Edge(src, dst, conn["distance"], conn["line"]))

    def _refresh(self) -> None:
        """Rebuild derived structures after a data modification."""
        self._build()
        self.last_updated = datetime.datetime.now()

    # ----- station lookup ----------------------------------------------------
    def station_names(self) -> List[str]:
        """Return all station names sorted alphabetically."""
        return sorted(self.name_to_number)

    def standardize_name(self, raw_name: str) -> Optional[str]:
        """Return the official station name matching the input, or None."""
        text = raw_name.strip()
        if text in self.name_to_number:
            return text
        key = normalize_station_name(text)
        for name in self.name_to_number:
            if normalize_station_name(name) == key:
                return name
        return None

    def resolve_station(self, raw_name: str) -> Tuple[str, bool]:
        """Resolve user input to an official station name.

        Returns:
            (official_name, was_fuzzy_matched). Unknown names that are close
            enough to a known station are matched to the nearest station.

        Raises:
            UnknownStationError: If no sufficiently close station exists.
        """
        text = raw_name.strip() if raw_name else ""
        if not text:
            raise UnknownStationError("Station name cannot be empty")

        exact = self.standardize_name(text)
        if exact is not None:
            return exact, False

        keys: Dict[str, str] = {}
        for name in self.name_to_number:
            keys.setdefault(normalize_station_name(name), name)
        matches = difflib.get_close_matches(
            normalize_station_name(text), list(keys), n=1, cutoff=FUZZY_MATCH_CUTOFF
        )
        if not matches:
            raise UnknownStationError(text)
        return keys[matches[0]], True

    def number_of(self, station_name: str) -> int:
        """Return the station number of an official station name."""
        if station_name not in self.name_to_number:
            raise UnknownStationError(station_name)
        return self.name_to_number[station_name]

    def get_station_lines(self, station_name: str) -> List[str]:
        """Return the lines serving a station."""
        if station_name not in self.graph.station_lines:
            raise UnknownStationError(station_name)
        return list(self.graph.station_lines[station_name])

    def is_transfer_station(self, station_name: str) -> bool:
        """Return True if the station is served by more than one line."""
        return len(self.get_station_lines(station_name)) > 1

    def line_names(self) -> List[str]:
        """Return all line names in the network, sorted."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        for conn in self._connections:
            lines.add(conn["line"])
        return sorted(lines)

    def stations_on_line(self, line: str) -> List[str]:
        """Return the station names served by a line."""
        return [name for name, lines in self.graph.station_lines.items() if line in lines]

    # ----- data updates ------------------------------------------------------
    def add_line(
        self,
        line_name: str,
        station_names: Sequence[str],
        distances_m: Sequence[int],
        bidirectional: bool = True,
    ) -> None:
        """Add a new line described by an ordered station sequence.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names along the line.
            distances_m: Distances in meters between consecutive stations.
            bidirectional: If True, add connections in both directions.

        Raises:
            ValueError: If the line already exists or the data is invalid.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")

        stations = [s.strip() for s in station_names]
        if len(stations) < 2 or len(set(stations)) != len(stations):
            raise ValueError("A line needs at least two distinct stations")
        if len(distances_m) != len(stations) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        distances = [int(d) for d in distances_m]
        if any(d <= 0 for d in distances):
            raise ValueError("Distances must be positive")

        existing = {s["name"] for s in self._stations}
        for name in stations:
            if name not in existing:
                self._stations.append({"name": name, "lines": [line_name]})
                existing.add(name)
            else:
                for entry in self._stations:
                    if entry["name"] == name and line_name not in entry["lines"]:
                        entry["lines"].append(line_name)

        for i, distance in enumerate(distances):
            self._connections.append(
                {"source": stations[i], "dest": stations[i + 1], "distance": distance, "line": line_name}
            )
            if bidirectional:
                self._connections.append(
                    {"source": stations[i + 1], "dest": stations[i], "distance": distance, "line": line_name}
                )
        self._refresh()

    def modify_station(
        self,
        old_name: str,
        new_name: Optional[str] = None,
        lines: Optional[Sequence[str]] = None,
    ) -> None:
        """Rename a station and/or change the lines serving it."""
        old = old_name.strip()
        entries = [s for s in self._stations if s["name"] == old]
        if not entries:
            raise UnknownStationError(old)

        if new_name is not None and new_name.strip() and new_name.strip() != old:
            new = new_name.strip()
            if new in self.name_to_number:
                raise ValueError(f"Station '{new}' already exists")
            for entry in entries:
                entry["name"] = new
            for conn in self._connections:
                if conn["source"] == old:
                    conn["source"] = new
                if conn["dest"] == old:
                    conn["dest"] = new
            old = new

        if lines is not None:
            cleaned = list(dict.fromkeys(str(x).strip() for x in lines if str(x).strip()))
            if not cleaned:
                raise ValueError("A station must be served by at least one line")
            for entry in self._stations:
                if entry["name"] == old:
                    entry["lines"] = list(cleaned)
        self._refresh()

    def update_distance(
        self, source: str, dest: str, distance_m: int, line: Optional[str] = None
    ) -> int:
        """Update the distance of connections between two stations.

        Returns:
            Number of connections updated.
        """
        if distance_m <= 0:
            raise ValueError("Distance must be positive")
        count = 0
        for conn in self._connections:
            if conn["source"] == source and conn["dest"] == dest and (line is None or conn["line"] == line):
                conn["distance"] = int(distance_m)
                count += 1
        if count == 0:
            raise ValueError(f"No connection from '{source}' to '{dest}' found")
        self._refresh()
        return count

    def save_to(self, path: str = DATA_FILE_PATH) -> None:
        """Persist the current dataset to a JSON file."""
        data = {
            "version": self.version,
            "stations": copy.deepcopy(self._stations),
            "connections": copy.deepcopy(self._connections),
        }
        save_subway_data(data, path)

    # ----- integrity checks --------------------------------------------------
    def check_integrity(self) -> Dict[str, List[str]]:
        """Run data integrity checks.

        Checks performed:
            * coverage: representative main lines are present;
            * connectivity: connections reference known stations and
              reverse connections exist, isolated stations are reported;
            * consistency: connection lines are served by both endpoints;
            * accuracy: distances are positive and plausible.

        Returns:
            Dictionary with 'errors' and 'warnings' lists of messages.
        """
        errors: List[str] = list(self.build_warnings)
        warnings: List[str] = []

        all_lines = set(self.line_names())
        for line in REQUIRED_LINES:
            if line not in all_lines:
                errors.append(f"Coverage: main line '{line}' is missing from the dataset")

        connected = set()
        for conn in self._connections:
            src = self.name_to_number.get(conn["source"])
            dst = self.name_to_number.get(conn["dest"])
            if src is not None:
                connected.add(src)
            if dst is not None:
                connected.add(dst)
        for name, number in self.name_to_number.items():
            if number not in connected:
                warnings.append(f"Connectivity: station '{name}' has no connections")

        pairs = {(c["source"], c["dest"]) for c in self._connections}
        seen = set()
        for conn in self._connections:
            s, d, line, dist = conn["source"], conn["dest"], conn["line"], conn["distance"]
            label = f"{s} -> {d} ({line})"
            if s not in self.graph.station_lines or d not in self.graph.station_lines:
                continue  # already reported as a build warning
            if line not in self.graph.station_lines[s] or line not in self.graph.station_lines[d]:
                errors.append(f"Consistency: line '{line}' is not served by both endpoints of {label}")
            if dist <= 0:
                errors.append(f"Accuracy: non-positive distance {dist} m on {label}")
            elif dist > MAX_REASONABLE_DISTANCE_M:
                warnings.append(f"Accuracy: unusually long distance {dist} m on {label}")
            if (s, d, line) in seen:
                warnings.append(f"Connectivity: duplicate connection {label}")
            seen.add((s, d, line))
            if (d, s) not in pairs:
                warnings.append(f"Connectivity: reverse connection {d} -> {s} is missing (one-way link)")

        return {"errors": errors, "warnings": warnings}
