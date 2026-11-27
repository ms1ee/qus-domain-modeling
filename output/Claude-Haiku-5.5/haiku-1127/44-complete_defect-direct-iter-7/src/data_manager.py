"""Data update operations: adding lines, modifying stations and updating distances.

All operations work on a private deep copy of the data dictionary, so a failed
update never leaves the data in a partially modified state. Use ``build_network``
on the result to obtain an updated network model.
"""

import copy

from data_loader import save_subway_data
from subway_network import build_network


class DataUpdateError(ValueError):
    """Raised when a requested data update is invalid."""


def _valid_distance(distance):
    """Validate a distance in meters (positive integer)."""
    if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
        raise DataUpdateError("distance must be a positive integer number of meters")
    return distance


class DataManager:
    """Manages updates to the subway network data dictionary."""

    def __init__(self, data):
        self._data = copy.deepcopy(data)
        self._data.setdefault("stations", [])
        self._data.setdefault("connections", [])

    @property
    def data(self):
        """Return a deep copy of the current data dictionary."""
        return copy.deepcopy(self._data)

    def _find_station(self, name):
        for station in self._data["stations"]:
            if station["name"] == name:
                return station
        return None

    def _existing_lines(self):
        lines = set()
        for station in self._data["stations"]:
            lines.update(station.get("lines", []))
        for conn in self._data["connections"]:
            lines.add(conn["line"])
        return lines

    def add_line(self, line_name, station_names, distances):
        """Add a new line.

        ``station_names`` is the ordered list of stations on the line, and
        ``distances`` contains the distance (meters) between consecutive stations.
        Existing stations are linked to the new line; new stations are created.
        """
        line_name = " ".join(str(line_name).split())
        if not line_name:
            raise DataUpdateError("line name must not be empty")
        if line_name in self._existing_lines():
            raise DataUpdateError(f"line '{line_name}' already exists")
        if len(station_names) < 2:
            raise DataUpdateError("a line needs at least two stations")
        if len(set(station_names)) != len(station_names):
            raise DataUpdateError("a line cannot contain duplicate stations")
        if len(distances) != len(station_names) - 1:
            raise DataUpdateError("number of distances must be one less than number of stations")
        for distance in distances:
            _valid_distance(distance)

        for name in station_names:
            station = self._find_station(name)
            if station is None:
                self._data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in station.get("lines", []):
                station.setdefault("lines", []).append(line_name)

        for index, distance in enumerate(distances):
            self._data["connections"].append({
                "source": station_names[index],
                "dest": station_names[index + 1],
                "distance": distance,
                "line": line_name,
            })

    def modify_station(self, old_name, new_name=None, add_lines=None, remove_lines=None):
        """Rename a station and/or add or remove lines serving it."""
        station = self._find_station(old_name)
        if station is None:
            raise DataUpdateError(f"station '{old_name}' does not exist")

        if new_name and new_name != old_name:
            new_name = " ".join(new_name.split())
            if self._find_station(new_name) is not None:
                raise DataUpdateError(f"station '{new_name}' already exists")
            station["name"] = new_name
            for conn in self._data["connections"]:
                if conn["source"] == old_name:
                    conn["source"] = new_name
                if conn["dest"] == old_name:
                    conn["dest"] = new_name

        lines = station.setdefault("lines", [])
        for line in add_lines or []:
            if line not in lines:
                lines.append(line)
        for line in remove_lines or []:
            if line in lines:
                lines.remove(line)

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of connections between two stations.

        If ``line`` is given, only the connection on that line is updated.
        Returns the number of connections updated.
        """
        _valid_distance(distance)
        updated = 0
        for conn in self._data["connections"]:
            same_pair = {conn["source"], conn["dest"]} == {source, dest}
            if same_pair and (line is None or conn["line"] == line):
                conn["distance"] = distance
                updated += 1
        if updated == 0:
            raise DataUpdateError(f"no connection between '{source}' and '{dest}'")
        return updated

    def build_network(self):
        """Return a SubwayNetwork built from the current data."""
        return build_network(self._data)

    def save(self, path):
        """Persist the current data to a JSON file."""
        save_subway_data(self._data, path)
