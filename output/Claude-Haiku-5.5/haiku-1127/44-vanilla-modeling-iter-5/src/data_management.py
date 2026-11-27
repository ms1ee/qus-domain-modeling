"""Data integrity checks and data update operations for the subway dataset.

Update functions never mutate their input: they return a new dataset dict,
which can be turned into a SubwayNetwork via ``SubwayNetwork.from_data``.
"""

import copy
from dataclasses import dataclass, field
from typing import List

MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000


@dataclass
class DataIntegrityReport:
    """Result of an integrity check.

    Attributes:
        passed: True when no issues were found.
        issues: human-readable description of each problem.
    """

    passed: bool
    issues: List[str] = field(default_factory=list)


def check_data_integrity(network):
    """Run coverage, connection and distance checks on a SubwayNetwork.

    Returns:
        DataIntegrityReport
    """
    issues = []

    # 1. Coverage of main lines.
    for line in MAIN_LINES:
        if line not in network.lines:
            issues.append(f"Coverage: main line '{line}' is missing from the network")
        elif len(network.lines[line]) < 2:
            issues.append(f"Coverage: main line '{line}' has fewer than 2 stations")

    # 2. Connection integrity and distance accuracy.
    declared = network.declared_stations
    seen = {}
    connected = set()
    for conn in network.connections:
        src, dst = conn["source"], conn["dest"]
        dist, line = conn["distance"], conn["line"]
        connected.add(src)
        connected.add(dst)

        for end in (src, dst):
            if end not in declared:
                issues.append(f"Connection: station '{end}' is referenced but not declared in stations")
        if src == dst:
            issues.append(f"Connection: self-loop on station '{src}' (line '{line}')")
        if not isinstance(dist, (int, float)) or dist <= 0:
            issues.append(f"Accuracy: non-positive distance {dist} between '{src}' and '{dst}'")
        elif dist < MIN_PLAUSIBLE_DISTANCE_M or dist > MAX_PLAUSIBLE_DISTANCE_M:
            issues.append(
                f"Accuracy: implausible distance {dist} m between '{src}' and '{dst}' on '{line}'"
            )

        for end in (src, dst):
            if line not in declared.get(end, []):
                issues.append(f"Connection: line '{line}' is not listed for station '{end}'")

        key = (frozenset((src, dst)), line)
        if key in seen and seen[key] != dist:
            issues.append(
                f"Connection: conflicting distances {seen[key]} and {dist} between "
                f"'{src}' and '{dst}' on '{line}'"
            )
        seen.setdefault(key, dist)

    # 3. Stations without any connection.
    for name in declared:
        if name not in connected:
            issues.append(f"Connection: station '{name}' has no connections")

    # 4. Network connectivity.
    graph = network.graph
    if network.station_to_number:
        start = next(iter(network.station_to_number.values()))
        reached = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            for edge in graph.neighbors(node):
                other = edge.other(node)
                if other not in reached:
                    reached.add(other)
                    stack.append(other)
        if len(reached) != graph.node_count:
            issues.append(
                f"Connectivity: {graph.node_count - len(reached)} station(s) unreachable "
                f"from '{network.get_station_name(start)}'"
            )

    return DataIntegrityReport(passed=not issues, issues=issues)


def _validate_distance(distance):
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError("distance must be a number of meters")
    if distance <= 0:
        raise ValueError("distance must be positive")
    return int(distance)


def add_line(data, line_name, station_names, distances):
    """Return a new dataset with an additional line.

    Args:
        data: current dataset dict.
        line_name: name of the new line (must not already exist).
        station_names: ordered list of station names on the line.
        distances: distances in meters between consecutive stations
            (len(station_names) - 1 values).

    Raises:
        ValueError: On invalid input or duplicate line name.
    """
    line_name = " ".join(str(line_name).split())
    if not line_name:
        raise ValueError("line name must not be empty")
    if len(station_names) < 2:
        raise ValueError("a line needs at least two stations")
    if len(distances) != len(station_names) - 1:
        raise ValueError("distances must have one value per consecutive station pair")
    for conn in data.get("connections", []):
        if conn.get("line") == line_name:
            raise ValueError(f"line '{line_name}' already exists")

    new_data = copy.deepcopy(data)
    stations = new_data.setdefault("stations", [])
    index = {item["name"]: item for item in stations}
    for name in station_names:
        if name not in index:
            entry = {"name": name, "lines": [line_name]}
            stations.append(entry)
            index[name] = entry
        elif line_name not in index[name].setdefault("lines", []):
            index[name]["lines"].append(line_name)

    connections = new_data.setdefault("connections", [])
    for i, dist in enumerate(distances):
        connections.append({
            "source": station_names[i],
            "dest": station_names[i + 1],
            "distance": _validate_distance(dist),
            "line": line_name,
        })
    return new_data


def modify_station(data, old_name, new_name=None, lines=None):
    """Return a new dataset with a station renamed and/or its lines replaced.

    Raises:
        KeyError: If the station does not exist.
        ValueError: If the new name is already used by another station.
    """
    new_data = copy.deepcopy(data)
    stations = new_data.get("stations", [])
    target = next((s for s in stations if s.get("name") == old_name), None)
    if target is None:
        raise KeyError(f"station '{old_name}' does not exist")

    if new_name and new_name != old_name:
        if any(s.get("name") == new_name for s in stations):
            raise ValueError(f"station '{new_name}' already exists")
        target["name"] = new_name
        for conn in new_data.get("connections", []):
            if conn.get("source") == old_name:
                conn["source"] = new_name
            if conn.get("dest") == old_name:
                conn["dest"] = new_name
    if lines is not None:
        unique = []
        for line in lines:
            if line not in unique:
                unique.append(line)
        target["lines"] = unique
    return new_data


def update_distance(data, station_a, station_b, line, distance):
    """Return a new dataset with the distance of one connection updated.

    Raises:
        KeyError: If no matching connection exists.
        ValueError: If the distance is invalid.
    """
    value = _validate_distance(distance)
    new_data = copy.deepcopy(data)
    found = False
    for conn in new_data.get("connections", []):
        if conn.get("line") == line and {conn.get("source"), conn.get("dest")} == {station_a, station_b}:
            conn["distance"] = value
            found = True
    if not found:
        raise KeyError(f"no connection on '{line}' between '{station_a}' and '{station_b}'")
    return new_data
