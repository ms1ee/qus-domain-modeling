"""Data integrity checks and update operations on the raw subway dataset."""

from __future__ import annotations

import copy
import json
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Set

from models import Graph
from network import build_graph

REQUIRED_MAIN_LINES = [
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
MIN_STATIONS_PER_MAIN_LINE = 2
MAX_ADJACENT_DISTANCE_M = 10000


def _is_positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


class DataManager:
    """Wraps the raw dataset to offer integrity checks and updates."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ------------------------------------------------------------------ #
    # Integrity checks
    # ------------------------------------------------------------------ #
    def check_integrity(self) -> List[str]:
        """Run all integrity checks and return human-readable issues.

        An empty list means the dataset passed every check.
        """
        issues: List[str] = []
        stations = self.data["stations"]
        connections = self.data["connections"]

        # Station data
        station_lines: Dict[str, List[str]] = {}
        for index, entry in enumerate(stations):
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                issues.append(f"Station #{index} has no valid name")
                continue
            if name in station_lines:
                issues.append(f"Duplicate station name: '{name}'")
            lines = entry.get("lines")
            if not isinstance(lines, list) or not lines:
                issues.append(f"Station '{name}' has no line affiliation")
                lines = []
            station_lines[name] = list(lines)

        # Coverage of main lines
        for line in REQUIRED_MAIN_LINES:
            count = sum(1 for lines in station_lines.values() if line in lines)
            if count == 0:
                issues.append(f"Coverage: main line '{line}' has no stations")
            elif count < MIN_STATIONS_PER_MAIN_LINE:
                issues.append(
                    f"Coverage: main line '{line}' has only {count} station(s)"
                )

        # Connection integrity and distance accuracy
        adjacency: Dict[str, Set[str]] = {name: set() for name in station_lines}
        touched_lines: Dict[str, Set[str]] = {name: set() for name in station_lines}
        seen_pairs: Dict[tuple, Any] = {}
        for index, conn in enumerate(connections):
            src = conn.get("source")
            dst = conn.get("dest")
            distance = conn.get("distance")
            line = conn.get("line")
            label = f"connection #{index} ({src} - {dst}, {line})"

            if src not in station_lines or dst not in station_lines:
                issues.append(f"Connection: unknown station in {label}")
                continue
            if src == dst:
                issues.append(f"Connection: self loop in {label}")
                continue
            if not _is_positive_number(distance):
                issues.append(f"Distance: invalid (non-positive) distance in {label}")
            elif distance > MAX_ADJACENT_DISTANCE_M:
                issues.append(f"Distance: suspiciously large ({distance} m) in {label}")
            if line not in station_lines[src] or line not in station_lines[dst]:
                issues.append(f"Connection: line '{line}' is not served by both endpoints in {label}")

            key = (line, frozenset((src, dst)))
            if key in seen_pairs:
                if seen_pairs[key] != distance:
                    issues.append(f"Distance: conflicting duplicate distances in {label}")
                else:
                    issues.append(f"Connection: duplicate connection in {label}")
            else:
                seen_pairs[key] = distance

            adjacency[src].add(dst)
            adjacency[dst].add(src)
            touched_lines[src].add(line)
            touched_lines[dst].add(line)

        for name, lines in station_lines.items():
            for line in lines:
                if line not in touched_lines[name]:
                    issues.append(
                        f"Connection: station '{name}' is on '{line}' but has no connection on that line"
                    )

        # Network connectivity
        components = self._count_components(adjacency)
        if components > 1:
            issues.append(f"Connectivity: network has {components} disconnected components")

        return issues

    @staticmethod
    def _count_components(adjacency: Dict[str, Set[str]]) -> int:
        """Count connected components of an undirected adjacency mapping."""
        visited: Set[str] = set()
        components = 0
        for start in adjacency:
            if start in visited:
                continue
            components += 1
            queue = deque([start])
            visited.add(start)
            while queue:
                current = queue.popleft()
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
        return components

    # ------------------------------------------------------------------ #
    # Data updates
    # ------------------------------------------------------------------ #
    def _find_station(self, name: str) -> Optional[Dict[str, Any]]:
        for entry in self.data["stations"]:
            if entry.get("name") == name:
                return entry
        return None

    def add_line(self, line_name: str, station_names: Sequence[str], distances: Sequence[int]) -> None:
        """Add a new line with its ordered stations and segment distances.

        New stations are created when they do not exist yet; existing stations
        gain the new line (becoming transfer stations).

        Raises:
            ValueError: On invalid input or if the line already exists.
        """
        line_name = (line_name or "").strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        names = [name.strip() for name in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("Station names on a line must be unique")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for distance in distances:
            if not _is_positive_number(distance):
                raise ValueError(f"Invalid distance: {distance}")
        for entry in self.data["stations"]:
            if line_name in entry.get("lines", []):
                raise ValueError(f"Line '{line_name}' already exists")

        index = {entry["name"]: entry for entry in self.data["stations"]}
        for name in names:
            if name in index:
                if line_name not in index[name]["lines"]:
                    index[name]["lines"].append(line_name)
            else:
                new_entry = {"name": name, "lines": [line_name]}
                self.data["stations"].append(new_entry)
                index[name] = new_entry

        for src, dst, distance in zip(names, names[1:], distances):
            self.data["connections"].append(
                {"source": src, "dest": dst, "distance": int(distance), "line": line_name}
            )

    def update_station(
        self,
        name: str,
        lines: Optional[Sequence[str]] = None,
        new_name: Optional[str] = None,
    ) -> None:
        """Modify a station's lines and/or rename it.

        Raises:
            KeyError: If the station does not exist.
            ValueError: On invalid input or name collision.
        """
        entry = self._find_station(name)
        if entry is None:
            raise KeyError(f"Unknown station: {name}")
        if lines is not None:
            cleaned = [line for line in lines if isinstance(line, str) and line.strip()]
            if not cleaned:
                raise ValueError("A station must keep at least one line")
            entry["lines"] = list(dict.fromkeys(cleaned))
        if new_name is not None and new_name != name:
            new_name = new_name.strip()
            if not new_name:
                raise ValueError("New station name must not be empty")
            if self._find_station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self.data["connections"]:
                if conn.get("source") == name:
                    conn["source"] = new_name
                if conn.get("dest") == name:
                    conn["dest"] = new_name

    def update_distance(
        self,
        source: str,
        dest: str,
        distance: int,
        line: Optional[str] = None,
    ) -> int:
        """Update the distance of the connection(s) between two stations.

        Returns:
            The number of connection records updated.

        Raises:
            ValueError: If the distance is invalid.
            KeyError: If no matching connection exists.
        """
        if not _is_positive_number(distance):
            raise ValueError("Distance must be a positive number of meters")
        updated = 0
        for conn in self.data["connections"]:
            pair = {conn.get("source"), conn.get("dest")}
            if pair != {source, dest}:
                continue
            if line is not None and conn.get("line") != line:
                continue
            conn["distance"] = int(distance)
            updated += 1
        if updated == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        return updated

    # ------------------------------------------------------------------ #
    # Access and persistence
    # ------------------------------------------------------------------ #
    def build_graph(self) -> Graph:
        """Build a graph from the current (possibly updated) dataset."""
        return build_graph(self.data)

    def to_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the current dataset."""
        return copy.deepcopy(self.data)

    def save(self, path: str) -> None:
        """Write the current dataset to a JSON file."""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
