"""Data management for the Beijing Subway network.

Loads the dataset, builds the ``Graph`` used by the path algorithms, runs
data integrity checks, and supports updates (adding lines, modifying station
information, updating distances) followed by graph rebuilds.
"""

import json
import os
from collections import deque

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph

# Representative (station, line) pairs that must be present in the dataset.
REPRESENTATIVE_STATIONS = (
    ("Pingguoyuan", "Line 1"),
    ("Xizhimen", "Line 2"),
    ("Beijing Zoo", "Line 4"),
    ("Songjiazhuang", "Line 5"),
    ("Shuangjing", "Line 6"),
    ("Dongzhimen", "Line 2"),
)

# Plausibility range for inter-station distances (meters).
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 8000


class DataManager:
    """Manage the subway dataset and the graph built from it."""

    def __init__(self, data_source_path=None):
        self.data_source_path = data_source_path or DATA_FILE_PATH
        self.data = None
        self.graph = None

    # ----- loading and graph construction ---------------------------------
    def load(self):
        """Load the dataset from the data source path and return it."""
        self.data = load_subway_data(self.data_source_path)
        self.graph = None
        return self.data

    def _require_data(self):
        if self.data is None:
            self.load()
        return self.data

    def build_graph(self):
        """Build the weighted undirected graph from the dataset."""
        data = self._require_data()
        graph = Graph()

        names = []
        seen = set()

        def add_name(name):
            if name not in seen:
                seen.add(name)
                names.append(name)

        for station in data["stations"]:
            add_name(station["name"])
        for conn in data["connections"]:
            add_name(conn["source"])
            add_name(conn["dest"])

        for number, name in enumerate(names):
            graph.register_station(name, number)

        lines_by_station = {name: [] for name in names}
        for station in data["stations"]:
            for line in station.get("lines", []):
                if line not in lines_by_station[station["name"]]:
                    lines_by_station[station["name"]].append(line)
        for conn in data["connections"]:
            for endpoint in (conn["source"], conn["dest"]):
                if conn["line"] not in lines_by_station[endpoint]:
                    lines_by_station[endpoint].append(conn["line"])
        for name in names:
            graph.set_station_lines(name, lines_by_station[name])

        for conn in data["connections"]:
            graph.add_edge(
                Edge(
                    graph.get_number(conn["source"]),
                    graph.get_number(conn["dest"]),
                    conn["distance"],
                    conn["line"],
                )
            )

        self.graph = graph
        return graph

    def _refresh(self):
        """Rebuild the graph after the dataset has changed."""
        if self.graph is not None:
            self.build_graph()

    def get_lines(self):
        """Return a sorted list of all line names in the dataset."""
        data = self._require_data()
        lines = set()
        for station in data["stations"]:
            lines.update(station.get("lines", []))
        for conn in data["connections"]:
            lines.add(conn["line"])
        return sorted(lines)

    def get_line_connections(self, line):
        """Return all connections operated by a line."""
        data = self._require_data()
        return [conn for conn in data["connections"] if conn["line"] == line]

    # ----- integrity check -------------------------------------------------
    def check_integrity(self):
        """Run data integrity checks.

        Returns:
            list[str]: Human-readable issue descriptions; empty if no issues.
        """
        data = self._require_data()
        issues = []

        stations = data.get("stations", [])
        connections = data.get("connections", [])

        station_lines = {}
        names = []
        for index, station in enumerate(stations):
            name = station.get("name")
            if not name:
                issues.append(f"station #{index} has no name")
                continue
            if name in station_lines:
                issues.append(f"duplicate station name '{name}'")
                continue
            station_lines[name] = list(station.get("lines", []))
            names.append(name)

        # Connection integrity and distance accuracy.
        seen = set()
        adjacency = {name: set() for name in station_lines}
        for index, conn in enumerate(connections):
            try:
                src = conn["source"]
                dst = conn["dest"]
                dist = conn["distance"]
                line = conn["line"]
            except (KeyError, TypeError):
                issues.append(f"connection #{index} is missing required fields")
                continue

            if src == dst:
                issues.append(f"connection on {line} is a self-loop at '{src}'")
            for endpoint in (src, dst):
                if endpoint not in station_lines:
                    issues.append(
                        f"connection {src} - {dst} ({line}) references unknown station '{endpoint}'"
                    )
                elif station_lines[endpoint] and line not in station_lines[endpoint]:
                    issues.append(f"station '{endpoint}' is not listed on {line}")

            if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
                issues.append(f"connection {src} - {dst} ({line}) has invalid distance {dist!r}")
            elif not MIN_PLAUSIBLE_DISTANCE_M <= dist <= MAX_PLAUSIBLE_DISTANCE_M:
                issues.append(
                    f"connection {src} - {dst} ({line}) distance {dist} m is outside the "
                    f"plausible range {MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )

            key = (frozenset((src, dst)), line)
            if key in seen:
                issues.append(f"duplicate connection {src} - {dst} on {line}")
            seen.add(key)

            if src in adjacency and dst in adjacency:
                adjacency[src].add(dst)
                adjacency[dst].add(src)

        # Connectivity.
        if names:
            visited = {names[0]}
            queue = deque([names[0]])
            while queue:
                current = queue.popleft()
                for nxt in adjacency.get(current, ()):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            for name in names:
                if name not in visited:
                    issues.append(f"station '{name}' is not connected to the rest of the network")

        # Coverage of representative stations.
        for station, line in REPRESENTATIVE_STATIONS:
            if station not in station_lines:
                issues.append(f"representative station '{station}' ({line}) is missing")
            elif line not in station_lines[station]:
                issues.append(f"representative station '{station}' is not listed on {line}")

        # Lines that have stations but no connections.
        connection_lines = {conn.get("line") for conn in connections}
        station_line_names = set()
        for lines in station_lines.values():
            station_line_names.update(lines)
        for line in sorted(station_line_names - connection_lines):
            issues.append(f"line '{line}' has stations but no connections")

        return issues

    # ----- updates ---------------------------------------------------------
    def add_line(self, line_name, stations, distances):
        """Add a new line with an ordered station sequence.

        Args:
            line_name: Name of the new line.
            stations: Ordered list of station names.
            distances: Distances in meters between consecutive stations
                (length ``len(stations) - 1``).

        Raises:
            ValueError: If the input is inconsistent or the line exists.
        """
        data = self._require_data()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self.get_lines():
            raise ValueError(f"line '{line_name}' already exists")
        if len(stations) < 2:
            raise ValueError("a line needs at least two stations")
        if len(set(stations)) != len(stations):
            raise ValueError("a line cannot contain the same station twice")
        if len(distances) != len(stations) - 1:
            raise ValueError("expected one distance per consecutive station pair")
        if any(not isinstance(d, int) or d <= 0 for d in distances):
            raise ValueError("distances must be positive integers (meters)")

        entries = {station["name"]: station for station in data["stations"]}
        for name in stations:
            if name not in entries:
                entry = {"name": name, "lines": [line_name]}
                data["stations"].append(entry)
                entries[name] = entry
            elif line_name not in entries[name].setdefault("lines", []):
                entries[name]["lines"].append(line_name)

        for index, dist in enumerate(distances):
            data["connections"].append(
                {
                    "source": stations[index],
                    "dest": stations[index + 1],
                    "distance": dist,
                    "line": line_name,
                }
            )
        self._refresh()

    def update_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or lines.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name already exists.
        """
        data = self._require_data()
        entry = next((s for s in data["stations"] if s["name"] == name), None)
        if entry is None:
            raise KeyError(f"unknown station '{name}'")
        if lines is not None:
            entry["lines"] = list(lines)
        if new_name and new_name != name:
            if any(s["name"] == new_name for s in data["stations"]):
                raise ValueError(f"station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in data["connections"]:
                if conn["source"] == name:
                    conn["source"] = new_name
                if conn["dest"] == name:
                    conn["dest"] = new_name
        self._refresh()

    def update_distance(self, source, dest, distance):
        """Update the distance of every connection between two stations.

        Returns:
            int: Number of connections updated.

        Raises:
            KeyError: If no connection exists between the stations.
            ValueError: If the distance is not a positive number.
        """
        data = self._require_data()
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("distance must be a positive number of meters")
        count = 0
        for conn in data["connections"]:
            if {conn["source"], conn["dest"]} == {source, dest}:
                conn["distance"] = distance
                count += 1
        if count == 0:
            raise KeyError(f"no connection between '{source}' and '{dest}'")
        self._refresh()
        return count

    def save(self, path=None):
        """Write the current dataset to a JSON file."""
        data = self._require_data()
        target = path or self.data_source_path
        directory = os.path.dirname(os.path.abspath(target))
        os.makedirs(directory, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return target
