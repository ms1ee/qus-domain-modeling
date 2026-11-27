"""Data integrity checks for the raw subway dataset.

Checks performed:
    * structure: stations and connections are well-formed;
    * coverage: representative main lines are present and have stations;
    * connections: endpoints exist, lines are consistent, no duplicates or
      conflicting distances, no self-loops;
    * accuracy: distances are positive integers within a plausible range;
    * connectivity: the network forms a single connected component.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

PLAUSIBLE_MIN_DISTANCE_M = 50
PLAUSIBLE_MAX_DISTANCE_M = 10000


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def render(self) -> str:
        """Human-readable summary of the report."""
        lines = ["Data integrity check"]
        if not self.errors and not self.warnings:
            lines.append("  All checks passed.")
        for msg in self.errors:
            lines.append(f"  [ERROR] {msg}")
        for msg in self.warnings:
            lines.append(f"  [WARN]  {msg}")
        lines.append(
            f"Result: {'OK' if self.is_ok() else 'FAILED'} "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join(lines)


def _normalize_line(name: str) -> str:
    return "".join(str(name).split()).casefold()


def check_data_integrity(data: dict) -> IntegrityReport:
    """Run all integrity checks on the parsed dataset."""
    report = IntegrityReport()
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        report.errors.append("'stations' must be a list")
        stations = []
    if not isinstance(connections, list):
        report.errors.append("'connections' must be a list")
        connections = []

    # ----- stations -------------------------------------------------------
    names: set[str] = set()
    station_lines: dict[str, list[str]] = {}
    for idx, station in enumerate(stations):
        if not isinstance(station, dict) or not isinstance(station.get("name"), str) \
                or not station["name"].strip():
            report.errors.append(f"station #{idx} has no valid name")
            continue
        name = station["name"]
        if name in names:
            report.errors.append(f"duplicate station name '{name}'")
        names.add(name)
        lines = station.get("lines")
        if not isinstance(lines, list) or not lines:
            report.errors.append(f"station '{name}' has no lines")
            station_lines[name] = []
        else:
            station_lines[name] = [str(line) for line in lines]

    # ----- connections ----------------------------------------------------
    seen_pairs: dict[tuple, int] = {}
    adjacency: dict[str, set[str]] = {name: set() for name in names}
    for idx, conn in enumerate(connections):
        if not isinstance(conn, dict):
            report.errors.append(f"connection #{idx} is not an object")
            continue
        src = conn.get("source")
        dst = conn.get("dest")
        dist = conn.get("distance")
        line = conn.get("line")
        label = f"connection #{idx} ({src} - {dst})"
        valid_endpoints = True
        if src not in names:
            report.errors.append(f"{label}: source station does not exist")
            valid_endpoints = False
        if dst not in names:
            report.errors.append(f"{label}: destination station does not exist")
            valid_endpoints = False
        if src == dst:
            report.errors.append(f"{label}: self-loop connection")
        if not isinstance(dist, int) or isinstance(dist, bool) or dist <= 0:
            report.errors.append(f"{label}: distance must be a positive integer (meters)")
        elif not PLAUSIBLE_MIN_DISTANCE_M <= dist <= PLAUSIBLE_MAX_DISTANCE_M:
            report.warnings.append(f"{label}: distance {dist} m is outside the plausible range")
        if not isinstance(line, str) or not line:
            report.errors.append(f"{label}: line name missing")
        elif src in station_lines and line not in station_lines[src]:
            report.warnings.append(f"{label}: line '{line}' not listed for source station")
        elif dst in station_lines and line not in station_lines.get(dst, []):
            report.warnings.append(f"{label}: line '{line}' not listed for destination station")

        if valid_endpoints and isinstance(dist, int) and isinstance(line, str):
            key = (min(src, dst), max(src, dst), line)
            if key in seen_pairs:
                if seen_pairs[key] != dist:
                    report.errors.append(f"{label}: conflicting distances for the same connection")
                else:
                    report.warnings.append(f"{label}: duplicate connection")
            seen_pairs[key] = dist
            if src != dst:
                adjacency[src].add(dst)
                adjacency[dst].add(src)

    # ----- connectivity ---------------------------------------------------
    isolated = [name for name, nbrs in adjacency.items() if not nbrs]
    for name in isolated:
        report.warnings.append(f"station '{name}' has no connections")
    if adjacency:
        remaining = set(adjacency)
        components = 0
        while remaining:
            components += 1
            start = remaining.pop()
            queue = deque([start])
            while queue:
                node = queue.popleft()
                for nbr in adjacency[node]:
                    if nbr in remaining:
                        remaining.remove(nbr)
                        queue.append(nbr)
        if components > 1:
            report.warnings.append(f"network has {components} disconnected components")

    # ----- main-line coverage --------------------------------------------
    all_lines: dict[str, list[str]] = {}
    for name, lines in station_lines.items():
        for line in lines:
            all_lines.setdefault(_normalize_line(line), []).append(name)
    for required in REQUIRED_MAIN_LINES:
        members = all_lines.get(_normalize_line(required), [])
        if not members:
            report.warnings.append(f"main line '{required}' is not covered by the data")
        elif len(members) < 2:
            report.warnings.append(f"main line '{required}' has fewer than two stations")
    return report
