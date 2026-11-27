"""
Data management for the subway network.

Provides integrity checks (station coverage, connection integrity, distance
accuracy, line connectivity) and data update operations (adding lines,
modifying stations, updating distances). All operations work on a private
copy of the raw data dictionary.
"""

import copy

from data_loader import save_subway_data

# Lines that must be present in the dataset.
REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations of main lines used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Sihui", "Tiananmen West"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Chegongzhuang"],
    "Line 4": ["Xizhimen", "Anheqiao North", "Beijing Zoo"],
    "Line 5": ["Songjiazhuang", "Dongdaqiao", "Tiantongyuan North"],
}

MIN_DISTANCE_M = 1
MAX_DISTANCE_M = 10000
TYPICAL_MAX_DISTANCE_M = 5000


class _UnionFind:
    """Simple disjoint-set structure used for connectivity checks."""

    def __init__(self):
        self._parent = {}

    def add(self, item):
        self._parent.setdefault(item, item)

    def find(self, item):
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, a, b):
        self.add(a)
        self.add(b)
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_b] = root_a

    def component_count(self):
        return len({self.find(item) for item in self._parent})


def validate_distance(distance):
    """
    Validate a distance value in meters.

    Raises:
        ValueError: If the distance is not a positive integer.
    """
    if isinstance(distance, bool) or not isinstance(distance, int):
        raise ValueError("Distance must be an integer number of meters")
    if distance < MIN_DISTANCE_M:
        raise ValueError("Distance must be a positive number of meters")


class DataManager:
    """
    Manage the raw subway data: integrity checking and updates.

    Attributes:
        data: The working copy of the network data dictionary.
    """

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])

    @property
    def stations(self):
        return self.data["stations"]

    @property
    def connections(self):
        return self.data["connections"]

    def _station_index(self):
        return {station["name"]: station for station in self.stations}

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self):
        """
        Run all data integrity checks.

        Returns:
            dict with keys "errors" (list[str]), "warnings" (list[str]),
            "info" (dict) and "ok" (bool, True when there are no errors).
        """
        report = {"errors": [], "warnings": [], "info": {}, "ok": True}
        self._check_station_coverage(report)
        self._check_connections(report)
        self._check_distances(report)
        self._check_line_connectivity(report)
        report["info"]["station_count"] = len(self.stations)
        report["info"]["connection_count"] = len(self.connections)
        report["ok"] = not report["errors"]
        return report

    def _check_station_coverage(self, report):
        names = [station.get("name") for station in self.stations]
        name_set = set(names)

        if len(name_set) != len(names):
            report["warnings"].append("Duplicate station names found in station data")

        lines_present = set()
        for station in self.stations:
            lines_present.update(station.get("lines", []))
        for conn in self.connections:
            if "line" in conn:
                lines_present.add(conn["line"])

        for line in REQUIRED_LINES:
            if line not in lines_present:
                report["warnings"].append(f"Main line '{line}' is not covered by the data")

        for line, representatives in REPRESENTATIVE_STATIONS.items():
            for station_name in representatives:
                if station_name not in name_set:
                    report["warnings"].append(
                        f"Representative station '{station_name}' of {line} is missing")

    def _check_connections(self, report):
        station_index = self._station_index()
        seen = set()
        connected = set()

        for position, conn in enumerate(self.connections):
            missing = [key for key in ("source", "dest", "distance", "line") if key not in conn]
            if missing:
                report["errors"].append(
                    f"Connection #{position} is missing fields: {', '.join(missing)}")
                continue

            source, dest, line = conn["source"], conn["dest"], conn["line"]
            for name in (source, dest):
                if name not in station_index:
                    report["errors"].append(
                        f"Connection #{position} refers to unknown station '{name}'")
            if source == dest:
                report["errors"].append(f"Connection #{position} links '{source}' to itself")
                continue

            for name in (source, dest):
                station = station_index.get(name)
                if station is not None and line not in station.get("lines", []):
                    report["errors"].append(
                        f"Station '{name}' is not listed as served by '{line}'")

            key = (frozenset((source, dest)), line)
            if key in seen:
                report["warnings"].append(
                    f"Duplicate connection {source} - {dest} on {line}")
            seen.add(key)
            connected.update((source, dest))

        for station in self.stations:
            if station.get("name") not in connected:
                report["warnings"].append(
                    f"Station '{station.get('name')}' has no connections")

    def _check_distances(self, report):
        for position, conn in enumerate(self.connections):
            distance = conn.get("distance")
            label = f"{conn.get('source')} - {conn.get('dest')}"
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                report["errors"].append(f"Distance for {label} is not a number")
                continue
            if distance <= 0:
                report["errors"].append(f"Distance for {label} must be positive")
            elif distance > MAX_DISTANCE_M:
                report["errors"].append(f"Distance for {label} exceeds {MAX_DISTANCE_M} m")
            elif distance > TYPICAL_MAX_DISTANCE_M:
                report["warnings"].append(
                    f"Distance for {label} ({distance} m) is unusually large")

    def _check_line_connectivity(self, report):
        per_line = {}
        for conn in self.connections:
            if "line" not in conn or "source" not in conn or "dest" not in conn:
                continue
            uf = per_line.setdefault(conn["line"], _UnionFind())
            uf.union(conn["source"], conn["dest"])

        for line, uf in sorted(per_line.items()):
            components = uf.component_count()
            if components > 1:
                report["warnings"].append(
                    f"{line} is split into {components} disconnected segments")

    # ------------------------------------------------------------------
    # Update operations
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """
        Add a new line made of an ordered sequence of stations.

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names on the line.
            distances: List of distances (meters) between consecutive stations.

        Raises:
            ValueError: On invalid input or if the line already exists.
        """
        if not line_name or not isinstance(line_name, str):
            raise ValueError("Line name must be a non-empty string")
        if line_name in {line for s in self.stations for line in s.get("lines", [])} or \
                line_name in {c.get("line") for c in self.connections}:
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(station_names)) != len(station_names):
            raise ValueError("Station sequence contains duplicates")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for distance in distances:
            validate_distance(distance)

        index = self._station_index()
        for name in station_names:
            if name not in index:
                station = {"name": name, "lines": []}
                self.stations.append(station)
                index[name] = station
            if line_name not in index[name]["lines"]:
                index[name]["lines"].append(line_name)

        for position, distance in enumerate(distances):
            self.connections.append({
                "source": station_names[position],
                "dest": station_names[position + 1],
                "distance": distance,
                "line": line_name,
            })

    def modify_station(self, name, new_name=None, lines=None):
        """
        Modify a station's name and/or its line affiliations.

        Args:
            name: Current official station name.
            new_name: Optional new name (renames connections too).
            lines: Optional full replacement list of line names.

        Returns:
            The final station name.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name is already used or the lines are invalid.
        """
        index = self._station_index()
        if name not in index:
            raise KeyError(f"Station '{name}' does not exist")
        station = index[name]

        final_name = name
        if new_name and new_name != name:
            if new_name in index:
                raise ValueError(f"Station '{new_name}' already exists")
            final_name = new_name
            station["name"] = new_name
            for conn in self.connections:
                if conn.get("source") == name:
                    conn["source"] = new_name
                if conn.get("dest") == name:
                    conn["dest"] = new_name

        if lines is not None:
            if not isinstance(lines, list) or not all(isinstance(x, str) and x for x in lines):
                raise ValueError("Lines must be a list of non-empty strings")
            station["lines"] = list(dict.fromkeys(lines))

        return final_name

    def update_distance(self, source, dest, distance):
        """
        Update the distance between two directly connected stations.

        Returns:
            int: Number of connection records updated.

        Raises:
            ValueError: If the distance is invalid.
            KeyError: If the stations are not directly connected.
        """
        validate_distance(distance)
        updated = 0
        for conn in self.connections:
            if {conn.get("source"), conn.get("dest")} == {source, dest}:
                conn["distance"] = distance
                updated += 1
        if updated == 0:
            raise KeyError(f"No direct connection between '{source}' and '{dest}'")
        return updated

    def to_dict(self):
        """Return a deep copy of the working data dictionary."""
        return copy.deepcopy(self.data)

    def save(self, path):
        """Persist the working data to a JSON file."""
        save_subway_data(self.data, path)
