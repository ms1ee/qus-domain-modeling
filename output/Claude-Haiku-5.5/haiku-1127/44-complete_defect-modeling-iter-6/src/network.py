"""Subway network construction and data management (add lines, modify stations, update distances)."""
from __future__ import annotations

import copy
from typing import Dict, List, Optional

from models import Edge, Graph


class SubwayNetwork:
    """Holds the raw subway dataset and the derived weighted graph.

    Station numbers start at 1 and are assigned in the order station names are
    first encountered (station list first, then connection endpoints). Any data
    update rebuilds the graph so that it stays consistent with the raw data.
    """

    def __init__(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise ValueError("subway data must be a dictionary")
        for key in ("stations", "connections"):
            if not isinstance(data.get(key), list):
                raise ValueError(f"subway data must contain a list under '{key}'")
        self.raw: dict = copy.deepcopy(data)
        self.station_to_number: Dict[str, int] = {}
        self.number_to_name: Dict[int, str] = {}
        self.graph: Graph = Graph()
        self.skipped_connections: List[str] = []
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        """(Re)build station mapping and graph from the raw data."""
        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        self.skipped_connections = []

        lines_by_name: Dict[str, List[str]] = {}
        for station in self.raw["stations"]:
            name = str(station.get("name", "")).strip()
            if not name:
                continue
            lines = lines_by_name.setdefault(name, [])
            for line in station.get("lines", []) or []:
                if line not in lines:
                    lines.append(line)

        for conn in self.raw["connections"]:
            for key in ("source", "dest"):
                name = str(conn.get(key, "")).strip()
                if name:
                    lines_by_name.setdefault(name, [])

        for number, name in enumerate(lines_by_name, start=1):
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.add_vertex(number)
            self.graph.set_station_lines(name, lines_by_name[name])

        for conn in self.raw["connections"]:
            src = str(conn.get("source", "")).strip()
            dst = str(conn.get("dest", "")).strip()
            line = str(conn.get("line", ""))
            try:
                distance = float(conn["distance"])
                edge = Edge(self.station_to_number[src], self.station_to_number[dst], distance, line)
            except (KeyError, ValueError, TypeError) as exc:
                self.skipped_connections.append(f"{src} - {dst} ({line}): {exc}")
                continue
            self.graph.add_edge(edge)

    # --------------------------------------------------------------- queries
    def stations(self) -> List[str]:
        """Return all station names ordered by station number."""
        return [self.number_to_name[n] for n in sorted(self.number_to_name)]

    def has_station(self, name: str) -> bool:
        """Return True if the exact station name exists."""
        return name in self.station_to_number

    def resolve_station(self, name: str) -> Optional[str]:
        """Return the official station name matching ``name`` or None.

        Whitespace is normalized and a unique case-insensitive match is accepted.
        """
        cleaned = " ".join(str(name).split())
        if cleaned in self.station_to_number:
            return cleaned
        folded = cleaned.casefold()
        matches = [n for n in self.station_to_number if n.casefold() == folded]
        return matches[0] if len(matches) == 1 else None

    def number_of(self, name: str) -> int:
        """Return the station number of a station name."""
        return self.station_to_number[name]

    def name_of(self, number: int) -> str:
        """Return the station name of a station number."""
        return self.number_to_name[number]

    def lines_of(self, name: str) -> List[str]:
        """Return the lines serving a station."""
        return self.graph.get_station_lines(name)

    def is_transfer_station(self, name: str) -> bool:
        """Return True if a station is served by more than one line."""
        return len(self.lines_of(name)) > 1

    def line_names(self) -> List[str]:
        """Return all known line names (from station lines and connections), sorted."""
        names = set()
        for station in self.raw["stations"]:
            for line in station.get("lines", []) or []:
                names.add(line)
        for conn in self.raw["connections"]:
            if conn.get("line"):
                names.add(conn["line"])
        return sorted(names)

    # ---------------------------------------------------------------- updates
    def _find_station_entries(self, name: str) -> List[dict]:
        return [s for s in self.raw["stations"] if str(s.get("name", "")).strip() == name]

    def add_line(self, line_name: str, station_names: List[str], distances: List[int]) -> None:
        """Add a new line described by an ordered station list and consecutive distances (meters)."""
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"line '{line_name}' already exists")
        names = [str(n).strip() for n in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if any(not n for n in names):
            raise ValueError("station names must not be empty")
        if len(distances) != len(names) - 1:
            raise ValueError("number of distances must be one less than number of stations")
        for d in distances:
            if d <= 0:
                raise ValueError("distances must be positive")

        for name in names:
            entries = self._find_station_entries(name)
            if entries:
                for entry in entries:
                    lines = entry.setdefault("lines", [])
                    if line_name not in lines:
                        lines.append(line_name)
            else:
                self.raw["stations"].append({"name": name, "lines": [line_name]})

        for i, d in enumerate(distances):
            self.raw["connections"].append(
                {"source": names[i], "dest": names[i + 1], "distance": int(d), "line": line_name}
            )
        self._build()

    def set_station_lines(self, name: str, lines: List[str]) -> None:
        """Replace the lines serving a station (station information modification)."""
        if name not in self.station_to_number:
            raise KeyError(f"station '{name}' does not exist")
        entries = self._find_station_entries(name)
        if entries:
            for entry in entries:
                entry["lines"] = list(lines)
        else:
            self.raw["stations"].append({"name": name, "lines": list(lines)})
        self._build()

    def update_distance(self, source: str, dest: str, distance: int, line: Optional[str] = None) -> int:
        """Update the distance (meters) of connections between two stations.

        Returns:
            The number of connections updated.
        """
        if distance <= 0:
            raise ValueError("distance must be positive")
        count = 0
        for conn in self.raw["connections"]:
            pair_ok = (conn.get("source") == source and conn.get("dest") == dest) or (
                conn.get("source") == dest and conn.get("dest") == source
            )
            if pair_ok and (line is None or conn.get("line") == line):
                conn["distance"] = int(distance)
                count += 1
        if count == 0:
            raise KeyError(f"no connection between '{source}' and '{dest}'")
        self._build()
        return count
