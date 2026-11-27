"""Subway network model: maps station names to numbers and manages data updates.

The network keeps the raw dataset dictionary as the single source of truth and
rebuilds the Graph whenever the data is modified.
"""

import copy

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph


class NetworkError(Exception):
    """Raised when a network operation (lookup or update) is invalid."""


class SubwayNetwork:
    """Beijing Subway network with graph model and data management.

    Attributes:
        data: The underlying dataset dictionary (stations and connections).
        station_to_number: dict mapping station name -> station number.
        number_to_name: dict mapping station number -> station name.
        graph: The Graph built from the dataset.
    """

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        self.rebuild()

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Create a network from the subway JSON file."""
        return cls(load_subway_data(path))

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def rebuild(self):
        """Rebuild the station numbering and the graph from the dataset.

        Station numbers are assigned in order of first appearance. A
        station's lines are the union of the lines listed for it in the
        stations section and the lines of connections touching it.
        """
        station_lines = {}
        order = []

        def ensure(name):
            if name not in station_lines:
                station_lines[name] = []
                order.append(name)

        def add_line(name, line):
            if line and line not in station_lines[name]:
                station_lines[name].append(line)

        for station in self.data["stations"]:
            name = station["name"]
            ensure(name)
            for line in station.get("lines", []):
                add_line(name, line)

        for conn in self.data["connections"]:
            for end in (conn["source"], conn["dest"]):
                ensure(end)
                add_line(end, conn["line"])

        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        for number, name in enumerate(order):
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.set_station_lines(name, station_lines[name])
            self.graph.add_vertex(number)

        for conn in self.data["connections"]:
            self.graph.add_edge(Edge(
                self.station_to_number[conn["source"]],
                self.station_to_number[conn["dest"]],
                int(conn["distance"]),
                conn["line"],
            ))

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def station_names(self):
        """Return all official station names in numbering order."""
        return [self.number_to_name[n] for n in sorted(self.number_to_name)]

    def all_lines(self):
        """Return the sorted list of all line names in the network."""
        lines = set()
        for line_list in self.graph.station_lines.values():
            lines.update(line_list)
        for conn in self.data["connections"]:
            lines.add(conn["line"])
        return sorted(lines)

    def has_station(self, name):
        """Return True if a station with this exact name exists."""
        return name in self.station_to_number

    def number_of(self, name):
        """Return the station number for a station name.

        Raises:
            NetworkError: If the station does not exist.
        """
        try:
            return self.station_to_number[name]
        except KeyError as exc:
            raise NetworkError(f"Unknown station: {name}") from exc

    def name_of(self, number):
        """Return the station name for a station number."""
        try:
            return self.number_to_name[number]
        except KeyError as exc:
            raise NetworkError(f"Unknown station number: {number}") from exc

    def lines_of(self, name):
        """Return the list of lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    # ------------------------------------------------------------------
    # Data update mechanisms
    # ------------------------------------------------------------------
    def _station_entry(self, name, create=True):
        """Return the stations-section entry for a name, optionally creating it."""
        for entry in self.data["stations"]:
            if entry["name"] == name:
                return entry
        if not create:
            return None
        entry = {"name": name, "lines": []}
        self.data["stations"].append(entry)
        return entry

    def add_line(self, line_name, station_names, distances, bidirectional=True):
        """Add a new subway line with its ordered stations and distances.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered list of station names on the line.
            distances: List of distances (meters) between consecutive stations.
            bidirectional: If True, add connections in both directions.

        Raises:
            NetworkError: If the input is inconsistent.
        """
        if not line_name or not line_name.strip():
            raise NetworkError("Line name must not be empty")
        line_name = line_name.strip()
        if line_name in self.all_lines():
            raise NetworkError(f"Line already exists: {line_name}")
        if len(station_names) < 2:
            raise NetworkError("A new line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise NetworkError("Number of distances must be one less than number of stations")
        if any(d <= 0 for d in distances):
            raise NetworkError("Distances must be positive")

        for name in station_names:
            entry = self._station_entry(name)
            if line_name not in entry["lines"]:
                entry["lines"].append(line_name)

        for i, distance in enumerate(distances):
            src, dst = station_names[i], station_names[i + 1]
            self.data["connections"].append(
                {"source": src, "dest": dst, "distance": int(distance), "line": line_name})
            if bidirectional:
                self.data["connections"].append(
                    {"source": dst, "dest": src, "distance": int(distance), "line": line_name})
        self.rebuild()

    def update_station(self, old_name, new_name=None, lines=None):
        """Modify a station's name and/or its lines.

        Args:
            old_name: Current station name (must exist).
            new_name: Optional new official name.
            lines: Optional replacement list of line names.

        Raises:
            NetworkError: If the station does not exist or the new name is taken.
        """
        if not self.has_station(old_name):
            raise NetworkError(f"Unknown station: {old_name}")
        entry = self._station_entry(old_name)
        if new_name and new_name != old_name:
            if self.has_station(new_name):
                raise NetworkError(f"Station already exists: {new_name}")
            entry["name"] = new_name
            for conn in self.data["connections"]:
                if conn["source"] == old_name:
                    conn["source"] = new_name
                if conn["dest"] == old_name:
                    conn["dest"] = new_name
        if lines is not None:
            entry["lines"] = list(lines)
        self.rebuild()

    def update_distance(self, source, dest, distance, bidirectional=False):
        """Update the distance of a connection.

        Args:
            source: Origin station name.
            dest: Destination station name.
            distance: New distance in meters (positive integer).
            bidirectional: If True, also update the reverse connection.

        Returns:
            int: Number of connections updated.

        Raises:
            NetworkError: If no matching connection exists or distance is invalid.
        """
        if distance <= 0:
            raise NetworkError("Distance must be positive")
        updated = 0
        for conn in self.data["connections"]:
            pair = (conn["source"], conn["dest"])
            if pair == (source, dest) or (bidirectional and pair == (dest, source)):
                conn["distance"] = int(distance)
                updated += 1
        if updated == 0:
            raise NetworkError(f"No connection from {source} to {dest}")
        self.rebuild()
        return updated

    def save(self, path=DATA_FILE_PATH):
        """Persist the current dataset to a JSON file."""
        save_subway_data(self.data, path)
