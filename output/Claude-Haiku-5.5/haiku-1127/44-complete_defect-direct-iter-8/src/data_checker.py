"""Data integrity checks for the subway network (triggered by --check_data)."""

import math

from pathfinding import MODE_SHORTEST_DISTANCE  # noqa: F401  (keeps module graph explicit)

# Main lines that must be present in the network data.
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_STATIONS_PER_MAIN_LINE = 2
# Plausible range for a single inter-station distance, in meters.
MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _is_valid_number(value):
    """Return True for finite, positive, non-boolean numbers."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def _check_coverage(network, issues):
    """Verify that the main lines and their stations are present."""
    if network.station_count() == 0:
        issues.append("Coverage: the network contains no stations")
        return
    present = {line.lower(): line for line in network.line_names()}
    for required in REQUIRED_MAIN_LINES:
        actual = present.get(required.lower())
        if actual is None:
            issues.append(f"Coverage: main line '{required}' is missing from the network")
            continue
        count = len(network.stations_on_line(actual))
        if count < MIN_STATIONS_PER_MAIN_LINE:
            issues.append(f"Coverage: main line '{required}' has only {count} station(s)")


def _check_connections(network, issues):
    """Verify connection relationships and network connectivity."""
    graph = network.graph

    for name in sorted(network.undeclared_stations):
        issues.append(f"Connection: station '{name}' is referenced by a connection "
                      f"but not declared in the station list")

    vertices = graph.vertices()
    for number in vertices:
        if not graph.adjacent(number):
            issues.append(f"Connection: station '{network.name_of(number)}' has no connections")

    for name in network.station_names():
        number = network.number_of(name)
        incident_lines = {edge.line for edge in graph.adjacent(number)}
        for line in network.station_lines(name):
            if line not in incident_lines:
                issues.append(f"Connection: station '{name}' declares line '{line}' "
                              f"but has no connection on it")

    if vertices:
        start = vertices[0]
        seen = {start}
        stack = [start]
        while stack:
            node = stack.pop()
            for edge in graph.adjacent(node):
                nxt = edge.other(node)
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        unreachable = sorted(network.name_of(v) for v in vertices if v not in seen)
        if unreachable:
            issues.append(f"Connectivity: {len(unreachable)} station(s) cannot be reached from "
                          f"'{network.name_of(start)}': {', '.join(unreachable[:10])}")


def _check_distances(network, issues):
    """Verify distance data is valid, plausible, and consistent per station pair."""
    graph = network.graph
    pair_distances = {}
    for edge in graph.edges():
        label = f"{network.name_of(edge.source)} - {network.name_of(edge.dest)} ({edge.line})"
        if not _is_valid_number(edge.distance):
            issues.append(f"Distance: invalid distance {edge.distance!r} for {label}")
            continue
        if edge.distance < MIN_PLAUSIBLE_DISTANCE_M or edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
            issues.append(f"Distance: {edge.distance} m for {label} is outside the plausible range "
                          f"[{MIN_PLAUSIBLE_DISTANCE_M}, {MAX_PLAUSIBLE_DISTANCE_M}] m")
        pair = (min(edge.source, edge.dest), max(edge.source, edge.dest))
        pair_distances.setdefault(pair, set()).add(edge.distance)

    for (a, b), values in sorted(pair_distances.items()):
        if len(values) > 1:
            issues.append(f"Distance: conflicting distances {sorted(values)} between "
                          f"'{network.name_of(a)}' and '{network.name_of(b)}'")


def check_data_integrity(network):
    """Run all integrity checks on a SubwayNetwork.

    Returns:
        A list of human-readable issue strings. An empty list means the data passed.
    """
    issues = []
    _check_coverage(network, issues)
    _check_connections(network, issues)
    _check_distances(network, issues)
    return issues
