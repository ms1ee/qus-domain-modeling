"""Data management: adding lines, modifying stations and updating distances."""

import copy
from typing import Any, Dict, Iterable, Optional

from data_loader import DATA_FILE_PATH, build_network, parse_distance, save_subway_data
from models import SubwayNetwork


class NetworkManager:
    """Maintains the raw dataset and keeps the network model in sync with it."""

    def __init__(self, data: Dict[str, Any], data_path: str = DATA_FILE_PATH) -> None:
        self._data = copy.deepcopy(data)
        self.data_path = data_path
        self.network: SubwayNetwork = build_network(self._data)

    @property
    def data(self) -> Dict[str, Any]:
        """The raw dataset (as loaded from JSON, plus applied changes)."""
        return self._data

    def _refresh(self) -> None:
        self.network = build_network(self._data)

    def _find_station_entry(self, name: str) -> Optional[Dict[str, Any]]:
        for entry in self._data["stations"]:
            if entry.get("name") == name:
                return entry
        return None

    def add_line(self, line_name: str, station_names: Iterable[str], distances_meters: Iterable[float]) -> None:
        """Add a new line through the given ordered stations.

        Args:
            line_name: name of the new line.
            station_names: ordered station names of the line (at least 2).
            distances_meters: distance between consecutive stations (len - 1 values).

        Raises:
            ValueError: on invalid or duplicate input.
        """
        line_name = line_name.strip()
        names = [name.strip() for name in station_names]
        distances = list(distances_meters)
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.network.line_names:
            raise ValueError(f"Line '{line_name}' already exists")
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("Station names on a line must be unique")
        if len(distances) != len(names) - 1:
            raise ValueError("Exactly one distance per consecutive station pair is required")
        for distance in distances:
            if parse_distance(distance) is None:
                raise ValueError(f"Invalid distance: {distance}")

        for name in names:
            entry = self._find_station_entry(name)
            if entry is None:
                entry = {"name": name, "lines": []}
                self._data["stations"].append(entry)
            entry.setdefault("lines", [])
            if line_name not in entry["lines"]:
                entry["lines"].append(line_name)

        for index, distance in enumerate(distances):
            self._data["connections"].append(
                {
                    "source": names[index],
                    "dest": names[index + 1],
                    "distance": int(round(float(distance))),
                    "line": line_name,
                }
            )
        self._refresh()

    def modify_station(
        self,
        station_name: str,
        new_name: Optional[str] = None,
        add_lines: Iterable[str] = (),
        remove_lines: Iterable[str] = (),
    ) -> None:
        """Rename a station and/or change the lines serving it.

        Raises:
            KeyError: if the station does not exist.
            ValueError: if the new name is already used.
        """
        entry = self._find_station_entry(station_name)
        if entry is None:
            raise KeyError(f"Station '{station_name}' does not exist")
        entry.setdefault("lines", [])

        if new_name and new_name.strip() and new_name.strip() != station_name:
            new_name = new_name.strip()
            if self._find_station_entry(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self._data["connections"]:
                if conn.get("source") == station_name:
                    conn["source"] = new_name
                if conn.get("dest") == station_name:
                    conn["dest"] = new_name
            station_name = new_name

        for line in add_lines:
            line = line.strip()
            if line and line not in entry["lines"]:
                entry["lines"].append(line)
        for line in remove_lines:
            line = line.strip()
            if line in entry["lines"]:
                entry["lines"].remove(line)
        self._refresh()

    def update_distance(
        self,
        station_a: str,
        station_b: str,
        distance_meters: float,
        line: Optional[str] = None,
    ) -> int:
        """Update the distance of the connection(s) between two stations.

        Returns:
            Number of connections updated.

        Raises:
            KeyError: if no matching connection exists.
            ValueError: if the distance is invalid.
        """
        if parse_distance(distance_meters) is None:
            raise ValueError(f"Invalid distance: {distance_meters}")
        count = 0
        for conn in self._data["connections"]:
            pair = {conn.get("source"), conn.get("dest")}
            if pair != {station_a, station_b}:
                continue
            if line is not None and conn.get("line") != line:
                continue
            conn["distance"] = int(round(float(distance_meters)))
            count += 1
        if count == 0:
            raise KeyError(f"No connection between '{station_a}' and '{station_b}'")
        self._refresh()
        return count

    def save(self, path: Optional[str] = None) -> None:
        """Persist the dataset to JSON (defaults to the originally loaded path)."""
        save_subway_data(self._data, path or self.data_path)
