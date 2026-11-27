"""Data integrity checks and data update operations for the subway network."""

from models import UnknownStationError  # noqa: F401  (re-exported for callers)


# Main lines that must be represented in the data set (PRD section 4.1).
REQUIRED_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8",
    "Line 10", "Line 13", "Line 14", "Line 15", "Changping Line",
    "Yizhuang Line", "Fangshan Line", "Airport Line",
)

# Plausible range of distances between adjacent stations (meters).
MIN_ADJACENT_DISTANCE_M = 100
MAX_ADJACENT_DISTANCE_M = 5000


def _count_components(network):
    """Count weakly connected components of the station graph."""
    parent = {number: number for number in network.number_to_station}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for edge in network.graph.edges():
        root_a = find(edge.source)
        root_b = find(edge.dest)
        if root_a != root_b:
            parent[root_a] = root_b
    return len({find(number) for number in parent})


def check_integrity(network):
    """Run the data integrity checks on a ``SubwayNetwork``.

    Checks performed:
        * coverage of the required main lines,
        * connection integrity (self loops, duplicates, reverse directions,
          isolated stations, line consistency, connectivity),
        * accuracy of distance data.

    Returns:
        list[str]: Messages prefixed with "[ERROR]" or "[WARNING]".
            An empty list means no problems were found.
    """
    messages = []

    # 1. Station data coverage.
    lines_present = set(network.line_names)
    stations_per_line = {}
    for name in network.station_names():
        for line in network.lines_of(name):
            stations_per_line[line] = stations_per_line.get(line, 0) + 1
    for line in REQUIRED_LINES:
        if line not in lines_present:
            messages.append(f"[ERROR] Required line is missing from data: {line}")
        elif stations_per_line.get(line, 0) < 2:
            messages.append(f"[WARNING] Line has fewer than 2 stations: {line}")

    # 2. Connection integrity and distance accuracy.
    directed_keys = set()
    edges = list(network.graph.edges())
    for edge in edges:
        directed_keys.add((edge.source, edge.dest, edge.line))

    seen = set()
    for edge in edges:
        src_name = network.get_name(edge.source)
        dst_name = network.get_name(edge.dest)
        label = f"{src_name} -> {dst_name} ({edge.line})"
        if edge.source == edge.dest:
            messages.append(f"[ERROR] Self loop connection: {label}")
        if edge.distance <= 0:
            messages.append(f"[ERROR] Non-positive distance {edge.distance} m: {label}")
        elif not MIN_ADJACENT_DISTANCE_M <= edge.distance <= MAX_ADJACENT_DISTANCE_M:
            messages.append(
                f"[WARNING] Distance {edge.distance} m outside expected range "
                f"{MIN_ADJACENT_DISTANCE_M}-{MAX_ADJACENT_DISTANCE_M} m: {label}")
        key = (edge.source, edge.dest, edge.line)
        if key in seen:
            messages.append(f"[WARNING] Duplicate connection: {label}")
        seen.add(key)
        if (edge.dest, edge.source, edge.line) not in directed_keys:
            messages.append(f"[WARNING] No reverse direction for connection: {label}")
        if edge.line not in network.lines_of(src_name):
            messages.append(f"[WARNING] Station '{src_name}' does not list line {edge.line}")
        if edge.line not in network.lines_of(dst_name):
            messages.append(f"[WARNING] Station '{dst_name}' does not list line {edge.line}")

    # 3. Isolated stations.
    connected = {edge.source for edge in edges} | {edge.dest for edge in edges}
    for number, name in network.number_to_station.items():
        if number not in connected:
            messages.append(f"[WARNING] Isolated station without connections: {name}")

    # 4. Connectivity of the whole network.
    components = _count_components(network)
    if components > 1:
        messages.append(f"[WARNING] Network has {components} disconnected components")

    return messages


def has_errors(messages):
    """Return True if any message in ``messages`` is an error."""
    return any(message.startswith("[ERROR]") for message in messages)


class DataManager:
    """Data update operations on a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def add_line(self, line_name, station_names, distances):
        """Add a new line with its ordered stations.

        Args:
            line_name: Name of the new line (must not exist yet).
            station_names: Ordered list of station names (at least 2).
                Existing stations become transfer stations.
            distances: Distances in meters between consecutive stations
                (length must be ``len(station_names) - 1``).

        Raises:
            ValueError: If the input is invalid.
        """
        line_name = str(line_name).strip()
        if not line_name:
            raise ValueError("Line name must not be empty")
        if line_name in self.network.line_names:
            raise ValueError(f"Line already exists: {line_name}")
        if len(station_names) < 2:
            raise ValueError("A line needs at least two stations")
        if len(distances) != len(station_names) - 1:
            raise ValueError("Number of distances must be one less than number of stations")
        if any(int(d) <= 0 for d in distances):
            raise ValueError("Distances must be positive")

        for name in station_names:
            self.network.add_station(name, [line_name])
        for (first, second), distance in zip(zip(station_names, station_names[1:]), distances):
            self.network.add_connection(first, second, distance, line_name)
            self.network.add_connection(second, first, distance, line_name)

    def modify_station(self, old_name, new_name=None, lines=None):
        """Rename a station and/or replace its lines."""
        if new_name is not None and new_name.strip() != old_name:
            self.network.rename_station(old_name, new_name.strip())
            old_name = new_name.strip()
        if lines is not None:
            self.network.set_station_lines(old_name, lines)

    def update_distance(self, source, dest, distance, line=None):
        """Update the distance of the connection(s) from ``source`` to ``dest``.

        Returns:
            int: Number of connections updated.

        Raises:
            ValueError: If the distance is not positive.
            UnknownStationError: If a station does not exist or no matching
                connection is found.
        """
        distance = int(distance)
        if distance <= 0:
            raise ValueError("Distance must be positive")
        src = self.network.get_number(source)
        dst = self.network.get_number(dest)
        updated = 0
        for edge in self.network.graph.adjacent(src):
            if edge.dest == dst and (line is None or edge.line == line):
                edge.distance = distance
                updated += 1
        if updated == 0:
            raise UnknownStationError(
                f"No connection from '{source}' to '{dest}'" +
                (f" on line '{line}'" if line else ""))
        return updated

    def export_data(self):
        """Return the current network as a dict in the data file schema."""
        stations = []
        for name in self.network.station_names():
            stations.append({"name": name, "lines": self.network.lines_of(name)})
        connections = []
        for edge in self.network.graph.edges():
            connections.append({
                "source": self.network.get_name(edge.source),
                "dest": self.network.get_name(edge.dest),
                "distance": edge.distance,
                "line": edge.line,
            })
        return {"stations": stations, "connections": connections}
