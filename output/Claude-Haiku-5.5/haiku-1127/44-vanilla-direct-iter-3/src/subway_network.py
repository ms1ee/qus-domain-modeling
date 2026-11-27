"""Subway network modelling and data management.

SubwayNetwork builds the weighted undirected graph from the dataset, assigns
station numbers (station_to_number), keeps line information, and provides
data update operations: adding lines, modifying stations, and updating distances.
"""

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


def _normalize_name(name):
    """Collapse internal whitespace and strip a station or line name."""
    if not isinstance(name, str):
        raise ValueError("name must be a string")
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("name must not be empty")
    return cleaned


def _normalize_distance(distance):
    """Validate a distance in meters and return it as a positive integer."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    if distance <= 0:
        raise ValueError("distance must be positive")
    return int(round(distance))


class SubwayNetwork:
    """Beijing Subway network: stations, lines, connections and graph.

    Attributes:
        graph: the Graph instance holding adjacency lists and station lines.
        station_to_number: station name -> station number.
        number_to_station: station number -> station name.
    """

    def __init__(self, data=None):
        if data is None:
            data = load_subway_data()
        self.graph = Graph()
        self.station_to_number = {}
        self.number_to_station = {}
        self._station_order = []
        self._connections = []  # list of dicts: source, dest, distance, line
        self.undeclared_stations = []  # stations used by connections but not declared
        self._build(data)

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        """Create a network from a subway_data.json file."""
        return cls(load_subway_data(path))

    # ----- construction -----
    def _build(self, data):
        """Populate stations, lines and connections from the dataset."""
        declared = set()
        for station in data.get("stations", []):
            name = _normalize_name(station["name"])
            declared.add(name)
            lines = [str(line).strip() for line in station.get("lines", []) if str(line).strip()]
            self._register_station(name, lines)

        for conn in data.get("connections", []):
            source = _normalize_name(conn["source"])
            dest = _normalize_name(conn["dest"])
            for name in (source, dest):
                if name not in declared and name not in self.undeclared_stations:
                    self.undeclared_stations.append(name)
            self._add_connection_record(source, dest, conn["distance"], conn["line"].strip())

    def _register_station(self, name, lines=()):
        """Add a station if needed and merge the given lines into its line list."""
        if name not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self._station_order.append(name)
            self.graph.add_node(number)
            self.graph.set_station_lines(name, [])
        current = self.graph.get_station_lines(name)
        self.graph.set_station_lines(name, current + [line for line in lines if line])
        return self.station_to_number[name]

    def _add_connection_record(self, source, dest, distance, line):
        """Create a bidirectional connection between two stations on a line."""
        if source == dest:
            raise ValueError(f"Connection from '{source}' to itself is not allowed")
        if not line:
            raise ValueError("connection line must not be empty")
        distance = _normalize_distance(distance)
        a = self._register_station(source, [line])
        b = self._register_station(dest, [line])
        self.graph.add_edge(Edge(a, b, distance, line))
        self._connections.append(
            {"source": source, "dest": dest, "distance": distance, "line": line}
        )

    # ----- queries -----
    def resolve_station(self, name):
        """Return the official station name matching ``name``, or None.

        Matching ignores case, surrounding and repeated whitespace, and an optional
        trailing '站' (station) suffix.
        """
        if not isinstance(name, str):
            return None
        cleaned = " ".join(name.split())
        if not cleaned:
            return None
        if cleaned in self.station_to_number:
            return cleaned
        candidates = [cleaned]
        if cleaned.endswith("站"):
            candidates.append(cleaned[:-1].strip())
        keys = {official.casefold().replace(" ", ""): official for official in self._station_order}
        for candidate in candidates:
            key = candidate.casefold().replace(" ", "")
            if key in keys:
                return keys[key]
        return None

    def has_station(self, name):
        """Return True if the station exists."""
        return name in self.station_to_number

    def station_number(self, name):
        """Return the station number of an official station name."""
        if name not in self.station_to_number:
            raise KeyError(f"Unknown station '{name}'")
        return self.station_to_number[name]

    def station_name(self, number):
        """Return the official station name for a station number."""
        return self.number_to_station[number]

    def station_names(self):
        """Return all station names in definition order."""
        return list(self._station_order)

    def lines(self):
        """Return the sorted list of all line names in the network."""
        found = set()
        for lines in self.graph.station_lines.values():
            found.update(lines)
        return sorted(found)

    def stations_on_line(self, line):
        """Return the names of the stations that belong to ``line``."""
        return [name for name in self._station_order if line in self.graph.get_station_lines(name)]

    def transfer_stations(self):
        """Return the names of stations served by more than one line."""
        return [
            name for name in self._station_order if len(self.graph.get_station_lines(name)) > 1
        ]

    def connection_records(self):
        """Return a copy of all connection records."""
        return [dict(record) for record in self._connections]

    # ----- updates -----
    def add_station(self, name, lines=()):
        """Add a new station that is not yet connected to the network."""
        cleaned = _normalize_name(name)
        if self.resolve_station(cleaned) is not None:
            raise ValueError(f"Station '{cleaned}' already exists")
        clean_lines = [str(line).strip() for line in lines if str(line).strip()]
        self._register_station(cleaned, clean_lines)
        return cleaned

    def add_line(self, line_name, station_names, distances):
        """Add a new line through an ordered list of existing stations.

        Args:
            line_name: name of the new line (must not exist yet).
            station_names: ordered station names of the line (at least two).
            distances: distances in meters between consecutive stations.

        Returns:
            The number of connections added.
        """
        line = _normalize_name(line_name)
        if line in self.lines():
            raise ValueError(f"Line '{line}' already exists")
        resolved = []
        for name in station_names:
            official = self.resolve_station(name)
            if official is None:
                raise ValueError(f"Station '{name}' does not exist")
            resolved.append(official)
        if len(resolved) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(resolved) - 1:
            raise ValueError("distances must contain one value per consecutive station pair")
        normalized = [_normalize_distance(d) for d in distances]
        for index, distance in enumerate(normalized):
            self._add_connection_record(resolved[index], resolved[index + 1], distance, line)
        return len(normalized)

    def update_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Returns:
            The (possibly new) official name of the station.
        """
        official = self.resolve_station(old_name)
        if official is None:
            raise ValueError(f"Station '{old_name}' does not exist")

        if new_name is not None:
            target = _normalize_name(new_name)
            existing = self.resolve_station(target)
            if existing is not None and existing != official:
                raise ValueError(f"Station '{target}' already exists")
            if target != official:
                number = self.station_to_number.pop(official)
                self.station_to_number[target] = number
                self.number_to_station[number] = target
                self._station_order[self._station_order.index(official)] = target
                self.graph.station_lines[target] = self.graph.station_lines.pop(official)
                for record in self._connections:
                    if record["source"] == official:
                        record["source"] = target
                    if record["dest"] == official:
                        record["dest"] = target
                official = target

        if lines is not None:
            clean_lines = [str(line).strip() for line in lines if str(line).strip()]
            self.graph.set_station_lines(official, clean_lines)
        return official

    def update_distance(self, a, b, distance, line=None):
        """Update the distance between two adjacent stations.

        Args:
            a, b: station names (any accepted spelling).
            distance: new distance in meters.
            line: restrict the update to this line (None updates all connections).

        Returns:
            The number of connections updated.
        """
        name_a = self.resolve_station(a)
        name_b = self.resolve_station(b)
        if name_a is None or name_b is None:
            raise ValueError("Both stations must exist")
        distance = _normalize_distance(distance)
        num_a = self.station_to_number[name_a]
        num_b = self.station_to_number[name_b]

        updated = 0
        for edge in self.graph.neighbors(num_a):
            if edge.other(num_a) == num_b and (line is None or edge.line == line):
                edge.distance = distance
                updated += 1
        if updated == 0:
            raise ValueError(f"No connection between '{name_a}' and '{name_b}'")

        for record in self._connections:
            pair = {record["source"], record["dest"]}
            if pair == {name_a, name_b} and (line is None or record["line"] == line):
                record["distance"] = distance
        return updated

    def to_data(self):
        """Export the network in the subway_data.json structure."""
        stations = [
            {"name": name, "lines": self.graph.get_station_lines(name)}
            for name in self._station_order
        ]
        return {"stations": stations, "connections": self.connection_records()}
