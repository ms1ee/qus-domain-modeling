"""Data management: loading, graph construction, and data update operations."""

from data_loader import DATA_FILE_PATH, load_subway_data, save_subway_data
from models import Edge, Graph

DATA_VERSION = "1.0"


def _normalize(name):
    """Normalize a station name for lookup: remove whitespace and ignore ASCII case."""
    return "".join(str(name).split()).lower()


def _validate_distance(distance):
    """Ensure a distance is a positive number of meters; return it as int."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("Distance must be a number of meters")
    if distance <= 0:
        raise ValueError("Distance must be positive")
    return int(distance)


class DataManager:
    """Manages the subway network data and the derived graph.

    Station numbers are assigned in order of first appearance (stations list
    first, then connection endpoints). Each station name is one graph node,
    so interchange stations are naturally shared by all of their lines.
    """

    def __init__(self, data_source=DATA_FILE_PATH):
        self.data_source = data_source
        self.version = DATA_VERSION
        self.data = load_subway_data(data_source)
        self.graph = Graph()
        self.station_numbers = {}   # station name -> station number
        self.number_to_name = {}    # station number -> station name
        self._normalized = {}       # normalized name -> canonical name
        self.rebuild()

    # ------------------------------------------------------------------ build
    def rebuild(self):
        """(Re)build the graph and lookup tables from the raw data."""
        stations = self.data.get("stations", [])
        connections = self.data.get("connections", [])

        numbers = {}
        names = {}
        station_lines = {}

        def ensure(name):
            if name not in numbers:
                number = len(numbers)
                numbers[name] = number
                names[number] = name
                station_lines[name] = []
            return numbers[name]

        def attach_line(name, line):
            if line and line not in station_lines[name]:
                station_lines[name].append(line)

        for record in stations:
            name = record["name"]
            ensure(name)
            for line in record.get("lines", []):
                attach_line(name, line)

        for conn in connections:
            for key in ("source", "dest"):
                name = conn[key]
                ensure(name)
                attach_line(name, conn.get("line"))

        graph = Graph()
        for number in numbers.values():
            graph.add_node(number)
        for name, lines in station_lines.items():
            graph.set_station_lines(name, lines)
        for conn in connections:
            graph.add_edge(Edge(
                numbers[conn["source"]],
                numbers[conn["dest"]],
                conn["distance"],
                conn.get("line", ""),
            ))

        self.graph = graph
        self.station_numbers = numbers
        self.number_to_name = names
        self._normalized = {}
        for name in numbers:
            self._normalized.setdefault(_normalize(name), name)

    # ----------------------------------------------------------------- lookup
    def station_names(self):
        """Return all station names in numbering order."""
        return list(self.station_numbers.keys())

    def has_station(self, name):
        return name in self.station_numbers

    def standardize_station_name(self, raw_name):
        """Map user input to the official station name, or None if unknown."""
        if raw_name is None:
            return None
        key = _normalize(raw_name)
        if not key:
            return None
        return self._normalized.get(key)

    def lines(self):
        """Return the sorted list of all line names in the dataset."""
        found = set()
        for record in self.data.get("stations", []):
            found.update(record.get("lines", []))
        for conn in self.data.get("connections", []):
            if conn.get("line"):
                found.add(conn["line"])
        return sorted(found)

    def lines_of(self, station_name):
        return list(self.graph.station_lines.get(station_name, []))

    def is_transfer_station(self, station_name):
        return self.graph.is_transfer_station(station_name)

    # ----------------------------------------------------------------- update
    def add_line(self, line_name, station_names, distances):
        """Add a new line through the given consecutive stations.

        Args:
            line_name: Name of the new line.
            station_names: Ordered station names along the line.
            distances: Distances in meters between consecutive stations.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.lines():
            raise ValueError(f"Line '{line_name}' already exists")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Exactly one distance is required between consecutive stations")
        checked = [_validate_distance(d) for d in distances]

        declared = {record["name"]: record for record in self.data.setdefault("stations", [])}
        for name in station_names:
            if name in declared:
                record_lines = declared[name].setdefault("lines", [])
                if line_name not in record_lines:
                    record_lines.append(line_name)
            else:
                record = {"name": name, "lines": [line_name]}
                self.data["stations"].append(record)
                declared[name] = record

        for index, distance in enumerate(checked):
            self.data.setdefault("connections", []).append({
                "source": station_names[index],
                "dest": station_names[index + 1],
                "distance": distance,
                "line": line_name,
            })
        self.rebuild()

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If the new name is already used by another station.
        """
        if old_name not in self.station_numbers:
            raise KeyError(f"Station '{old_name}' does not exist")

        stations = self.data.setdefault("stations", [])
        record = next((r for r in stations if r["name"] == old_name), None)
        if record is None:
            record = {"name": old_name, "lines": []}
            stations.append(record)

        if new_name and new_name != old_name:
            if new_name in self.station_numbers:
                raise ValueError(f"Station '{new_name}' already exists")
            for rec in stations:
                if rec["name"] == old_name:
                    rec["name"] = new_name
            for conn in self.data.get("connections", []):
                if conn["source"] == old_name:
                    conn["source"] = new_name
                if conn["dest"] == old_name:
                    conn["dest"] = new_name

        if lines is not None:
            record["lines"] = [str(line) for line in lines]
        self.rebuild()

    def update_distance(self, source, dest, distance):
        """Update the distance of all connections between two stations.

        Returns:
            Number of connections updated.

        Raises:
            KeyError: If no connection exists between the two stations.
            ValueError: If the distance is invalid.
        """
        new_distance = _validate_distance(distance)
        count = 0
        for conn in self.data.get("connections", []):
            if {conn["source"], conn["dest"]} == {source, dest}:
                conn["distance"] = new_distance
                count += 1
        if count == 0:
            raise KeyError(f"No connection between '{source}' and '{dest}'")
        self.rebuild()
        return count

    def save(self, path=None):
        """Persist the current data to a JSON file (defaults to the source file)."""
        save_subway_data(self.data, path or self.data_source)
