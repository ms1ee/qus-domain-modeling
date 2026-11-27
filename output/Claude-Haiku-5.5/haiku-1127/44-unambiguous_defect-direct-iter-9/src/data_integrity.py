"""Data integrity checks for the subway dataset (triggered by ``--check_data``).

Checks performed:
* Coverage: main lines and representative hub stations are present.
* Connections: endpoints are declared stations, no self-loops, no duplicates,
  lines are consistent with station affiliations.
* Distances: positive integers within a plausible inter-station range.
* Connectivity: every station is reachable from every other station.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field

REQUIRED_LINES = (
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
REPRESENTATIVE_STATIONS = ("Xizhimen", "Dongzhimen", "Tiananmen East")
MIN_PLAUSIBLE_DISTANCE_M = 150
MAX_PLAUSIBLE_DISTANCE_M = 8000


@dataclass
class IntegrityReport:
    """Outcome of an integrity check."""

    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors

    def format(self):
        """Render the report as human-readable text."""
        out = ["Data integrity check"]
        if not self.errors and not self.warnings:
            out.append("  All checks passed.")
        for message in self.errors:
            out.append(f"  [ERROR] {message}")
        for message in self.warnings:
            out.append(f"  [WARN]  {message}")
        if self.ok:
            out.append(f"Result: PASSED ({len(self.warnings)} warning(s))")
        else:
            out.append(f"Result: FAILED ({len(self.errors)} error(s))")
        return "\n".join(out)


def check_integrity(data):
    """Run all integrity checks on the raw dataset dict.

    Returns:
        IntegrityReport: The collected errors and warnings.
    """
    report = IntegrityReport()
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list) or not isinstance(connections, list):
        report.errors.append("dataset must contain 'stations' and 'connections' lists")
        return report

    # ----- stations ----------------------------------------------------------
    declared = {}
    for station in stations:
        if not isinstance(station, dict):
            report.errors.append(f"station entry is not an object: {station!r}")
            continue
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            report.errors.append(f"station entry has invalid name: {name!r}")
            continue
        if name in declared:
            report.errors.append(f"station {name!r} is declared more than once")
            continue
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not lines:
            report.warnings.append(f"station {name!r} has no line information")
            lines = []
        declared[name] = {line for line in lines if isinstance(line, str)}

    # ----- coverage ----------------------------------------------------------
    all_lines = set()
    for lines in declared.values():
        all_lines.update(lines)
    for connection in connections:
        if isinstance(connection, dict) and isinstance(connection.get("line"), str):
            all_lines.add(connection["line"])
    for line in REQUIRED_LINES:
        if line not in all_lines:
            report.errors.append(f"main line {line!r} is missing from the network data")
    for hub in REPRESENTATIVE_STATIONS:
        if hub not in declared:
            report.errors.append(f"representative station {hub!r} is missing")

    # ----- connections -------------------------------------------------------
    seen = set()
    adjacency = defaultdict(set)
    for index, connection in enumerate(connections, start=1):
        if not isinstance(connection, dict):
            report.errors.append(f"connection #{index} is not an object")
            continue
        src = connection.get("source")
        dst = connection.get("dest")
        distance = connection.get("distance")
        line = connection.get("line")
        label = f"connection #{index} ({src!r} - {dst!r})"
        if not all(isinstance(v, str) for v in (src, dst, line)):
            report.errors.append(f"{label} has missing or invalid source/dest/line")
            continue
        undeclared = [name for name in (src, dst) if name not in declared]
        if undeclared:
            report.errors.append(
                f"{label} references undeclared station(s): {', '.join(undeclared)}"
            )
            continue
        if src == dst:
            report.errors.append(f"{label} is a self-loop")
            continue
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            report.errors.append(f"{label} has invalid distance {distance!r} (positive integer meters required)")
        elif not MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M:
            report.warnings.append(
                f"{label} distance {distance} m is outside the plausible range "
                f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
            )
        for name in (src, dst):
            if line not in declared[name]:
                report.warnings.append(
                    f"{label}: line {line!r} is not listed for station {name!r}"
                )
        key = (frozenset((src, dst)), line)
        if key in seen:
            report.errors.append(f"{label} duplicates an existing connection on {line!r}")
        seen.add(key)
        adjacency[src].add(dst)
        adjacency[dst].add(src)

    # ----- connectivity ------------------------------------------------------
    if declared:
        start = next(iter(declared))
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        unreachable = sorted(set(declared) - visited)
        if unreachable:
            sample = ", ".join(unreachable[:10])
            report.errors.append(
                f"{len(unreachable)} station(s) are not connected to the network: {sample}"
            )
    return report
