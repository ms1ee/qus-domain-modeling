"""Data update mechanisms for the subway dataset.

Supports adding new lines, modifying station information and updating
inter-station distances. Operations work on an in-memory copy of the
dataset; call save() to persist the changes.
"""

import copy
from typing import Any, Dict, List, Optional, Sequence

from data_loader import DATA_FILE_PATH, save_subway_data


class SubwayDataManager:
    """Mutable wrapper around the raw subway dataset dictionary."""

    def __init__(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("subway data must be a dictionary")
        self.data: Dict[str, Any] = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ------------------------------------------------------------------ helpers
    def _find_station(self, name: str) -> Optional[Dict[str, Any]]:
        for station in self.data["stations"]:
            if station.get("name") == name:
                return station
        return None

    def get_line_names(self) -> List[str]:
        """Return all line names known in stations or connections."""
        names: List[str] = []
        for station in self.data["stations"]:
            for line in station.get("lines", []):
                if line not in names:
                    names.append(line)
        for conn in self.data["connections"]:
            line = conn.get("line")
            if line not in names:
                names.append(line)
        return names

    # ---------------------------------------------------------------- mutations
    def add_line(
        self,
        line_name: str,
        station_names: Sequence[str],
        distances: Sequence[int],
    ) -> None:
        """Add a new line made of consecutive stations.

        Args:
            line_name: name of the new line; must not already exist.
            station_names: ordered station names of the line (at least 2).
            distances: distance in meters between consecutive stations
                (length must be len(station_names) - 1, all positive).

        Raises:
            ValueError: on duplicate line names or invalid input.
        """
        if not line_name or not line_name.strip():
            raise ValueError("line name must be non-empty")
        line_name = line_name.strip()
        if line_name in self.get_line_names():
            raise ValueError(f"line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("distances must have one entry per adjacent station pair")
        for distance in distances:
            if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
                raise ValueError("distances must be positive integers (meters)")

        for name in station_names:
            station = self._find_station(name)
            if station is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in station.setdefault("lines", []):
                station["lines"].append(line_name)

        for index, distance in enumerate(distances):
            self.data["connections"].append(
                {
                    "source": station_names[index],
                    "dest": station_names[index + 1],
                    "distance": distance,
                    "line": line_name,
                }
            )

    def modify_station(
        self,
        name: str,
        new_name: Optional[str] = None,
        lines: Optional[Sequence[str]] = None,
    ) -> None:
        """Rename a station and/or replace its line list.

        Raises:
            KeyError: if the station does not exist.
            ValueError: if the new name is already used.
        """
        station = self._find_station(name)
        if station is None:
            raise KeyError(f"station '{name}' does not exist")

        if new_name and new_name.strip() and new_name.strip() != name:
            new_name = new_name.strip()
            if self._find_station(new_name) is not None:
                raise ValueError(f"station '{new_name}' already exists")
            station["name"] = new_name
            for conn in self.data["connections"]:
                if conn.get("source") == name:
                    conn["source"] = new_name
                if conn.get("dest") == name:
                    conn["dest"] = new_name

        if lines is not None:
            station["lines"] = list(dict.fromkeys(lines))

    def update_distance(
        self,
        source: str,
        dest: str,
        distance: int,
        line: Optional[str] = None,
    ) -> int:
        """Update the distance of the connection(s) between two stations.

        Args:
            source: one endpoint station name.
            dest: the other endpoint station name.
            distance: new distance in meters (positive integer).
            line: restrict the update to connections of this line, if given.

        Returns:
            The number of connections updated.

        Raises:
            KeyError: if no matching connection exists.
            ValueError: if the distance is invalid.
        """
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise ValueError("distance must be a positive integer (meters)")
        matched = 0
        for conn in self.data["connections"]:
            pair = {conn.get("source"), conn.get("dest")}
            if pair == {source, dest} and (line is None or conn.get("line") == line):
                conn["distance"] = distance
                matched += 1
        if matched == 0:
            raise KeyError(f"no connection between '{source}' and '{dest}'")
        return matched

    # ------------------------------------------------------------------ output
    def to_dict(self) -> Dict[str, Any]:
        """Return the (copied) dataset dictionary."""
        return copy.deepcopy(self.data)

    def save(self, path: str = DATA_FILE_PATH) -> None:
        """Persist the dataset to a JSON file."""
        save_subway_data(self.data, path)
