"""Data management: integrity checks and data update operations."""

from collections import deque

from models import natural_sort_key  # noqa: F401  (re-exported for convenience)

# Representative stations of main lines used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Xidan", "Guomao"],
    "Line 2": ["Xizhimen", "Dongzhimen", "Qianmen"],
    "Line 4": ["Xizhimen", "Yuanmingyuan"],
    "Line 5": ["Dongsi"],
    "Line 8": ["Gulou Dajie"],
    "Line 10": ["Guomao"],
    "Line 13": ["Huilongguan"],
}

MAX_NORMAL_SEGMENT_DISTANCE_M = 5000


class IntegrityReport:
    """Collects errors, warnings and informational messages from a data check."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def add_error(self, message):
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def add_info(self, message):
        self.info.append(message)

    def has_errors(self):
        return bool(self.errors)

    def format(self):
        """Return a human-readable text report."""
        out = ["Data integrity check report", "-" * 40]
        out.extend(f"[INFO]    {message}" for message in self.info)
        out.extend(f"[WARNING] {message}" for message in self.warnings)
        out.extend(f"[ERROR]   {message}" for message in self.errors)
        out.append("-" * 40)
        out.append(f"Errors: {len(self.errors)}, warnings: {len(self.warnings)}")
        out.append("Result: " + ("FAILED" if self.has_errors() else "PASSED"))
        return "\n".join(out)


class DataManager:
    """Integrity checks and update operations on a loaded Network."""

    def __init__(self, network):
        self.network = network

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    def check_integrity(self, representative_stations=None):
        """Run all integrity checks and return an IntegrityReport."""
        report = IntegrityReport()
        reps = REPRESENTATIVE_STATIONS if representative_stations is None else representative_stations
        report.add_info(
            f"Stations: {len(self.network.station_to_number)}, "
            f"connections: {self.network.graph.num_edges}, "
            f"lines: {len(self.network.all_line_names())}")
        self._check_station_coverage(report, reps)
        self._check_connections(report)
        self._check_distances(report)
        for message in self.network.load_warnings:
            report.add_warning(message)
        return report

    def _check_station_coverage(self, report, representative_stations):
        if not self.network.station_to_number:
            report.add_error("No stations are loaded")
            return
        available_lines = set(self.network.all_line_names())
        for line, stations in representative_stations.items():
            if line not in available_lines:
                report.add_warning(f"Main line '{line}' has no stations in the data")
                continue
            for station in stations:
                if not self.network.has_station(station):
                    report.add_warning(f"Representative station '{station}' of {line} is missing")
                elif line not in self.network.lines_of(station):
                    report.add_warning(f"Station '{station}' is not registered on {line}")

    def _check_connections(self, report):
        graph = self.network.graph
        for name in self.network.station_names():
            number = self.network.number_of(name)
            incident = graph.adjacent_edges(number)
            if not incident:
                report.add_warning(f"Station '{name}' has no connections")
                continue
            station_lines = set(self.network.lines_of(name))
            edge_lines = {edge.line for edge in incident}
            for line in sorted(station_lines - edge_lines):
                report.add_warning(f"Station '{name}' is listed on {line} but has no connection on it")
            for line in sorted(edge_lines - station_lines):
                report.add_warning(f"Station '{name}' has a connection on {line} but is not listed on it")

        # Overall connectivity.
        visited = set()
        component_sizes = []
        for vertex in graph.vertices():
            if vertex in visited:
                continue
            size = 0
            queue = deque([vertex])
            visited.add(vertex)
            while queue:
                current = queue.popleft()
                size += 1
                for neighbour in graph.neighbors(current):
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)
            component_sizes.append(size)
        if len(component_sizes) > 1:
            report.add_warning(f"Network is split into {len(component_sizes)} disconnected parts "
                               f"(sizes: {sorted(component_sizes, reverse=True)})")

        # Per-line continuity.
        for line in self.network.all_line_names():
            sections = self._count_line_sections(line)
            if sections > 1:
                report.add_warning(f"Line '{line}' is split into {sections} disconnected sections")

    def _count_line_sections(self, line):
        """Count connected components formed by the edges of one line."""
        graph = self.network.graph
        line_vertices = set()
        adjacency = {}
        for edge in graph.edges():
            if edge.line != line:
                continue
            line_vertices.add(edge.source)
            line_vertices.add(edge.dest)
            adjacency.setdefault(edge.source, []).append(edge.dest)
            adjacency.setdefault(edge.dest, []).append(edge.source)
        visited = set()
        sections = 0
        for vertex in line_vertices:
            if vertex in visited:
                continue
            sections += 1
            queue = deque([vertex])
            visited.add(vertex)
            while queue:
                current = queue.popleft()
                for neighbour in adjacency.get(current, []):
                    if neighbour not in visited:
                        visited.add(neighbour)
                        queue.append(neighbour)
        return sections

    def _check_distances(self, report):
        graph = self.network.graph
        for edge in graph.edges():
            source_name = self.network.name_of(edge.source)
            dest_name = self.network.name_of(edge.dest)
            label = f"{source_name} - {dest_name} ({edge.line})"
            distance = edge.distance
            if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance <= 0:
                report.add_error(f"Invalid distance {distance!r} on {label}")
            elif distance > MAX_NORMAL_SEGMENT_DISTANCE_M:
                report.add_warning(f"Unusually long distance {distance} m on {label}")

    # ------------------------------------------------------------------
    # Update operations
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_distance(distance):
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError("Distance must be a number of meters")
        if distance <= 0:
            raise ValueError("Distance must be positive")

    def add_line(self, line_name, station_names, distances):
        """Add a new line with an ordered station sequence.

        ``distances`` holds the distance in meters between consecutive stations
        and must have length ``len(station_names) - 1``.
        """
        name = (line_name or "").strip()
        if not name:
            raise ValueError("Line name cannot be empty")
        if name in self.network.all_line_names():
            raise ValueError(f"Line '{name}' already exists")
        stations = [station.strip() for station in station_names]
        if len(stations) < 2:
            raise ValueError("A line needs at least two stations")
        if len(set(stations)) != len(stations):
            raise ValueError("A line cannot contain the same station twice")
        if len(distances) != len(stations) - 1:
            raise ValueError("Number of distances must be one less than the number of stations")
        for distance in distances:
            self._validate_distance(distance)

        for station in stations:
            self.network.add_station(station, [name])
        for source, dest, distance in zip(stations, stations[1:], distances):
            self.network.add_connection(source, dest, int(distance), name)

    def modify_station(self, name, new_name=None, add_lines=(), remove_lines=()):
        """Rename a station and/or change its line membership. Returns the final name."""
        if not self.network.has_station(name):
            raise ValueError(f"Unknown station: {name}")
        target = name
        if new_name and new_name.strip() and new_name.strip() != name:
            target = new_name.strip()
            self.network.rename_station(name, target)

        lines = list(self.network.graph.station_lines.get(target, []))
        for line in add_lines:
            if line not in lines:
                lines.append(line)
        for line in remove_lines:
            if line in lines:
                lines.remove(line)
        self.network.graph.set_station_lines(target, lines)
        return target

    def update_distance(self, source_name, dest_name, distance, line=None):
        """Update the distance between two adjacent stations. Returns the number of edges changed."""
        self._validate_distance(distance)
        edges = self.network.connections_between(source_name, dest_name)
        if line is not None:
            edges = [edge for edge in edges if edge.line == line]
        if not edges:
            raise ValueError(f"No connection between '{source_name}' and '{dest_name}'"
                             + (f" on {line}" if line else ""))
        for edge in edges:
            edge.distance = int(distance)
        return len(edges)
