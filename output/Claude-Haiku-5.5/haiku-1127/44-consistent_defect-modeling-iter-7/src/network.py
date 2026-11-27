"""
Subway network management.

SubwayNetwork builds the weighted directed Graph from the dataset, assigns
station numbers, resolves user-entered station names, and provides data
update operations (adding lines, modifying stations, updating distances).
"""

import difflib

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph, Station


STATION_NUMBER_PREFIX = "S"
NAME_MATCH_CUTOFF = 0.6


class UnknownStationError(Exception):
    """Raised when a station name matches no official station."""

    def __init__(self, raw_name):
        super().__init__(f"Station '{raw_name}' does not exist, please check the station name")
        self.raw_name = raw_name


class SubwayNetwork:
    """Subway network built from the dataset and kept in sync with edits.

    Attributes:
        data: The raw dataset dictionary (stations and connections).
        graph: The Graph built from the dataset.
        name_to_number: dict official station name -> station number.
        number_to_name: dict station number -> official station name.
    """

    def __init__(self, data=None, data_path=None):
        self.data_path = data_path or DATA_FILE_PATH
        self.data = data if data is not None else load_subway_data(self.data_path)
        self.graph = Graph()
        self.name_to_number = {}
        self.number_to_name = {}
        self._normalized_names = {}
        self.build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def build(self):
        """(Re)build the graph and lookup tables from the dataset."""
        self.graph = Graph()
        self.name_to_number = {}
        self.number_to_name = {}
        self._normalized_names = {}

        for entry in self.data.get("stations", []):
            name = entry["name"]
            self._ensure_station(name)
            for line in entry.get("lines", []):
                self._add_station_line(name, line)

        for conn in self.data.get("connections", []):
            src_name = conn["source"]
            dst_name = conn["dest"]
            line = conn["line"]
            distance = int(conn["distance"])
            src = self._ensure_station(src_name)
            dst = self._ensure_station(dst_name)
            self._add_station_line(src_name, line)
            self._add_station_line(dst_name, line)
            self.graph.add_edge(Edge(src, dst, distance, line))

    def _ensure_station(self, name):
        """Return the number of a station, creating it if it is new."""
        if name in self.name_to_number:
            return self.name_to_number[name]
        number = f"{STATION_NUMBER_PREFIX}{len(self.name_to_number) + 1:04d}"
        self.name_to_number[name] = number
        self.number_to_name[number] = name
        self._normalized_names[self.normalize_name(name)] = name
        self.graph.add_node(number)
        self.graph.set_station_lines(name, [])
        return number

    def _add_station_line(self, name, line):
        """Register a line as serving the given station."""
        lines = list(self.graph.station_lines.get(name, []))
        if line not in lines:
            lines.append(line)
            self.graph.set_station_lines(name, lines)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_name(name):
        """Standardise a station name for comparison (trim, collapse spaces, lowercase)."""
        return " ".join(str(name).split()).lower()

    def resolve_station(self, raw_name):
        """Map a user-entered name to an official station name.

        Returns:
            tuple: (official name, matched_by_similarity flag)

        Raises:
            UnknownStationError: If no station is close enough to the input.
        """
        key = self.normalize_name(raw_name)
        if not key:
            raise UnknownStationError(raw_name)
        if key in self._normalized_names:
            return self._normalized_names[key], False
        candidates = difflib.get_close_matches(
            key, list(self._normalized_names.keys()), n=1, cutoff=NAME_MATCH_CUTOFF
        )
        if candidates:
            return self._normalized_names[candidates[0]], True
        raise UnknownStationError(raw_name)

    def station_number(self, name):
        """Return the station number of an official station name."""
        return self.name_to_number[name]

    def name_of(self, number):
        """Return the official station name of a station number."""
        return self.number_to_name[number]

    def lines_of(self, name):
        """Return the list of lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def station_names(self):
        """Return all official station names, sorted."""
        return sorted(self.name_to_number.keys())

    def station_info(self, name):
        """Return a Station record for an official station name."""
        lines = self.lines_of(name)
        return Station(name=name, number=self.name_to_number[name], is_transfer=len(lines) > 1)

    def line_names(self):
        """Return the sorted list of all line names in the network."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        return sorted(names)

    def stations_on_line(self, line):
        """Return the official names of stations served by a line."""
        return [name for name in self.station_names() if line in self.lines_of(name)]

    def has_station(self, name):
        """Return True if an official station with this exact name exists."""
        return name in self.name_to_number

    # ------------------------------------------------------------------
    # Data update operations
    # ------------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line through the given ordered stations (both directions).

        Args:
            line_name: Name of the new line.
            station_names: Ordered list of station names (at least two).
            distances: Distances in meters between consecutive stations.

        Raises:
            ValueError: On invalid or conflicting input.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("Line name cannot be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        station_names = [name.strip() for name in station_names]
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        distances = [int(d) for d in distances]
        if any(d <= 0 for d in distances):
            raise ValueError("Distances must be positive")

        stations = self.data.setdefault("stations", [])
        index = {entry["name"]: entry for entry in stations}
        for name in station_names:
            if name in index:
                entry = index[name]
                entry.setdefault("lines", [])
                if line_name not in entry["lines"]:
                    entry["lines"].append(line_name)
            else:
                entry = {"name": name, "lines": [line_name]}
                stations.append(entry)
                index[name] = entry

        connections = self.data.setdefault("connections", [])
        for i, distance in enumerate(distances):
            a, b = station_names[i], station_names[i + 1]
            connections.append({"source": a, "dest": b, "distance": distance, "line": line_name})
            connections.append({"source": b, "dest": a, "distance": distance, "line": line_name})
        self.build()

    def modify_station(self, name, new_name=None, lines=None):
        """Modify a station's name and/or its line list.

        Raises:
            UnknownStationError: If the station does not exist.
            ValueError: If the new name is already used by another station.
        """
        official, _ = self.resolve_station(name)
        stations = self.data.setdefault("stations", [])
        entry = next((s for s in stations if s["name"] == official), None)
        if entry is None:
            entry = {"name": official, "lines": []}
            stations.append(entry)
        if lines is not None:
            entry["lines"] = list(lines)
        if new_name is not None and new_name.strip() and new_name.strip() != official:
            new_name = new_name.strip()
            if self.has_station(new_name):
                raise ValueError(f"Station '{new_name}' already exists")
            entry["name"] = new_name
            for conn in self.data.get("connections", []):
                if conn["source"] == official:
                    conn["source"] = new_name
                if conn["dest"] == official:
                    conn["dest"] = new_name
        self.build()

    def update_distance(self, source, dest, distance):
        """Update the distance between two adjacent stations (both directions).

        Returns:
            int: Number of connections updated.

        Raises:
            UnknownStationError: If a station does not exist.
            ValueError: If the distance is invalid or the stations are not connected.
        """
        src, _ = self.resolve_station(source)
        dst, _ = self.resolve_station(dest)
        distance = int(distance)
        if distance <= 0:
            raise ValueError("Distance must be positive")
        changed = 0
        for conn in self.data.get("connections", []):
            if (conn["source"], conn["dest"]) in ((src, dst), (dst, src)):
                conn["distance"] = distance
                changed += 1
        if changed == 0:
            raise ValueError(f"No direct connection between '{src}' and '{dst}'")
        self.build()
        return changed

    def save(self, path=None):
        """Persist the current dataset to disk."""
        save_subway_data(self.data, path or self.data_path)
