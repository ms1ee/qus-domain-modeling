"""Subway network model built from the dataset, with data management operations.

SubwayNetwork owns the raw dataset dictionary, assigns integer station
numbers, builds the Graph, and supports data updates (adding lines, editing
stations, updating distances). Every update rebuilds the graph.
"""

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


class StationNotFoundError(LookupError):
    """Raised when a station name is not part of the network."""


class SubwayNetwork:
    """Beijing Subway network: station mapping, graph and data management.

    Attributes:
        name: Network name.
        data_source: Origin of the data (file path).
        version: Data version string.
        data: Raw dataset dict with "stations" and "connections" lists.
        station_to_number: dict mapping station name to integer number.
        number_to_name: dict mapping integer number to station name.
        graph: The Graph built from the dataset.
    """

    def __init__(self, data=None, name="Beijing Subway", data_source=None, version="1.0"):
        self.name = name
        self.data_source = data_source or DATA_FILE_PATH
        self.version = version
        self.data = data if data is not None else load_subway_data(DATA_FILE_PATH)
        self.data.setdefault("stations", [])
        self.data.setdefault("connections", [])
        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        self.rebuild()

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Create a network from a subway_data.json file."""
        return cls(load_subway_data(path), data_source=path)

    # ----- building --------------------------------------------------------
    def _register(self, name) -> int:
        """Return the number of a station, registering it if new."""
        if name not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_name[number] = name
            self.graph.add_node(number)
        return self.station_to_number[name]

    def rebuild(self) -> None:
        """Rebuild station mapping, station-line table and graph from the dataset."""
        self.station_to_number = {}
        self.number_to_name = {}
        self.graph = Graph()
        lines_map = {}

        for record in self.data["stations"]:
            name = record["name"]
            lines = lines_map.setdefault(name, [])
            for line in record.get("lines", []):
                if line not in lines:
                    lines.append(line)
            self._register(name)

        for connection in self.data["connections"]:
            for name in (connection["source"], connection["dest"]):
                self._register(name)
                lines = lines_map.setdefault(name, [])
                if connection["line"] not in lines:
                    lines.append(connection["line"])

        for name, lines in lines_map.items():
            self.graph.set_station_lines(name, lines)

        for connection in self.data["connections"]:
            self.graph.add_edge(
                Edge(
                    self.station_to_number[connection["source"]],
                    self.station_to_number[connection["dest"]],
                    int(connection["distance"]),
                    connection["line"],
                )
            )

    # ----- queries ---------------------------------------------------------
    def has_station(self, name) -> bool:
        """Return True if the station name exists in the network."""
        return name in self.station_to_number

    def get_number(self, name) -> int:
        """Return the number of a station.

        Raises:
            StationNotFoundError: If the station is unknown.
        """
        if name not in self.station_to_number:
            raise StationNotFoundError(f"Station '{name}' does not exist")
        return self.station_to_number[name]

    def get_name(self, number) -> str:
        """Return the name of a station number."""
        return self.number_to_name[number]

    def station_names(self) -> list:
        """Return all station names, sorted."""
        return sorted(self.station_to_number)

    def line_names(self) -> list:
        """Return all line names, sorted."""
        lines = set()
        for station_lines in self.graph.station_lines.values():
            lines.update(station_lines)
        return sorted(lines)

    def stations_on_line(self, line) -> list:
        """Return station names served by a line, sorted."""
        return sorted(
            name for name, lines in self.graph.station_lines.items() if line in lines
        )

    def transfer_stations(self) -> dict:
        """Return {station name: lines} for stations served by two or more lines."""
        return {
            name: list(lines)
            for name, lines in self.graph.station_lines.items()
            if len(lines) >= 2
        }

    # ----- data management -------------------------------------------------
    def _station_record(self, name, create=False):
        for record in self.data["stations"]:
            if record["name"] == name:
                return record
        if create:
            record = {"name": name, "lines": []}
            self.data["stations"].append(record)
            return record
        return None

    def add_line(self, line_name, station_names, distances, bidirectional=True) -> None:
        """Add a new line described by an ordered station sequence.

        Args:
            line_name: Name of the new line (must be unused).
            station_names: Ordered list of station names on the line (at least 2).
            distances: Distances in meters between consecutive stations (len - 1 values).
            bidirectional: If True, both travel directions are added explicitly.

        Raises:
            ValueError: If the input is inconsistent.
        """
        names = list(station_names)
        distances = [int(d) for d in distances]
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.line_names():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("Station sequence of a line must not repeat stations")
        if len(distances) != len(names) - 1:
            raise ValueError("Exactly one distance per consecutive station pair is required")
        if any(d <= 0 for d in distances):
            raise ValueError("Distances must be positive")

        for name in names:
            record = self._station_record(name, create=True)
            if line_name not in record["lines"]:
                record["lines"].append(line_name)
        for index, distance in enumerate(distances):
            source, dest = names[index], names[index + 1]
            self.data["connections"].append(
                {"source": source, "dest": dest, "distance": distance, "line": line_name}
            )
            if bidirectional:
                self.data["connections"].append(
                    {"source": dest, "dest": source, "distance": distance, "line": line_name}
                )
        self.rebuild()

    def update_station(self, name, lines=None, new_name=None) -> None:
        """Modify station information: its served lines and/or its name.

        Raises:
            StationNotFoundError: If the station is unknown.
            ValueError: If the new name is already used.
        """
        if not self.has_station(name):
            raise StationNotFoundError(f"Station '{name}' does not exist")
        record = self._station_record(name, create=True)
        if lines is not None:
            record["lines"] = list(dict.fromkeys(lines))
        if new_name and new_name != name:
            if self.has_station(new_name):
                raise ValueError(f"Station '{new_name}' already exists")
            record["name"] = new_name
            for connection in self.data["connections"]:
                if connection["source"] == name:
                    connection["source"] = new_name
                if connection["dest"] == name:
                    connection["dest"] = new_name
        self.rebuild()

    def update_distance(self, source, dest, distance, bidirectional=True) -> None:
        """Update the distance of a connection.

        Raises:
            ValueError: If the distance is not positive or the connection is unknown.
        """
        distance = int(distance)
        if distance <= 0:
            raise ValueError("Distance must be positive")
        found = 0
        for connection in self.data["connections"]:
            forward = connection["source"] == source and connection["dest"] == dest
            backward = bidirectional and connection["source"] == dest and connection["dest"] == source
            if forward or backward:
                connection["distance"] = distance
                found += 1
        if not found:
            raise ValueError(f"No connection between '{source}' and '{dest}'")
        self.rebuild()
