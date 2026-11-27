"""
Subway network management.

SubwayNetwork builds the weighted undirected Graph from the dataset, assigns
station numbers, resolves user-supplied station names to official names, and
supports data updates (adding lines, modifying stations, updating distances).
"""

from data_loader import DATA_FILE_PATH, load_subway_data
from models import Edge, Graph


class SubwayNetwork:
    """Subway network model backed by a Graph.

    Attributes:
        graph: The Graph instance holding stations, lines and edges.
        source_path: Path of the dataset file the network was loaded from.
    """

    def __init__(self, data=None, path=None):
        self.source_path = path or DATA_FILE_PATH
        if data is None:
            data = load_subway_data(self.source_path)
        self.graph = Graph()
        self._normalized_index = {}
        self._build(data)

    # ----- helpers ------------------------------------------------------------
    @staticmethod
    def normalize_name(name):
        """Normalize a station name for lookup (strip, lowercase, drop spaces and trailing '站')."""
        text = str(name).strip().replace(" ", "").lower()
        if text.endswith("站") and len(text) > 1:
            text = text[:-1]
        return text

    def _register_station(self, name, lines):
        """Create a new station with the next free number."""
        if self.graph.has_station(name):
            raise ValueError(f"Station '{name}' already exists")
        number = self.graph.station_count() + 1
        self.graph.register_station(name, number)
        self.graph.set_station_lines(name, lines)
        self._normalized_index[self.normalize_name(name)] = name
        return number

    def _ensure_station(self, name, lines):
        """Return the number of a station, creating it if needed."""
        if self.graph.has_station(name):
            return self.graph.number_of(name)
        return self._register_station(name, lines)

    def _build(self, data):
        """Populate the graph from the dataset dictionary."""
        stations = data.get("stations")
        connections = data.get("connections")
        if not isinstance(stations, list) or not isinstance(connections, list):
            raise ValueError("Dataset must contain 'stations' and 'connections' lists")

        for station in stations:
            name = str(station["name"]).strip()
            lines = [str(line).strip() for line in station.get("lines", [])]
            if self.graph.has_station(name):
                merged = self.graph.station_lines[name] + lines
                self.graph.set_station_lines(name, merged)
            else:
                self._register_station(name, lines)

        for conn in connections:
            src = str(conn["source"]).strip()
            dst = str(conn["dest"]).strip()
            line = str(conn["line"]).strip()
            distance = float(conn["distance"])
            if distance <= 0:
                raise ValueError(f"Non-positive distance between '{src}' and '{dst}'")
            src_no = self._ensure_station(src, [line])
            dst_no = self._ensure_station(dst, [line])
            self.graph.add_edge(Edge(src_no, dst_no, distance, line))

    # ----- queries ------------------------------------------------------------
    def has_station(self, name):
        """Return True if the exact official station name exists."""
        return self.graph.has_station(name)

    def resolve_station(self, name):
        """Map a user-supplied name to the official station name, or None if unknown."""
        if name is None:
            return None
        stripped = str(name).strip()
        if self.graph.has_station(stripped):
            return stripped
        return self._normalized_index.get(self.normalize_name(stripped))

    def number_of(self, name):
        """Return the number of an official station name."""
        return self.graph.number_of(name)

    def name_of(self, number):
        """Return the official name of a station number."""
        return self.graph.name_of(number)

    def lines_of(self, name):
        """Return the lines serving a station."""
        return list(self.graph.station_lines.get(name, []))

    def station_names(self):
        """Return all official station names, sorted alphabetically."""
        return sorted(self.graph.station_to_number)

    def line_names(self):
        """Return all line names found in stations or connections, sorted."""
        names = set()
        for lines in self.graph.station_lines.values():
            names.update(lines)
        for edge in self.graph.edges:
            names.add(edge.line)
        return sorted(names)

    def line_stations(self, line):
        """Return the stations served by a line, in station-number order."""
        result = []
        for number in sorted(self.graph.number_to_station):
            name = self.graph.name_of(number)
            if line in self.graph.station_lines.get(name, []):
                result.append(name)
        return result

    def transfer_stations(self):
        """Return names of stations served by more than one line."""
        return [name for name in self.station_names() if len(self.graph.station_lines[name]) > 1]

    # ----- updates ------------------------------------------------------------
    def add_line(self, line_name, station_names, distances):
        """Add a new line as a chain of stations with given inter-station distances.

        Args:
            line_name: Name of the new line (must not exist yet).
            station_names: Ordered list of station names (existing or new).
            distances: Distances in meters between consecutive stations.
        """
        line = str(line_name).strip()
        if not line:
            raise ValueError("Line name must not be empty")
        if line in self.line_names():
            raise ValueError(f"Line '{line}' already exists")
        names = [str(s).strip() for s in station_names]
        if len(names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(names)) != len(names):
            raise ValueError("Station names on a line must be unique")
        if len(distances) != len(names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        for distance in distances:
            if float(distance) <= 0:
                raise ValueError("Distances must be positive")

        numbers = []
        for name in names:
            if self.graph.has_station(name):
                number = self.graph.number_of(name)
                current = self.graph.station_lines[name]
                if line not in current:
                    self.graph.set_station_lines(name, current + [line])
            else:
                number = self._register_station(name, [line])
            numbers.append(number)

        for i, distance in enumerate(distances):
            self.graph.add_edge(Edge(numbers[i], numbers[i + 1], float(distance), line))
        return numbers

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its line list. Returns the official name."""
        official = self.resolve_station(old_name)
        if official is None:
            raise KeyError(f"Unknown station '{old_name}'")
        if new_name is not None and str(new_name).strip() and str(new_name).strip() != official:
            target = str(new_name).strip()
            if self.graph.has_station(target):
                raise ValueError(f"Station '{target}' already exists")
            self.graph.rename_station(official, target)
            self._normalized_index.pop(self.normalize_name(official), None)
            self._normalized_index[self.normalize_name(target)] = target
            official = target
        if lines is not None:
            self.graph.set_station_lines(official, [str(x).strip() for x in lines])
        return official

    def update_distance(self, name_a, name_b, distance, line=None):
        """Update the distance between two adjacent stations. Returns the number of edges updated."""
        a = self.resolve_station(name_a)
        b = self.resolve_station(name_b)
        if a is None or b is None:
            raise KeyError("Both stations must exist")
        if float(distance) <= 0:
            raise ValueError("Distance must be positive")
        na = self.graph.number_of(a)
        nb = self.graph.number_of(b)
        updated = 0
        for edge in self.graph.adjacent(na):
            if edge.other(na) == nb and (line is None or edge.line == line):
                edge.distance = float(distance)
                updated += 1
        if updated == 0:
            raise KeyError(f"No connection between '{a}' and '{b}'")
        return updated
