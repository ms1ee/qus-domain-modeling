"""Data integrity checks and data update operations for the subway dataset.

All operations work on the raw dataset dictionary (the content of subway_data.json).
Call build_network() afterwards to obtain an updated SubwayNetwork.
"""

from collections import deque

from models import SubwayNetwork

MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

# Representative stations expected on each main line (coverage check).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "复兴门", "国贸"],
    "Line 2": ["西直门", "车公庄", "建国门"],
    "Line 4": ["圆明园", "西单", "北京南站"],
    "Line 5": ["天通苑北", "东单", "宋家庄"],
    "Line 6": ["海淀五路居", "北海北", "草房"],
    "Line 8": ["朱辛庄", "鼓楼大街"],
    "Line 10": ["巴沟", "国贸", "亮马桥"],
    "Line 13": ["西直门", "东直门"],
    "Line 14": ["张郭庄"],
    "Line 15": ["后沙峪"],
    "Changping Line": ["昌平营", "西二旗"],
    "Yizhuang Line": ["宋家庄", "亦庄火车站"],
    "Fangshan Line": ["郭公庄", "苏庄"],
    "Airport Line": ["T3航站楼"],
}

# Plausible range of inter-station distances in meters (warnings outside this range).
MIN_PLAUSIBLE_DISTANCE_M = 200
MAX_PLAUSIBLE_DISTANCE_M = 6000


class DataUpdateError(ValueError):
    """Raised when a data update request is invalid."""


class IntegrityReport:
    """Result of a data integrity check.

    Attributes:
        errors: List of error messages (cause the check to fail).
        warnings: List of warning messages (informational).
        checks_run: Names of the checks that were executed.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_run = []

    @property
    def passed(self):
        """True if no errors were found."""
        return not self.errors

    def format(self):
        """Return a human-readable report."""
        lines = ["Data integrity check"]
        lines.append("Checks run: " + ", ".join(self.checks_run))
        if not self.errors and not self.warnings:
            lines.append("  All checks passed without issues.")
        for message in self.errors:
            lines.append(f"  [ERROR] {message}")
        for message in self.warnings:
            lines.append(f"  [WARN] {message}")
        lines.append("Result: " + ("PASSED" if self.passed else "FAILED"))
        return "\n".join(lines)


class DataManager:
    """Integrity checking and updating of the raw subway dataset."""

    def __init__(self, data):
        """Wrap a dataset dictionary.

        Args:
            data: dict with 'stations' and 'connections' lists (modified in place).
        """
        self.data = data
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    # ------------------------------------------------------------------ helpers
    def _stations(self):
        return self.data["stations"]

    def _connections(self):
        return self.data["connections"]

    def _find_station(self, name):
        for station in self._stations():
            if station.get("name") == name:
                return station
        return None

    def build_network(self):
        """Build a SubwayNetwork from the current dataset."""
        return SubwayNetwork.from_data(self.data)

    # ------------------------------------------------------------ integrity
    def check_integrity(self):
        """Run all integrity checks.

        Returns:
            IntegrityReport: The collected errors and warnings.
        """
        report = IntegrityReport()
        self._check_station_data(report)
        self._check_coverage(report)
        self._check_connections(report)
        self._check_distances(report)
        return report

    def _check_station_data(self, report):
        report.checks_run.append("station data")
        seen = set()
        for index, station in enumerate(self._stations()):
            name = station.get("name")
            if not isinstance(name, str) or not name.strip():
                report.errors.append(f"station entry #{index} has no valid name")
                continue
            if name in seen:
                report.errors.append(f"duplicate station name '{name}'")
            seen.add(name)
            if not station.get("lines"):
                report.warnings.append(f"station '{name}' has no line information")

    def _check_coverage(self, report):
        report.checks_run.append("station coverage")
        covered_lines = set()
        names = set()
        for station in self._stations():
            names.add(station.get("name"))
            covered_lines.update(station.get("lines", []))
        for line in MAIN_LINES:
            if line not in covered_lines:
                report.errors.append(f"main line '{line}' has no stations in the dataset")
        for line, representatives in REPRESENTATIVE_STATIONS.items():
            for name in representatives:
                if name not in names:
                    report.warnings.append(f"representative station '{name}' of {line} is missing")

    def _check_connections(self, report):
        report.checks_run.append("connection integrity")
        names = {station.get("name"): set(station.get("lines", [])) for station in self._stations()}
        adjacency = {name: set() for name in names}
        seen_pairs = {}
        for index, conn in enumerate(self._connections()):
            missing = [key for key in ("source", "dest", "distance", "line") if key not in conn]
            if missing:
                report.errors.append(f"connection #{index} is missing fields {missing}")
                continue
            source, dest, line = conn["source"], conn["dest"], conn["line"]
            if source not in names or dest not in names:
                report.errors.append(f"connection {source} -> {dest} references an unknown station")
                continue
            if source == dest:
                report.errors.append(f"connection starts and ends at the same station '{source}'")
                continue
            for endpoint in (source, dest):
                if line not in names[endpoint]:
                    report.warnings.append(f"station '{endpoint}' is not listed on line '{line}'")
            key = (frozenset((source, dest)), line)
            if key in seen_pairs:
                if seen_pairs[key] != conn.get("distance"):
                    report.errors.append(f"conflicting distances for {source} - {dest} on {line}")
                else:
                    report.warnings.append(f"duplicate connection {source} - {dest} on {line}")
            else:
                seen_pairs[key] = conn.get("distance")
            adjacency[source].add(dest)
            adjacency[dest].add(source)

        isolated = [name for name, neighbours in adjacency.items() if not neighbours]
        for name in isolated:
            report.warnings.append(f"station '{name}' has no connections")

        components = self._count_components(adjacency)
        if components > 1:
            report.warnings.append(f"the network consists of {components} disconnected components")

    @staticmethod
    def _count_components(adjacency):
        remaining = set(adjacency)
        components = 0
        while remaining:
            components += 1
            start = remaining.pop()
            queue = deque([start])
            while queue:
                node = queue.popleft()
                for neighbour in adjacency.get(node, ()):
                    if neighbour in remaining:
                        remaining.discard(neighbour)
                        queue.append(neighbour)
        return components

    def _check_distances(self, report):
        report.checks_run.append("distance accuracy")
        for index, conn in enumerate(self._connections()):
            distance = conn.get("distance")
            label = f"{conn.get('source')} - {conn.get('dest')}"
            if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
                report.errors.append(f"invalid distance for {label}: {distance!r}")
                continue
            if distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
                report.warnings.append(
                    f"distance {distance} m for {label} is outside the plausible range "
                    f"[{MIN_PLAUSIBLE_DISTANCE_M}, {MAX_PLAUSIBLE_DISTANCE_M}] m"
                )

    # ------------------------------------------------------------- updates
    def add_line(self, line_name, station_names, distances):
        """Add a new line through an ordered list of stations.

        Existing stations are reused (and gain the new line); missing stations are created.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names along the line.
            distances: List of distances in meters between consecutive stations.

        Returns:
            int: Number of connections added.

        Raises:
            DataUpdateError: If the request is invalid.
        """
        line_name = (line_name or "").strip()
        if not line_name:
            raise DataUpdateError("line name must not be empty")
        for station in self._stations():
            if line_name in station.get("lines", []):
                raise DataUpdateError(f"line '{line_name}' already exists")
        names = [str(name).strip() for name in station_names]
        if len(names) < 2 or any(not name for name in names):
            raise DataUpdateError("a line needs at least two non-empty station names")
        if len(set(names)) != len(names):
            raise DataUpdateError("station names on a line must be unique")
        if len(distances) != len(names) - 1:
            raise DataUpdateError("exactly one distance per consecutive station pair is required")
        for distance in distances:
            self._validate_distance(distance)

        for name in names:
            station = self._find_station(name)
            if station is None:
                self._stations().append({"name": name, "lines": [line_name]})
            else:
                station.setdefault("lines", [])
                if line_name not in station["lines"]:
                    station["lines"].append(line_name)
        for index, distance in enumerate(distances):
            self._connections().append({
                "source": names[index],
                "dest": names[index + 1],
                "distance": int(distance),
                "line": line_name,
            })
        return len(distances)

    def modify_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its lines.

        Renaming also updates all connections that reference the station.

        Args:
            name: Current station name.
            new_name: Optional new name.
            lines: Optional new list of lines.

        Returns:
            dict: The updated station entry.

        Raises:
            DataUpdateError: If the station does not exist or the request is invalid.
        """
        station = self._find_station(name)
        if station is None:
            raise DataUpdateError(f"station '{name}' does not exist")
        if lines is not None:
            if not isinstance(lines, (list, tuple)) or not lines or not all(isinstance(x, str) and x.strip() for x in lines):
                raise DataUpdateError("lines must be a non-empty list of line names")
            station["lines"] = [x.strip() for x in lines]
        if new_name is not None and new_name.strip() != name:
            new_name = new_name.strip()
            if not new_name:
                raise DataUpdateError("new station name must not be empty")
            if self._find_station(new_name) is not None:
                raise DataUpdateError(f"station '{new_name}' already exists")
            station["name"] = new_name
            for conn in self._connections():
                if conn.get("source") == name:
                    conn["source"] = new_name
                if conn.get("dest") == name:
                    conn["dest"] = new_name
        return station

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) between two adjacent stations.

        Args:
            source: One station name.
            dest: The adjacent station name.
            distance: New distance in meters.
            line: Optional line name to restrict the update.

        Returns:
            int: Number of connections updated.

        Raises:
            DataUpdateError: If no matching connection exists or the distance is invalid.
        """
        self._validate_distance(distance)
        matches = [
            conn for conn in self._connections()
            if {conn.get("source"), conn.get("dest")} == {source, dest}
            and (line is None or conn.get("line") == line)
        ]
        if not matches:
            raise DataUpdateError(f"no connection between '{source}' and '{dest}'")
        for conn in matches:
            conn["distance"] = int(distance)
        return len(matches)

    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise DataUpdateError(f"distance must be a positive number of meters, got {distance!r}")
