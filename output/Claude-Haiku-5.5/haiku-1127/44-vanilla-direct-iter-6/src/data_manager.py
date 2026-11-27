"""Data integrity checks and data update helpers for the subway dataset.

All update helpers operate on the parsed dataset dictionary (the structure
returned by ``data_loader.load_subway_data``) and return it after modification.
Use ``data_loader.save_subway_data`` to persist the changes.
"""

from collections import defaultdict

# Lines that must be represented in the dataset.
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_STATIONS_PER_MAIN_LINE = 2
MAX_REASONABLE_DISTANCE_M = 8000


class IntegrityReport:
    """Collects errors and warnings found by ``check_data_integrity``."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def add_error(self, message):
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def render(self):
        """Return a human-readable text summary of the report."""
        lines = ["Data integrity check: " + ("PASSED" if self.ok else "FAILED")]
        lines.append(f"Errors: {len(self.errors)}")
        for message in self.errors:
            lines.append(f"  [ERROR] {message}")
        lines.append(f"Warnings: {len(self.warnings)}")
        for message in self.warnings:
            lines.append(f"  [WARN] {message}")
        return "\n".join(lines)


def _is_valid_distance(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value > 0)


def check_data_integrity(data):
    """Run integrity checks on the subway dataset.

    Checks performed:
        * structure and station name uniqueness
        * station coverage of the main lines
        * connection references, distance accuracy and duplicates
        * bidirectional consistency of connections
        * network connectivity

    Args:
        data: The parsed dataset dictionary.

    Returns:
        IntegrityReport: The findings.
    """
    report = IntegrityReport()
    if not isinstance(data, dict):
        report.add_error("Dataset must be a JSON object")
        return report

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        report.add_error("'stations' must be a list")
        stations = []
    if not isinstance(connections, list):
        report.add_error("'connections' must be a list")
        connections = []

    # ----- station data -------------------------------------------------
    station_lines = {}
    for index, station in enumerate(stations):
        if not isinstance(station, dict) or not station.get("name"):
            report.add_error(f"Station entry #{index} has no name")
            continue
        name = station["name"]
        if name in station_lines:
            report.add_error(f"Duplicate station name: {name}")
        lines = station.get("lines")
        if not isinstance(lines, list) or not lines:
            report.add_warning(f"Station '{name}' has no line affiliation")
            station_lines[name] = set()
        else:
            station_lines[name] = set(lines)

    # ----- connection data ----------------------------------------------
    distance_map = {}
    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            report.add_error(f"Connection entry #{index} is not an object")
            continue
        missing = [k for k in ("source", "dest", "distance", "line") if k not in conn]
        if missing:
            report.add_error(f"Connection entry #{index} is missing fields: {missing}")
            continue
        src, dst, line, dist = conn["source"], conn["dest"], conn["line"], conn["distance"]
        label = f"{src} -> {dst} ({line})"
        if src not in station_lines or dst not in station_lines:
            report.add_error(f"Connection {label} references an unknown station")
            continue
        if not _is_valid_distance(dist):
            report.add_error(f"Connection {label} has an invalid distance: {dist!r}")
            continue
        if dist > MAX_REASONABLE_DISTANCE_M:
            report.add_warning(f"Connection {label} distance {dist} m looks too large")
        if line not in station_lines[src] or line not in station_lines[dst]:
            report.add_warning(f"Connection {label}: line not listed for both stations")
        key = (src, dst, line)
        if key in distance_map:
            report.add_error(f"Duplicate connection: {label}")
        distance_map[key] = dist

    # ----- bidirectional consistency ------------------------------------
    for (src, dst, line), dist in distance_map.items():
        reverse = (dst, src, line)
        if reverse not in distance_map:
            report.add_warning(f"Connection {src} -> {dst} ({line}) has no reverse entry")
        elif distance_map[reverse] != dist:
            report.add_error(
                f"Distance mismatch between {src} and {dst} on {line}: "
                f"{dist} m vs {distance_map[reverse]} m")

    # ----- line coverage ------------------------------------------------
    for main_line in REQUIRED_MAIN_LINES:
        count = sum(1 for lines in station_lines.values() if main_line in lines)
        if count == 0:
            report.add_error(f"Main line '{main_line}' has no stations in the dataset")
        elif count < MIN_STATIONS_PER_MAIN_LINE:
            report.add_warning(f"Main line '{main_line}' has only {count} station(s)")

    # ----- connectivity -------------------------------------------------
    adjacency = defaultdict(set)
    for src, dst, _ in distance_map:
        adjacency[src].add(dst)
        adjacency[dst].add(src)
    visited = set()
    components = 0
    for start in sorted(station_lines):
        if start in visited:
            continue
        components += 1
        stack = [start]
        visited.add(start)
        while stack:
            node = stack.pop()
            for neighbour in adjacency[node]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    stack.append(neighbour)
    if components > 1:
        report.add_warning(f"The network is split into {components} disconnected groups")

    return report


def add_line(data, line_name, station_names, distances):
    """Add a new line with its ordered stations and inter-station distances.

    Existing stations are reused (and gain the new line); unknown stations are
    created. Connections are added in both directions.

    Args:
        data: The parsed dataset dictionary (modified in place).
        line_name: Name of the new line.
        station_names: Ordered list of station names on the line.
        distances: List of ``len(station_names) - 1`` distances in meters.

    Returns:
        dict: The modified dataset.

    Raises:
        ValueError: If the input is inconsistent or the line already exists.
    """
    line_name = " ".join(str(line_name).split())
    if not line_name:
        raise ValueError("line name must not be empty")
    if len(station_names) < 2:
        raise ValueError("a line needs at least two stations")
    if len(set(station_names)) != len(station_names):
        raise ValueError("a station appears more than once on the line")
    if len(distances) != len(station_names) - 1:
        raise ValueError("expected one distance per consecutive station pair")
    for dist in distances:
        if isinstance(dist, bool) or not isinstance(dist, int) or dist <= 0:
            raise ValueError(f"invalid distance: {dist!r}")
    if any(conn.get("line") == line_name for conn in data["connections"]):
        raise ValueError(f"line already exists: {line_name}")

    index = {station["name"]: station for station in data["stations"]}
    for name in station_names:
        station = index.get(name)
        if station is None:
            station = {"name": name, "lines": [line_name]}
            data["stations"].append(station)
            index[name] = station
        elif line_name not in station["lines"]:
            station["lines"].append(line_name)

    pairs = zip(station_names, station_names[1:])
    for (first, second), dist in zip(pairs, distances):
        data["connections"].append(
            {"source": first, "dest": second, "distance": dist, "line": line_name})
        data["connections"].append(
            {"source": second, "dest": first, "distance": dist, "line": line_name})
    return data


def modify_station(data, name, new_name=None, lines=None):
    """Rename a station and/or replace its line list.

    Args:
        data: The parsed dataset dictionary (modified in place).
        name: Current station name.
        new_name: Optional new name; connections are updated accordingly.
        lines: Optional replacement list of lines.

    Returns:
        dict: The modified dataset.

    Raises:
        KeyError: If the station does not exist.
        ValueError: If the new name is already used.
    """
    station = next((s for s in data["stations"] if s["name"] == name), None)
    if station is None:
        raise KeyError(f"unknown station: {name}")
    if new_name and new_name != name:
        if any(s["name"] == new_name for s in data["stations"]):
            raise ValueError(f"station already exists: {new_name}")
        station["name"] = new_name
        for conn in data["connections"]:
            if conn["source"] == name:
                conn["source"] = new_name
            if conn["dest"] == name:
                conn["dest"] = new_name
    if lines is not None:
        station["lines"] = list(lines)
    return data


def update_distance(data, source, dest, distance, line=None):
    """Update the distance between two adjacent stations (both directions).

    Args:
        data: The parsed dataset dictionary (modified in place).
        source: One station name.
        dest: The adjacent station name.
        distance: New distance in meters (positive integer).
        line: Optional line filter when several lines connect the pair.

    Returns:
        int: Number of connection entries updated.

    Raises:
        ValueError: If the distance is invalid.
        KeyError: If no matching connection exists.
    """
    if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
        raise ValueError("distance must be a positive integer number of meters")
    count = 0
    for conn in data["connections"]:
        if line is not None and conn["line"] != line:
            continue
        forward = conn["source"] == source and conn["dest"] == dest
        backward = conn["source"] == dest and conn["dest"] == source
        if forward or backward:
            conn["distance"] = distance
            count += 1
    if count == 0:
        raise KeyError(f"no connection between {source} and {dest}")
    return count
