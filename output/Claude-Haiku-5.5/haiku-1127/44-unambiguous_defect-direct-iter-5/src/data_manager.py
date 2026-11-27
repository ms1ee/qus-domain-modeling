"""Data management: integrity checks and data update operations.

All updates are applied to a deep copy of the dataset first; the network is
rebuilt from the copy and only then committed, so a failed update never
leaves the data in a half-modified state.
"""

import copy
import json
import os

from data_loader import DATA_FILE_PATH, load_subway_data
from errors import DataError, DataUpdateError
from network import build_network, natural_sort_key

# Main lines that the dataset is expected to cover.
REQUIRED_MAIN_LINES = (
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
)

# Representative stations that should appear in the dataset.
REPRESENTATIVE_STATIONS = (
    "苹果园",
    "西直门",
    "建国门",
    "天安门东",
    "王府井",
    "西单",
    "国贸",
    "东单",
    "北京南站",
    "圆明园",
)

# Distances outside this range (meters) are reported as suspicious.
DISTANCE_WARN_MIN_M = 200
DISTANCE_WARN_MAX_M = 4000


class IntegrityReport:
    """Collects notes, warnings and errors produced by an integrity check."""

    def __init__(self):
        self.notes = []
        self.warnings = []
        self.errors = []

    @property
    def is_ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def render(self):
        """Return the report as a multi-line string."""
        out = ["Data integrity check report", "=" * 30]
        out.extend(f"[INFO]    {note}" for note in self.notes)
        out.extend(f"[WARNING] {warning}" for warning in self.warnings)
        out.extend(f"[ERROR]   {error}" for error in self.errors)
        status = "PASSED" if self.is_ok else "FAILED"
        out.append(
            f"Result: {status} ({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join(out)


def _count_components(adjacency):
    """Count connected components of an adjacency mapping node -> set(node)."""
    seen = set()
    count = 0
    for start in adjacency:
        if start in seen:
            continue
        count += 1
        seen.add(start)
        stack = [start]
        while stack:
            node = stack.pop()
            for neighbour in adjacency.get(node, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
    return count


def _valid_distance(value):
    """Return True if the value is a positive integer number of meters."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


class SubwayDataManager:
    """Owns the raw dataset and the network built from it."""

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data(DATA_FILE_PATH)
        self.data = copy.deepcopy(data)
        self._validate_structure(self.data)
        self.network = build_network(self.data)

    # ----- helpers ------------------------------------------------------

    @staticmethod
    def _validate_structure(data):
        if not isinstance(data, dict):
            raise DataError("subway data must be a dictionary")
        if not isinstance(data.get("stations"), list) or not isinstance(data.get("connections"), list):
            raise DataError("subway data must contain 'stations' and 'connections' lists")

    def _commit(self, candidate):
        """Build the network from a candidate dataset and make it current."""
        network = build_network(candidate)  # raises DataError before any change
        self.data = candidate
        self.network = network

    @staticmethod
    def _find_station(data, name):
        for station in data["stations"]:
            if isinstance(station, dict) and station.get("name") == name:
                return station
        return None

    # ----- update operations -------------------------------------------

    def add_line(self, line_name, station_names, distances):
        """Add a new line made of consecutive stations.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations.

        Raises:
            DataUpdateError: If the line already exists or the input is invalid.
        """
        if not isinstance(line_name, str) or not line_name.strip():
            raise DataUpdateError("line name must be a non-empty string")
        line = line_name.strip()
        if line in self.network.line_names():
            raise DataUpdateError(f"line '{line}' already exists")
        names = [str(name).strip() for name in station_names]
        if len(names) < 2:
            raise DataUpdateError("a new line needs at least two stations")
        if len(set(names)) != len(names):
            raise DataUpdateError("station names of a new line must be unique")
        if len(distances) != len(names) - 1:
            raise DataUpdateError("number of distances must be one less than number of stations")
        for value in distances:
            if not _valid_distance(value):
                raise DataUpdateError(f"distance {value!r} must be a positive integer (meters)")

        candidate = copy.deepcopy(self.data)
        by_name = {s["name"]: s for s in candidate["stations"] if isinstance(s, dict) and "name" in s}
        for name in names:
            if name in by_name:
                lines = by_name[name].setdefault("lines", [])
                if line not in lines:
                    lines.append(line)
            else:
                entry = {"name": name, "lines": [line]}
                candidate["stations"].append(entry)
                by_name[name] = entry
        for index, distance in enumerate(distances):
            candidate["connections"].append(
                {
                    "source": names[index],
                    "dest": names[index + 1],
                    "distance": int(distance),
                    "line": line,
                }
            )
        self._commit(candidate)

    def modify_station(self, name, new_name=None, add_lines=None, remove_lines=None):
        """Rename a station and/or change its line membership.

        Args:
            name: Current official station name.
            new_name: New name (optional).
            add_lines: Lines to add to the station (optional).
            remove_lines: Lines to remove from the station (optional). A line
                cannot be removed while connections on it still touch the station.

        Raises:
            DataUpdateError: If the station does not exist or the change is invalid.
        """
        candidate = copy.deepcopy(self.data)
        station = self._find_station(candidate, name)
        if station is None:
            raise DataUpdateError(f"station '{name}' does not exist")

        current = station["name"]
        if new_name is not None:
            new_name = str(new_name).strip()
            if not new_name:
                raise DataUpdateError("new station name must not be empty")
            if new_name != current and self._find_station(candidate, new_name) is not None:
                raise DataUpdateError(f"station '{new_name}' already exists")
            for connection in candidate["connections"]:
                if connection.get("source") == current:
                    connection["source"] = new_name
                if connection.get("dest") == current:
                    connection["dest"] = new_name
            station["name"] = new_name
            current = new_name

        lines = station.setdefault("lines", [])
        for line in add_lines or []:
            line = str(line).strip()
            if line and line not in lines:
                lines.append(line)

        for line in remove_lines or []:
            line = str(line).strip()
            if line not in lines:
                raise DataUpdateError(f"station '{current}' is not on line '{line}'")
            still_used = any(
                connection.get("line") == line
                and current in (connection.get("source"), connection.get("dest"))
                for connection in candidate["connections"]
            )
            if still_used:
                raise DataUpdateError(
                    f"line '{line}' still has connections at station '{current}'"
                )
            lines.remove(line)

        self._commit(candidate)

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance between two adjacent stations.

        Args:
            source, dest: Names of the two stations (order does not matter).
            distance: New distance in meters (positive integer).
            line: If given, only the connection on this line is updated.

        Returns:
            int: Number of connections updated.

        Raises:
            DataUpdateError: If the distance is invalid or no connection matches.
        """
        if not _valid_distance(distance):
            raise DataUpdateError(f"distance {distance!r} must be a positive integer (meters)")
        pair = {str(source).strip(), str(dest).strip()}
        candidate = copy.deepcopy(self.data)
        matched = 0
        for connection in candidate["connections"]:
            if {connection.get("source"), connection.get("dest")} == pair and (
                line is None or connection.get("line") == line
            ):
                connection["distance"] = distance
                matched += 1
        if not matched:
            raise DataUpdateError(f"no connection found between '{source}' and '{dest}'")
        self._commit(candidate)
        return matched

    def save(self, path=DATA_FILE_PATH):
        """Write the current dataset to a JSON file and return the path."""
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        return path

    # ----- integrity check ---------------------------------------------

    def check_integrity(self):
        """Run all data integrity checks and return an IntegrityReport.

        Checks performed:
            * coverage of main lines and representative stations;
            * validity of every connection (known stations, lines, no self loops,
              no duplicates, consistent distances for the same station pair);
            * accuracy of distances (positive integers in a plausible range);
            * station data (lines present, not isolated);
            * connectivity of every line and of the whole network.
        """
        report = IntegrityReport()
        stations = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        names = [s.get("name") for s in stations if isinstance(s, dict)]
        name_set = set(names)
        if len(names) != len(name_set):
            report.notes.append("some station names appear more than once and are merged")

        station_lines = {}
        all_lines = set()
        for station in stations:
            if not isinstance(station, dict):
                report.errors.append("a station entry is not an object")
                continue
            lines = station.get("lines", [])
            station_lines.setdefault(station.get("name"), set()).update(lines)
            all_lines.update(lines)
        for connection in connections:
            if isinstance(connection, dict) and "line" in connection:
                all_lines.add(connection["line"])

        # 1. Coverage
        for line in REQUIRED_MAIN_LINES:
            if line not in all_lines:
                report.warnings.append(f"coverage: main line '{line}' is not in the dataset")
        for station in REPRESENTATIVE_STATIONS:
            if station not in name_set:
                report.warnings.append(f"coverage: representative station '{station}' is missing")
        report.notes.append(
            f"coverage: {len(name_set)} stations, {len(all_lines)} lines, "
            f"{len(connections)} connections"
        )

        # 2 & 3. Connection integrity and distance accuracy
        seen_segments = set()
        pair_distances = {}
        line_adjacency = {}
        connected_names = set()
        for index, connection in enumerate(connections):
            label = f"connection #{index}"
            if not isinstance(connection, dict):
                report.errors.append(f"{label} is not an object")
                continue
            missing = [k for k in ("source", "dest", "distance", "line") if k not in connection]
            if missing:
                report.errors.append(f"{label} misses fields: {', '.join(missing)}")
                continue
            src, dst = connection["source"], connection["dest"]
            distance, line = connection["distance"], connection["line"]

            if src not in name_set:
                report.errors.append(f"{label} references unknown station '{src}'")
            if dst not in name_set:
                report.errors.append(f"{label} references unknown station '{dst}'")
            if src == dst:
                report.errors.append(f"{label} connects station '{src}' to itself")
            if not _valid_distance(distance):
                report.errors.append(f"{label} has invalid distance {distance!r}")
            elif distance < DISTANCE_WARN_MIN_M or distance > DISTANCE_WARN_MAX_M:
                report.warnings.append(
                    f"{label} distance {distance} m between '{src}' and '{dst}' is unusual"
                )
            if line not in station_lines.get(src, set()) or line not in station_lines.get(dst, set()):
                report.warnings.append(
                    f"{label} line '{line}' is not listed on both stations '{src}' and '{dst}'"
                )

            key = (line, frozenset((src, dst)))
            if key in seen_segments:
                report.warnings.append(f"{label} duplicates an existing segment on '{line}'")
            seen_segments.add(key)

            pair = frozenset((src, dst))
            if _valid_distance(distance):
                pair_distances.setdefault(pair, set()).add(distance)

            adjacency = line_adjacency.setdefault(line, {})
            adjacency.setdefault(src, set()).add(dst)
            adjacency.setdefault(dst, set()).add(src)
            connected_names.update((src, dst))

        for pair, distances in pair_distances.items():
            if len(distances) > 1:
                left, right = sorted(str(p) for p in pair)
                report.errors.append(
                    f"conflicting distances {sorted(distances)} between '{left}' and '{right}'"
                )

        # 4. Station data
        for station in stations:
            if not isinstance(station, dict):
                continue
            name = station.get("name")
            if not station.get("lines"):
                report.warnings.append(f"station '{name}' has no lines")
            if name not in connected_names:
                report.warnings.append(f"station '{name}' is not connected to any other station")

        # 5. Line connectivity
        for line in sorted(line_adjacency, key=natural_sort_key):
            components = _count_components(line_adjacency[line])
            if components > 1:
                report.warnings.append(
                    f"line '{line}' is split into {components} disconnected segments"
                )
        for station_name, lines in station_lines.items():
            for line in lines:
                if line not in line_adjacency:
                    report.warnings.append(
                        f"line '{line}' listed at station '{station_name}' has no connections"
                    )

        # 6. Network-wide connectivity
        components = self.network.graph.connected_component_count()
        if components > 1:
            report.warnings.append(f"the network has {components} disconnected components")

        report.notes.append(
            f"accuracy: distances checked for {len(connections)} connection(s), "
            f"range {DISTANCE_WARN_MIN_M}-{DISTANCE_WARN_MAX_M} m considered normal"
        )
        return report
