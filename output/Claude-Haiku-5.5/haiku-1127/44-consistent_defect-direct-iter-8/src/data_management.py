"""Data integrity checks and data update operations for the subway dataset."""

import copy
import json

from data_loader import load_subway_data

REQUIRED_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_SEGMENT_METERS = 100
MAX_SEGMENT_METERS = 10000


class IntegrityReport:
    """Result of an integrity check."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def passed(self) -> bool:
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def render(self) -> str:
        """Return a printable multi-line report."""
        lines = ["Data integrity check"]
        if not self.errors and not self.warnings:
            lines.append("  No problems found.")
        for error in self.errors:
            lines.append(f"  [ERROR] {error}")
        for warning in self.warnings:
            lines.append(f"  [WARNING] {warning}")
        lines.append("Result: " + ("PASSED" if self.passed else "FAILED"))
        return "\n".join(lines)


class DataManager:
    """Manages the raw subway dataset (in memory) with checks and updates."""

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    @classmethod
    def from_file(cls, path):
        """Create a manager from a JSON dataset file."""
        return cls(load_subway_data(path))

    # ------------------------------------------------------------ integrity
    def check_integrity(self) -> IntegrityReport:
        """Validate station coverage, connection integrity and distance accuracy."""
        report = IntegrityReport()
        stations = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        station_names = set()
        station_lines = {}
        for station in stations:
            name = station.get("name")
            if not name:
                report.errors.append("station entry without a name")
                continue
            if name in station_names:
                report.errors.append(f"duplicate station name '{name}'")
            station_names.add(name)
            station_lines.setdefault(name, set()).update(station.get("lines", []))
            if not station.get("lines"):
                report.warnings.append(f"station '{name}' has no lines")

        # Coverage of main lines.
        covered = set()
        for lines in station_lines.values():
            covered.update(lines)
        for connection in connections:
            covered.add(connection.get("line"))
        for required in REQUIRED_LINES:
            if required not in covered:
                report.warnings.append(f"coverage: main line '{required}' is not represented")

        # Connection integrity and distance accuracy.
        seen = set()
        for connection in connections:
            source = connection.get("source")
            dest = connection.get("dest")
            line = connection.get("line")
            distance = connection.get("distance")
            if source is None or dest is None or line is None or distance is None:
                report.errors.append(f"connection with missing fields: {connection}")
                continue
            if source not in station_names:
                report.errors.append(f"connection references unknown station '{source}'")
            if dest not in station_names:
                report.errors.append(f"connection references unknown station '{dest}'")
            if source == dest:
                report.errors.append(f"self-loop connection at station '{source}'")
            if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
                report.errors.append(
                    f"invalid distance {distance!r} between '{source}' and '{dest}'")
            elif not MIN_SEGMENT_METERS <= distance <= MAX_SEGMENT_METERS:
                report.warnings.append(
                    f"suspicious distance {distance} m between '{source}' and '{dest}'")
            if line not in station_lines.get(source, set()) or \
                    line not in station_lines.get(dest, set()):
                report.warnings.append(
                    f"line '{line}' is not listed for both '{source}' and '{dest}'")
            key = (source, dest, line)
            if key in seen:
                report.warnings.append(
                    f"duplicate connection '{source}' -> '{dest}' on '{line}'")
            seen.add(key)

        for source, dest, line in sorted(seen, key=str):
            if (dest, source, line) not in seen:
                report.warnings.append(
                    f"connection '{source}' -> '{dest}' on '{line}' has no reverse direction")
        return report

    # -------------------------------------------------------------- updates
    def _find_station(self, name):
        for station in self.data["stations"]:
            if station.get("name") == name:
                return station
        return None

    def add_line(self, line_name, station_names, distances, bidirectional=True):
        """Add a new line from an ordered station list and segment distances.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations.
            bidirectional: Whether to add the reverse direction as well.

        Raises:
            ValueError: On invalid input or if the line already exists.
        """
        if not line_name:
            raise ValueError("line name must not be empty")
        if len(station_names) < 2:
            raise ValueError("a line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("one distance is required per consecutive station pair")
        for distance in distances:
            if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
                raise ValueError(f"invalid distance {distance!r}")
        for connection in self.data["connections"]:
            if connection.get("line") == line_name:
                raise ValueError(f"line '{line_name}' already exists")

        for name in station_names:
            station = self._find_station(name)
            if station is None:
                self.data["stations"].append({"name": name, "lines": [line_name]})
            elif line_name not in station.setdefault("lines", []):
                station["lines"].append(line_name)

        for index, distance in enumerate(distances):
            source, dest = station_names[index], station_names[index + 1]
            self.data["connections"].append(
                {"source": source, "dest": dest, "distance": distance, "line": line_name})
            if bidirectional:
                self.data["connections"].append(
                    {"source": dest, "dest": source, "distance": distance, "line": line_name})

    def update_station(self, name, lines=None, new_name=None):
        """Modify a station's lines and/or rename it.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name is already used.
        """
        station = self._find_station(name)
        if station is None:
            raise KeyError(f"station '{name}' does not exist")
        if lines is not None:
            station["lines"] = list(lines)
        if new_name and new_name != name:
            if self._find_station(new_name) is not None:
                raise ValueError(f"station '{new_name}' already exists")
            station["name"] = new_name
            for connection in self.data["connections"]:
                if connection.get("source") == name:
                    connection["source"] = new_name
                if connection.get("dest") == name:
                    connection["dest"] = new_name

    def update_distance(self, source, dest, distance, line=None, bidirectional=True):
        """Update the distance of an existing connection.

        Raises:
            ValueError: If the distance is invalid.
            KeyError: If no matching connection exists.
        """
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            raise ValueError(f"invalid distance {distance!r}")
        updated = 0
        for connection in self.data["connections"]:
            if line is not None and connection.get("line") != line:
                continue
            forward = connection.get("source") == source and connection.get("dest") == dest
            backward = bidirectional and connection.get("source") == dest \
                and connection.get("dest") == source
            if forward or backward:
                connection["distance"] = distance
                updated += 1
        if updated == 0:
            raise KeyError(f"no connection between '{source}' and '{dest}'")

    def save(self, path):
        """Write the dataset to a JSON file."""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
