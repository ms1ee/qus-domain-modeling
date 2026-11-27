"""Data integrity checks for the subway network dataset."""

from collections import deque
from dataclasses import dataclass, field

# Main lines that must be represented in the dataset.
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

# Representative stations whose absence is reported as a warning.
REPRESENTATIVE_STATIONS = (
    "Tiananmen East",
    "Dongzhimen",
    "Xizhimen",
    "Sihui",
    "Zhichunlu",
    "Wangfujing",
    "Dongdan",
    "Xierqi",
    "Sanyuanqiao",
)

# Plausible range for distances between adjacent stations (meters).
MIN_REASONABLE_DISTANCE_M = 100
MAX_REASONABLE_DISTANCE_M = 10000


@dataclass
class DataCheckReport:
    """Result of a data integrity check."""

    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def to_text(self):
        """Render the report as human-readable text."""
        lines = ["=== Data Integrity Check ==="]
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        for message in self.errors:
            lines.append(f"[ERROR] {message}")
        for message in self.warnings:
            lines.append(f"[WARNING] {message}")
        lines.append(
            f"Result: {'PASSED' if self.ok else 'FAILED'} "
            f"({len(self.errors)} errors, {len(self.warnings)} warnings)"
        )
        return "\n".join(lines)


def check_data_integrity(network):
    """Run all integrity checks on a SubwayNetwork.

    Returns:
        DataCheckReport: Errors and warnings found.
    """
    report = DataCheckReport()
    _check_coverage(network, report)
    _check_connections(network, report)
    _check_connectivity(network, report)
    return report


def _check_coverage(network, report):
    """Verify that main lines and representative stations are present."""
    known_lines = set(network.line_names())
    for line in MAIN_LINES:
        if line not in known_lines:
            report.errors.append(f"main line '{line}' is missing from the dataset")
        elif len(network.stations_on_line(line)) < 2:
            report.errors.append(f"main line '{line}' has fewer than two stations")
    for station in REPRESENTATIVE_STATIONS:
        if not network.has_station(station):
            report.warnings.append(f"representative station '{station}' is not in the dataset")


def _check_connections(network, report):
    """Verify connection endpoints, line membership and distance accuracy."""
    seen = set()
    for conn in network.connections():
        source, dest = conn["source"], conn["dest"]
        line, distance = conn["line"], conn["distance"]
        label = f"connection {source} - {dest} on '{line}'"
        endpoints_ok = True
        for endpoint in (source, dest):
            if not network.has_station(endpoint):
                report.errors.append(f"{label}: station '{endpoint}' does not exist")
                endpoints_ok = False
                continue
            if line not in network.lines_of(endpoint):
                report.errors.append(f"{label}: station '{endpoint}' is not served by this line")
        if not endpoints_ok:
            continue
        if distance <= 0:
            report.errors.append(f"{label}: distance {distance} must be positive")
        elif not (MIN_REASONABLE_DISTANCE_M <= distance <= MAX_REASONABLE_DISTANCE_M):
            report.warnings.append(f"{label}: distance {distance} m is outside the usual range")
        key = (line, frozenset((source, dest)))
        if key in seen:
            report.warnings.append(f"{label}: duplicated connection record")
        seen.add(key)


def _check_connectivity(network, report):
    """Verify the graph is connected and that no station is isolated."""
    graph = network.graph
    isolated = [network.station_name(v) for v in graph.vertices() if not graph.adj(v)]
    for name in isolated:
        report.warnings.append(f"station '{name}' has no connections")
    seen = set()
    components = 0
    for start in graph.vertices():
        if start in seen:
            continue
        components += 1
        seen.add(start)
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for edge in graph.adj(current):
                neighbour = edge.other(current)
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
    if components > 1:
        report.warnings.append(f"network consists of {components} disconnected components")
