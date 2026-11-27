"""Data integrity checks and data update operations for the subway dataset."""

import copy

from data_loader import DATA_FILE_PATH, save_subway_data
from network import normalize_station_name

# Representative stations of main lines used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Tiananmen East"],
    "Line 2": ["Xizhimen", "Jianguomen"],
    "Line 4": ["Beijing Zoo"],
    "Line 5": ["Songjiazhuang"],
    "Line 6": ["Beijing West Railway Station"],
}

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


class DataUpdateError(Exception):
    """Raised when a requested data update is invalid."""


def _station_names(data):
    return {normalize_station_name(entry.get("name")) for entry in data.get("stations", [])}


def check_data_integrity(data):
    """Run data integrity checks.

    Returns:
        list of (severity, message) tuples where severity is "ERROR" or "WARNING".
    """
    issues = []
    stations = data.get("stations", [])
    connections = data.get("connections", [])
    station_names = _station_names(data)

    station_lines = {}
    for entry in stations:
        name = normalize_station_name(entry.get("name"))
        lines = set(entry.get("lines", []))
        station_lines.setdefault(name, set()).update(lines)
        if not lines:
            issues.append(("WARNING", f"Station '{name}' has no line information"))

    all_lines = set()
    for lines in station_lines.values():
        all_lines.update(lines)
    for conn in connections:
        all_lines.add(conn.get("line"))

    # Coverage of main lines.
    for line, representatives in REPRESENTATIVE_STATIONS.items():
        if line not in all_lines:
            issues.append(("WARNING", f"Main line '{line}' is not present in the data"))
        for rep in representatives:
            if rep not in station_names:
                issues.append(("WARNING", f"Representative station '{rep}' of {line} is missing"))

    # Connection integrity and distance accuracy.
    connection_keys = set()
    for conn in connections:
        source = normalize_station_name(conn.get("source"))
        dest = normalize_station_name(conn.get("dest"))
        line = conn.get("line")
        distance = conn.get("distance")
        label = f"{source} -> {dest} ({line})"

        if source not in station_names:
            issues.append(("ERROR", f"Connection source '{source}' is not a known station"))
        if dest not in station_names:
            issues.append(("ERROR", f"Connection destination '{dest}' is not a known station"))
        if source == dest:
            issues.append(("ERROR", f"Self-loop connection at '{source}'"))

        if not isinstance(distance, int) or isinstance(distance, bool):
            issues.append(("ERROR", f"Connection {label} has non-integer distance {distance!r}"))
        elif not MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M:
            issues.append(("WARNING", f"Connection {label} has implausible distance {distance} m"))

        if line and line not in station_lines.get(source, set()):
            issues.append(("WARNING", f"Station '{source}' is not listed on line '{line}'"))
        if line and line not in station_lines.get(dest, set()):
            issues.append(("WARNING", f"Station '{dest}' is not listed on line '{line}'"))

        key = (source, dest, line)
        if key in connection_keys:
            issues.append(("WARNING", f"Duplicate connection {label}"))
        connection_keys.add(key)

    # Bidirectional consistency (warning only: the graph is directed).
    for source, dest, line in connection_keys:
        if (dest, source, line) not in connection_keys:
            issues.append(("WARNING", f"No reverse connection for {source} -> {dest} ({line})"))

    return issues


def format_integrity_report(issues):
    """Format integrity check results as text."""
    if not issues:
        return "Data integrity check passed: no issues found."
    lines = ["Data integrity check results:"]
    for severity, message in issues:
        lines.append(f"  [{severity}] {message}")
    errors = sum(1 for severity, _ in issues if severity == "ERROR")
    warnings = len(issues) - errors
    lines.append(f"Summary: {errors} error(s), {warnings} warning(s)")
    return "\n".join(lines)


class DataManager:
    """Supports adding lines, modifying stations and updating distances.

    All operations act on an internal copy of the dataset. Call to_dict() or
    save() to obtain the result.
    """

    def __init__(self, data):
        self.data = copy.deepcopy(data)

    def _station_entry(self, name):
        for entry in self.data["stations"]:
            if normalize_station_name(entry.get("name")) == name:
                return entry
        return None

    def add_line(self, line_name, station_names, distances):
        """Add a new line with an ordered station sequence.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances: Distances in meters between consecutive stations
                (length must be len(station_names) - 1).
        """
        line_name = (line_name or "").strip()
        if not line_name:
            raise DataUpdateError("Line name must not be empty")
        if any(conn.get("line") == line_name for conn in self.data["connections"]):
            raise DataUpdateError(f"Line '{line_name}' already exists")
        names = [normalize_station_name(name) for name in station_names]
        if len(names) < 2:
            raise DataUpdateError("A line needs at least two stations")
        if len(distances) != len(names) - 1:
            raise DataUpdateError("Number of distances must be one less than number of stations")
        for distance in distances:
            if not isinstance(distance, int) or distance <= 0:
                raise DataUpdateError(f"Invalid distance {distance!r}; must be a positive integer")

        for name in names:
            entry = self._station_entry(name)
            if entry is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in entry.setdefault("lines", []):
                entry["lines"].append(line_name)

        for index, distance in enumerate(distances):
            a, b = names[index], names[index + 1]
            self.data["connections"].append(
                {"source": a, "dest": b, "distance": distance, "line": line_name}
            )
            self.data["connections"].append(
                {"source": b, "dest": a, "distance": distance, "line": line_name}
            )

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list."""
        old_name = normalize_station_name(old_name)
        entry = self._station_entry(old_name)
        if entry is None:
            raise DataUpdateError(f"Station '{old_name}' does not exist")
        if new_name is not None:
            new_name = normalize_station_name(new_name)
            if not new_name:
                raise DataUpdateError("New station name must not be empty")
            if new_name != old_name and self._station_entry(new_name) is not None:
                raise DataUpdateError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self.data["connections"]:
                if normalize_station_name(conn.get("source")) == old_name:
                    conn["source"] = new_name
                if normalize_station_name(conn.get("dest")) == old_name:
                    conn["dest"] = new_name
        if lines is not None:
            entry["lines"] = [str(line) for line in lines]

    def update_distance(self, source, dest, distance, bidirectional=True):
        """Update the distance between two adjacent stations.

        Returns:
            int: Number of connection records updated.
        """
        source = normalize_station_name(source)
        dest = normalize_station_name(dest)
        if not isinstance(distance, int) or distance <= 0:
            raise DataUpdateError("Distance must be a positive integer (meters)")
        count = 0
        for conn in self.data["connections"]:
            forward = (normalize_station_name(conn.get("source")) == source
                       and normalize_station_name(conn.get("dest")) == dest)
            backward = bidirectional and (
                normalize_station_name(conn.get("source")) == dest
                and normalize_station_name(conn.get("dest")) == source)
            if forward or backward:
                conn["distance"] = distance
                count += 1
        if count == 0:
            raise DataUpdateError(f"No connection between '{source}' and '{dest}'")
        return count

    def to_dict(self):
        """Return a copy of the updated dataset."""
        return copy.deepcopy(self.data)

    def save(self, path=DATA_FILE_PATH):
        """Persist the updated dataset to a JSON file."""
        save_subway_data(self.data, path)
