"""
Data integrity checks for the subway dataset.

Checks performed:
  * Station coverage: each main line has representative stations.
  * Connection integrity: endpoints exist, lines are served by both endpoints,
    no duplicate connections, graph connectivity, no isolated stations.
  * Distance accuracy: distances are positive numbers, with suspicious values flagged.
"""

from dataclasses import dataclass, field

MAIN_LINES = (
    "Line 1",
    "Line 2",
    "Line 4",
    "Line 5",
    "Line 6",
    "Line 8",
    "Line 10",
    "Line 13",
    "Line 14",
    "Line 15",
    "Changping Line",
    "Yizhuang Line",
    "Fangshan Line",
    "Airport Line",
)

# Minimum number of stations expected on each main line.
MIN_REPRESENTATIVE_STATIONS = 2
# Distances above this (meters) between adjacent stations are reported as suspicious.
MAX_PLAUSIBLE_DISTANCE_M = 5000


@dataclass
class IntegrityCheck:
    """Result of a data integrity check."""

    passed: bool
    messages: list = field(default_factory=list)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_integrity(data):
    """
    Run all integrity checks on the raw subway dataset.

    Args:
        data: dict loaded from ``subway_data.json``.

    Returns:
        IntegrityCheck: ``passed`` is False if any error was found; ``messages``
        lists every error, warning and a closing summary.
    """
    errors = []
    warnings = []

    stations = data.get("stations") if isinstance(data, dict) else None
    connections = data.get("connections") if isinstance(data, dict) else None
    if not isinstance(stations, list) or not isinstance(connections, list):
        return IntegrityCheck(False, ["[ERROR] dataset must contain 'stations' and 'connections' lists"])

    # ---- Station data ----------------------------------------------------
    station_lines = {}
    for index, entry in enumerate(stations):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
            errors.append(f"[ERROR] station entry #{index} has no valid name")
            continue
        name = entry["name"]
        if name in station_lines:
            errors.append(f"[ERROR] duplicate station name '{name}'")
            continue
        lines = entry.get("lines", [])
        if not isinstance(lines, list):
            errors.append(f"[ERROR] station '{name}' has an invalid line list")
            lines = []
        station_lines[name] = set(lines)

    # Station coverage of main lines.
    line_counts = {}
    for lines in station_lines.values():
        for line in lines:
            line_counts[line] = line_counts.get(line, 0) + 1
    for line in MAIN_LINES:
        count = line_counts.get(line, 0)
        if count == 0:
            errors.append(f"[ERROR] main line '{line}' has no stations in the dataset")
        elif count < MIN_REPRESENTATIVE_STATIONS:
            warnings.append(f"[WARN] main line '{line}' has only {count} representative station(s)")

    # ---- Connection data -------------------------------------------------
    seen = set()
    adjacency = {name: set() for name in station_lines}
    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            errors.append(f"[ERROR] connection #{index} is not an object")
            continue
        source = conn.get("source")
        dest = conn.get("dest")
        line = conn.get("line")
        distance = conn.get("distance")
        label = f"{source} - {dest} ({line})"

        if source not in station_lines:
            errors.append(f"[ERROR] connection {label}: unknown source station '{source}'")
        if dest not in station_lines:
            errors.append(f"[ERROR] connection {label}: unknown destination station '{dest}'")

        if source in station_lines and dest in station_lines:
            if line not in station_lines[source] or line not in station_lines[dest]:
                errors.append(f"[ERROR] connection {label}: line not served by both endpoints")
            adjacency[source].add(dest)
            adjacency[dest].add(source)

        if not _is_number(distance) or distance <= 0:
            errors.append(f"[ERROR] connection {label}: distance must be a positive number, got {distance!r}")
        else:
            if isinstance(distance, float) and not distance.is_integer():
                warnings.append(f"[WARN] connection {label}: distance {distance} is not whole meters")
            if distance > MAX_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"[WARN] connection {label}: distance {distance} m looks implausibly large")

        key = (frozenset((source, dest)), line)
        if key in seen:
            errors.append(f"[ERROR] duplicate connection {label}")
        seen.add(key)

    # Isolated stations and connectivity.
    isolated = [name for name, neighbours in adjacency.items() if not neighbours]
    for name in isolated:
        warnings.append(f"[WARN] station '{name}' has no connections")

    if station_lines:
        start = next(iter(station_lines))
        visited = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for nxt in adjacency.get(current, ()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        unreachable = len(station_lines) - len(visited)
        if unreachable > 0:
            warnings.append(f"[WARN] {unreachable} station(s) are not connected to the main network")

    messages = errors + warnings
    passed = not errors
    summary = (
        f"Summary: {len(station_lines)} stations, {len(connections)} connections, "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    messages.append(summary)
    if passed and not warnings:
        messages.append("[OK] data integrity check passed")
    return IntegrityCheck(passed, messages)
