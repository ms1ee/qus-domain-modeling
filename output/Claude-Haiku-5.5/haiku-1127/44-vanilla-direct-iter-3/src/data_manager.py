"""Data integrity checks for the subway network.

Checks performed:
    * station coverage (main lines and representative stations are present)
    * connection integrity (valid endpoints, no duplicates, symmetric adjacency,
      no isolated stations, network connectivity)
    * distance accuracy (positive values within plausible ranges)
"""

from collections import deque


REQUIRED_LINES = [
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
]

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Sihui East"],
    "Line 2": ["Xizhimen", "Chegongzhuang"],
    "Line 4": ["Anheqiao North"],
    "Line 5": ["Songjiazhuang"],
    "Line 6": ["Hujialou"],
    "Line 10": ["Bagou"],
    "Line 13": ["Xi'erqi"],
}

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000


class IntegrityReport:
    """Collects errors, warnings and informational messages from the checks."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    @property
    def ok(self):
        """True when no errors were found (warnings do not fail the check)."""
        return not self.errors

    def render(self):
        """Return a human readable report."""
        lines = ["Data integrity check", "=" * 40]
        lines.extend(f"[INFO]    {message}" for message in self.info)
        lines.extend(f"[WARNING] {message}" for message in self.warnings)
        lines.extend(f"[ERROR]   {message}" for message in self.errors)
        lines.append("=" * 40)
        status = "PASSED" if self.ok else "FAILED"
        lines.append(
            f"Result: {status} ({len(self.errors)} errors, {len(self.warnings)} warnings)"
        )
        return "\n".join(lines)


def check_station_coverage(network, report):
    """Verify that main lines and representative stations are present."""
    stations = network.station_names()
    report.info.append(f"Stations loaded: {len(stations)}")
    if not stations:
        report.errors.append("No stations are defined in the network")
        return

    available = set(network.lines())
    for line in REQUIRED_LINES:
        if line not in available:
            report.warnings.append(f"Main line '{line}' is not present in the data")

    for line, names in REPRESENTATIVE_STATIONS.items():
        for name in names:
            if not network.has_station(name):
                report.warnings.append(
                    f"Representative station '{name}' of {line} is not in the data"
                )
            elif line not in network.graph.get_station_lines(name):
                report.warnings.append(
                    f"Station '{name}' is not recorded as belonging to {line}"
                )

    for name in stations:
        if not network.graph.get_station_lines(name):
            report.warnings.append(f"Station '{name}' has no line information")

    for name in network.undeclared_stations:
        report.warnings.append(f"Station '{name}' is used by connections but not declared")


def check_connections(network, report):
    """Verify endpoints, duplicates, adjacency symmetry and connectivity."""
    records = network.connection_records()
    report.info.append(f"Connections loaded: {len(records)}")

    seen = set()
    for record in records:
        source, dest, line = record["source"], record["dest"], record["line"]
        if source == dest:
            report.errors.append(f"Connection on {line} links '{source}' to itself")
        for name in (source, dest):
            if not network.has_station(name):
                report.errors.append(f"Connection on {line} references unknown station '{name}'")
        key = (frozenset((source, dest)), line)
        if key in seen:
            report.errors.append(
                f"Duplicate connection between '{source}' and '{dest}' on {line}"
            )
        seen.add(key)

    graph = network.graph
    for vertex, incident in graph.adj.items():
        for edge in incident:
            other = edge.other(vertex)
            if not any(candidate is edge for candidate in graph.adj.get(other, [])):
                report.errors.append(
                    f"Adjacency is not bidirectional for station number {vertex}"
                )

    stations = network.station_names()
    isolated = [name for name in stations if not graph.neighbors(network.station_number(name))]
    for name in isolated:
        report.warnings.append(f"Station '{name}' has no connections")

    if stations:
        start = network.station_number(stations[0])
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for edge in graph.neighbors(current):
                nxt = edge.other(current)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        unreachable = [name for name in stations if network.station_number(name) not in visited]
        if unreachable:
            report.warnings.append(
                f"{len(unreachable)} station(s) are not connected to the main network: "
                + ", ".join(unreachable[:10])
            )


def check_distances(network, report):
    """Verify that every connection distance is positive and plausible."""
    for record in network.connection_records():
        distance = record["distance"]
        label = f"{record['source']} - {record['dest']} ({record['line']})"
        if not isinstance(distance, (int, float)) or distance <= 0:
            report.errors.append(f"Invalid distance {distance!r} for {label}")
        elif distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
            report.warnings.append(f"Unusual distance {distance} m for {label}")


def run_integrity_check(network) -> IntegrityReport:
    """Run all integrity checks and return the collected report."""
    report = IntegrityReport()
    check_station_coverage(network, report)
    check_connections(network, report)
    check_distances(network, report)
    return report
