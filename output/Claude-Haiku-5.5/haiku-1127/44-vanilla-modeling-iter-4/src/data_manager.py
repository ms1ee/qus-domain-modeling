"""Data management: integrity checks and data update operations.

The manager works on the in-memory dataset and can save it back to the JSON file.
"""

import json
import os

from data_loader import DATA_FILE_PATH, load_subway_data
from subway_network import SubwayNetwork

# Representative stations of main lines used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Tiananmen West"],
    "Line 2": ["Xizhimen", "Chegongzhuang"],
    "Line 4": ["Beijing Zoo"],
    "Line 5": ["Songjiazhuang", "Dongsi"],
    "Line 13": ["Xi'erqi"],
}

EXPECTED_MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class DataManager:
    """Checks and updates the subway dataset.

    Attributes:
        source_file: Path of the JSON file used for loading and saving.
        data: The in-memory dataset dictionary.
        last_check_passed: Result of the most recent integrity check.
        last_issues: Issues found by the most recent integrity check.
    """

    def __init__(self, source_file=DATA_FILE_PATH, data=None):
        self.source_file = source_file
        self.data = data if data is not None else load_subway_data(source_file)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.last_check_passed = False
        self.last_issues = []

    # ------------------------------------------------------------ integrity
    def check_integrity(self):
        """Run all integrity checks.

        Returns:
            List of human-readable issue strings (empty if the data passes).
        """
        issues = []
        issues.extend(self._check_station_coverage())
        issues.extend(self._check_connections())
        issues.extend(self._check_distances())
        self.last_issues = issues
        self.last_check_passed = not issues
        return issues

    def _check_station_coverage(self):
        issues = []
        stations = self.data.get("stations", [])
        if not stations:
            issues.append("No stations are defined in the dataset")
        names = {s.get("name") for s in stations if isinstance(s, dict)}
        lines_present = set()
        for station in stations:
            if isinstance(station, dict):
                lines_present.update(station.get("lines", []))
        for connection in self.data.get("connections", []):
            if isinstance(connection, dict):
                lines_present.add(connection.get("line"))
        for line in EXPECTED_MAIN_LINES:
            if line not in lines_present:
                issues.append(f"Main line '{line}' is not covered by the station data")
        for line, representatives in REPRESENTATIVE_STATIONS.items():
            for name in representatives:
                if name not in names:
                    issues.append(f"Representative station '{name}' of {line} is missing")
        return issues

    def _check_connections(self):
        issues = []
        stations = self.data.get("stations", [])
        names = {s.get("name") for s in stations if isinstance(s, dict)}
        declared = {}
        for station in stations:
            if isinstance(station, dict):
                declared[station.get("name")] = set(station.get("lines", []))
        degree = {name: 0 for name in names}
        seen = set()
        required = ("source", "dest", "distance", "line")
        for index, connection in enumerate(self.data.get("connections", []), 1):
            if not isinstance(connection, dict):
                issues.append(f"Connection #{index} is not an object")
                continue
            missing = [key for key in required if key not in connection]
            if missing:
                issues.append(f"Connection #{index} is missing fields: {', '.join(missing)}")
                continue
            src, dst, line = connection["source"], connection["dest"], connection["line"]
            for endpoint in (src, dst):
                if endpoint not in names:
                    issues.append(f"Connection #{index} references unknown station '{endpoint}'")
            if src == dst:
                issues.append(f"Connection #{index} connects station '{src}' to itself")
            for endpoint in (src, dst):
                if endpoint in declared and line not in declared[endpoint]:
                    issues.append(
                        f"Station '{endpoint}' is connected on '{line}' but does not list that line"
                    )
            key = (frozenset((src, dst)), line)
            if key in seen:
                issues.append(f"Duplicate connection {src} - {dst} on '{line}'")
            seen.add(key)
            for endpoint in (src, dst):
                if endpoint in degree:
                    degree[endpoint] += 1
        if len(names) > 1:
            for name, count in degree.items():
                if count == 0:
                    issues.append(f"Station '{name}' has no connections")
        return issues

    def _check_distances(self):
        issues = []
        pair_distance = {}
        for index, connection in enumerate(self.data.get("connections", []), 1):
            if not isinstance(connection, dict):
                continue
            distance = connection.get("distance")
            if not _is_number(distance) or distance <= 0:
                issues.append(f"Connection #{index} has an invalid distance: {distance!r}")
                continue
            if not MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M:
                issues.append(
                    f"Connection #{index} distance {distance} m is outside the plausible range"
                )
            pair = frozenset((connection.get("source"), connection.get("dest")))
            if pair in pair_distance and pair_distance[pair] != distance:
                issues.append(
                    f"Inconsistent distances for {connection.get('source')} - "
                    f"{connection.get('dest')}: {pair_distance[pair]} vs {distance}"
                )
            pair_distance.setdefault(pair, distance)
        return issues

    # ------------------------------------------------------------ updates
    def all_lines(self):
        """Return the set of all line names in the dataset."""
        lines = set()
        for station in self.data.get("stations", []):
            lines.update(station.get("lines", []))
        for connection in self.data.get("connections", []):
            lines.add(connection.get("line"))
        return lines

    def _find_station(self, name):
        for station in self.data.get("stations", []):
            if station.get("name") == name:
                return station
        return None

    def add_line(self, line_name, station_names, distances_m):
        """Add a new line with an ordered station sequence.

        Args:
            line_name: Name of the new line (must not exist yet).
            station_names: Ordered station names (at least two, no duplicates).
            distances_m: Distances in meters between consecutive stations.

        Returns:
            Number of connections added.

        Raises:
            ValueError: If the input is invalid.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self.all_lines():
            raise ValueError(f"Line '{line_name}' already exists")
        names = [str(name).strip() for name in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("a line cannot contain duplicate stations")
        if len(distances_m) != len(names) - 1:
            raise ValueError("expected one distance per consecutive station pair")
        for distance in distances_m:
            if not _is_number(distance) or distance <= 0:
                raise ValueError(f"invalid distance: {distance!r}")

        stations = self.data["stations"]
        for name in names:
            entry = self._find_station(name)
            if entry is None:
                stations.append({"name": name, "lines": [line_name]})
            elif line_name not in entry.setdefault("lines", []):
                entry["lines"].append(line_name)

        connections = self.data["connections"]
        for index, distance in enumerate(distances_m):
            connections.append({
                "source": names[index],
                "dest": names[index + 1],
                "distance": int(round(distance)),
                "line": line_name,
            })
        return len(distances_m)

    def modify_station(self, name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name is empty or already used.
        """
        entry = self._find_station(name)
        if entry is None:
            raise KeyError(f"Station '{name}' not found")
        if new_name is not None:
            new_name = str(new_name).strip()
            if not new_name:
                raise ValueError("new station name must not be empty")
            if new_name != name and self._find_station(new_name) is not None:
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for connection in self.data["connections"]:
                if connection.get("source") == name:
                    connection["source"] = new_name
                if connection.get("dest") == name:
                    connection["dest"] = new_name
        if lines is not None:
            entry["lines"] = list(dict.fromkeys(str(line) for line in lines))
        return entry

    def update_distance(self, station_a, station_b, distance_m, line=None):
        """Update the distance of connections between two stations.

        Returns:
            Number of connections updated.

        Raises:
            ValueError: If the distance is not positive.
            KeyError: If no matching connection exists.
        """
        if not _is_number(distance_m) or distance_m <= 0:
            raise ValueError("distance must be a positive number")
        updated = 0
        pair = {station_a, station_b}
        for connection in self.data["connections"]:
            if {connection.get("source"), connection.get("dest")} == pair and (
                line is None or connection.get("line") == line
            ):
                connection["distance"] = int(round(distance_m))
                updated += 1
        if updated == 0:
            raise KeyError(f"No connection between '{station_a}' and '{station_b}'")
        return updated

    def save(self, path=None):
        """Write the dataset to ``path`` (defaults to the source file)."""
        target = path or self.source_file
        directory = os.path.dirname(os.path.abspath(target))
        os.makedirs(directory, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
        return target

    def build_network(self):
        """Build a SubwayNetwork from the current in-memory data."""
        return SubwayNetwork(self.data)
