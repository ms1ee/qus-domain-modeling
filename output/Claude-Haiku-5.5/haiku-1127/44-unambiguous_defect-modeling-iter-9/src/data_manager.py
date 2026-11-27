"""Data management: loading, updating and saving the subway dataset."""

import datetime

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import SubwayNetwork, _clean


class DataUpdateError(Exception):
    """Raised when a requested data update is invalid."""


def _validate_distance(value):
    """Return a positive integer distance in meters or raise DataUpdateError."""
    if isinstance(value, bool):
        raise DataUpdateError("Distance must be a positive number of meters")
    try:
        distance = float(value)
    except (TypeError, ValueError) as exc:
        raise DataUpdateError(f"Invalid distance: {value!r}") from exc
    if distance <= 0:
        raise DataUpdateError("Distance must be positive")
    return int(round(distance))


class DataManager:
    """Owns the raw subway dataset and the SubwayNetwork built from it.

    Every update rebuilds the network so that graph, station numbers and
    lookups stay consistent with the raw data.
    """

    def __init__(self, data_file_path=DATA_FILE_PATH, data=None):
        self.data_file_path = data_file_path
        self.raw_data = data if data is not None else load_subway_data(data_file_path)
        self.last_updated = datetime.datetime.now()
        self.network = SubwayNetwork(self.raw_data)

    def _rebuild(self):
        self.network = SubwayNetwork(self.raw_data)
        self.last_updated = datetime.datetime.now()

    def _find_station(self, name):
        for entry in self.raw_data["stations"]:
            if _clean(entry.get("name")) == name:
                return entry
        return None

    def add_line(self, line_name, station_names, distances):
        """Add a new line through an ordered list of stations.

        Stations that do not yet exist are created. ``distances`` gives the
        distance in meters between each pair of consecutive stations.

        Raises:
            DataUpdateError: if the input is invalid.
        """
        line = _clean(line_name)
        if not line:
            raise DataUpdateError("Line name must not be empty")
        if line in self.network.line_names():
            raise DataUpdateError(f"Line '{line}' already exists")
        names = [_clean(name) for name in station_names]
        if len(names) < 2 or any(not name for name in names):
            raise DataUpdateError("A line needs at least two non-empty station names")
        if len(set(names)) != len(names):
            raise DataUpdateError("A line cannot visit the same station twice")
        if len(distances) != len(names) - 1:
            raise DataUpdateError("Expected one distance per pair of consecutive stations")
        checked = [_validate_distance(d) for d in distances]

        for name in names:
            entry = self._find_station(name)
            if entry is None:
                self.raw_data["stations"].append({"name": name, "lines": [line]})
            elif line not in entry.get("lines", []):
                entry.setdefault("lines", []).append(line)
        for i, distance in enumerate(checked):
            self.raw_data["connections"].append({
                "source": names[i],
                "dest": names[i + 1],
                "distance": distance,
                "line": line,
            })
        self._rebuild()

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its list of lines.

        Raises:
            DataUpdateError: if the station does not exist or the new name is taken.
        """
        old = _clean(old_name)
        entry = self._find_station(old)
        if entry is None:
            raise DataUpdateError(f"Station '{old}' does not exist")
        if lines is not None:
            unique = []
            for line in lines:
                cleaned = _clean(line)
                if cleaned and cleaned not in unique:
                    unique.append(cleaned)
            if not unique:
                raise DataUpdateError("A station must belong to at least one line")
            entry["lines"] = unique
        if new_name is not None:
            target = _clean(new_name)
            if not target:
                raise DataUpdateError("New station name must not be empty")
            if target != old:
                if self._find_station(target) is not None:
                    raise DataUpdateError(f"Station '{target}' already exists")
                entry["name"] = target
                for conn in self.raw_data["connections"]:
                    if _clean(conn.get("source")) == old:
                        conn["source"] = target
                    if _clean(conn.get("dest")) == old:
                        conn["dest"] = target
        self._rebuild()

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two stations.

        Args:
            source, dest: station names.
            distance: new distance in meters (positive).
            line: restrict the update to connections on this line (optional).

        Returns:
            number of connections updated.

        Raises:
            DataUpdateError: if no matching connection exists.
        """
        value = _validate_distance(distance)
        src = _clean(source)
        dst = _clean(dest)
        matched = []
        for conn in self.raw_data["connections"]:
            pair = {_clean(conn.get("source")), _clean(conn.get("dest"))}
            if pair == {src, dst} and (line is None or _clean(conn.get("line")) == _clean(line)):
                matched.append(conn)
        if not matched:
            raise DataUpdateError(f"No connection found between '{src}' and '{dst}'")
        for conn in matched:
            conn["distance"] = value
        self._rebuild()
        return len(matched)

    def save(self, path=None):
        """Persist the current dataset to ``path`` (defaults to the loaded file)."""
        save_subway_data(self.raw_data, path or self.data_file_path)
