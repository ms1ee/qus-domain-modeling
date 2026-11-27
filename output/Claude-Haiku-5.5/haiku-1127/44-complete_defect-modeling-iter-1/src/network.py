"""Subway network model: data management, graph construction, and updates.

``SubwayNetwork`` wraps the raw dataset (stations and connections), builds the
weighted ``Graph`` used by the path finder, and offers data update operations
(adding lines, renaming or re-lining stations, updating distances). Every
update rebuilds the graph so that queries always see consistent data.
"""

from typing import Dict, List, Optional, Set

from models import Edge, Graph


def _normalize_name(name: str) -> str:
    """Normalize a station name for case-insensitive, whitespace-tolerant matching."""
    return " ".join(name.split()).lower()


def _is_positive_number(value) -> bool:
    """Return True if ``value`` is an int or float strictly greater than zero."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


class SubwayNetwork:
    """Subway network data plus its graph representation.

    Attributes:
        name: Network name.
        data_source: Origin of the dataset.
        version: Dataset version label.
        stations: Ordered mapping from station name to list of line names.
        connections: List of connection dictionaries with keys
            ``source``, ``dest``, ``distance`` (meters) and ``line``.
        undeclared_stations: Station names referenced by connections but not
            declared in the station list.
        graph: The weighted ``Graph`` (rebuilt after every update).
    """

    def __init__(self, data: dict) -> None:
        self._validate(data)
        self.name: str = str(data.get("name", "Beijing Subway"))
        self.data_source: str = str(data.get("data_source", "subway_data.json"))
        self.version: str = str(data.get("version", "1.0"))

        self.stations: Dict[str, List[str]] = {}
        for item in data["stations"]:
            station_name = item["name"].strip()
            lines = self.stations.setdefault(station_name, [])
            for line in item.get("lines", []):
                if line not in lines:
                    lines.append(line)

        self.connections: List[dict] = []
        self.undeclared_stations: Set[str] = set()
        for item in data["connections"]:
            source = item["source"].strip()
            dest = item["dest"].strip()
            for endpoint in (source, dest):
                if endpoint not in self.stations:
                    self.stations[endpoint] = []
                    self.undeclared_stations.add(endpoint)
            self.connections.append(
                {"source": source, "dest": dest, "distance": item["distance"], "line": item["line"]}
            )

        self.graph: Graph = Graph()
        self._name_index: Dict[str, str] = {}
        self.rebuild()

    @staticmethod
    def _validate(data) -> None:
        """Check the structure of the raw dataset."""
        if not isinstance(data, dict):
            raise ValueError("network data must be a JSON object")
        for key in ("stations", "connections"):
            if not isinstance(data.get(key), list):
                raise ValueError(f"network data must contain a list under '{key}'")
        for index, item in enumerate(data["stations"]):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
                raise ValueError(f"station entry #{index} is malformed")
            if not isinstance(item.get("lines", []), list):
                raise ValueError(f"station entry #{index} has a non-list 'lines' field")
        for index, item in enumerate(data["connections"]):
            if not isinstance(item, dict):
                raise ValueError(f"connection entry #{index} is malformed")
            for key in ("source", "dest", "line"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f"connection entry #{index} has an invalid '{key}' field")
            if not _is_positive_number(item.get("distance")) and not (
                isinstance(item.get("distance"), (int, float)) and not isinstance(item.get("distance"), bool)
            ):
                raise ValueError(f"connection entry #{index} has an invalid 'distance' field")

    def rebuild(self) -> None:
        """Rebuild the graph and the name index from the current data.

        Connections that are self-loops are skipped here; the integrity check
        reports them.
        """
        graph = Graph()
        numbers: Dict[str, int] = {}
        for index, (name, lines) in enumerate(self.stations.items()):
            numbers[name] = index
            graph.add_station(name, index, lines)
        for connection in self.connections:
            if connection["source"] == connection["dest"]:
                continue
            graph.add_edge(
                Edge(
                    numbers[connection["source"]],
                    numbers[connection["dest"]],
                    connection["distance"],
                    connection["line"],
                )
            )
        self.graph = graph
        self._name_index = {_normalize_name(name): name for name in self.stations}

    @property
    def station_to_number(self) -> Dict[str, int]:
        """Mapping from official station names to station numbers."""
        return self.graph.station_to_number

    def standardize_name(self, name: str) -> Optional[str]:
        """Return the official station name matching ``name``, or None if unknown."""
        if not name:
            return None
        return self._name_index.get(_normalize_name(name))

    def has_station(self, name: str) -> bool:
        """Return True if the official station name exists."""
        return name in self.stations

    def lines(self) -> List[str]:
        """Return the sorted list of all line names in the network."""
        names: Set[str] = set()
        for station_lines in self.stations.values():
            names.update(station_lines)
        for connection in self.connections:
            names.add(connection["line"])
        return sorted(names)

    def is_transfer_station(self, name: str) -> bool:
        """Return True if the station is served by more than one line."""
        return len(self.stations.get(name, [])) > 1

    def add_line(self, line_name: str, station_names: List[str], distances: List[float]) -> None:
        """Add a new line as an ordered sequence of stations.

        Args:
            line_name: Name of the new line (must not already exist).
            station_names: Ordered station names along the line (at least two).
            distances: Distance in meters between consecutive stations.

        Raises:
            ValueError: If the input is inconsistent.
        """
        line_name = line_name.strip()
        if not line_name:
            raise ValueError("line name must not be empty")
        if line_name in self.lines():
            raise ValueError(f"line '{line_name}' already exists")
        names = [name.strip() for name in station_names]
        if len(names) < 2:
            raise ValueError("a line needs at least two stations")
        if any(not name for name in names):
            raise ValueError("station names must not be empty")
        if len(distances) != len(names) - 1:
            raise ValueError("number of distances must be one less than number of stations")
        if not all(_is_positive_number(distance) for distance in distances):
            raise ValueError("distances must be positive numbers")

        for name in names:
            station_lines = self.stations.setdefault(name, [])
            if line_name not in station_lines:
                station_lines.append(line_name)
        for index, distance in enumerate(distances):
            self.connections.append(
                {"source": names[index], "dest": names[index + 1], "distance": distance, "line": line_name}
            )
        self.rebuild()

    def update_station(self, name: str, new_name: Optional[str] = None, lines: Optional[List[str]] = None) -> None:
        """Rename a station and/or replace its line affiliations.

        Raises:
            ValueError: If the station is unknown or the new name is taken.
        """
        if name not in self.stations:
            raise ValueError(f"station '{name}' does not exist")
        target = name
        if new_name is not None and new_name.strip() and new_name.strip() != name:
            new_name = new_name.strip()
            if new_name in self.stations:
                raise ValueError(f"station '{new_name}' already exists")
            renamed: Dict[str, List[str]] = {}
            for key, value in self.stations.items():
                renamed[new_name if key == name else key] = value
            self.stations = renamed
            for connection in self.connections:
                if connection["source"] == name:
                    connection["source"] = new_name
                if connection["dest"] == name:
                    connection["dest"] = new_name
            if name in self.undeclared_stations:
                self.undeclared_stations.discard(name)
                self.undeclared_stations.add(new_name)
            target = new_name
        if lines is not None:
            self.stations[target] = list(dict.fromkeys(line.strip() for line in lines if line.strip()))
        self.rebuild()

    def update_distance(self, source: str, dest: str, distance: float, line: Optional[str] = None) -> int:
        """Update the distance of every connection between two stations.

        Args:
            source: One endpoint station name.
            dest: The other endpoint station name.
            distance: New distance in meters (positive).
            line: Optionally restrict the update to connections on this line.

        Returns:
            The number of connections updated.

        Raises:
            ValueError: If the distance is invalid or no connection matches.
        """
        if not _is_positive_number(distance):
            raise ValueError("distance must be a positive number")
        count = 0
        for connection in self.connections:
            pair = {connection["source"], connection["dest"]}
            if pair == {source, dest} and (line is None or connection["line"] == line):
                connection["distance"] = distance
                count += 1
        if count == 0:
            raise ValueError(f"no connection found between '{source}' and '{dest}'")
        self.rebuild()
        return count
