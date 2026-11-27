"""Data integrity checks for the subway network (triggered by --check_data)."""

from dataclasses import dataclass, field

from subway_network import build_network

# Main lines expected to be covered by the data set.
REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
MIN_STATIONS_PER_LINE = 2
# Plausible range for distances between adjacent stations (meters).
MIN_REASONABLE_DISTANCE_M = 100
MAX_REASONABLE_DISTANCE_M = 10000


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""

    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    summary: list = field(default_factory=list)

    @property
    def ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def format_report(self):
        """Return a human-readable text report."""
        out = ["Data integrity check"]
        out.extend(self.summary)
        for message in self.errors:
            out.append(f"  [ERROR] {message}")
        for message in self.warnings:
            out.append(f"  [WARNING] {message}")
        if not self.errors and not self.warnings:
            out.append("Result: PASSED")
        elif self.errors:
            out.append(f"Result: FAILED ({len(self.errors)} error(s), {len(self.warnings)} warning(s))")
        else:
            out.append(f"Result: PASSED with {len(self.warnings)} warning(s)")
        return "\n".join(out)


def _check_station_coverage(network, report):
    """Verify that representative main lines are present and have stations."""
    if not network.station_names():
        report.errors.append("No stations found in the data set")
        return
    present = set(network.line_names())
    for line in REQUIRED_MAIN_LINES:
        if line not in present:
            report.warnings.append(f"Main line '{line}' is not covered by the data set")
    for line in sorted(present):
        count = len(network.stations_on_line(line))
        if count < MIN_STATIONS_PER_LINE:
            report.warnings.append(f"Line '{line}' has only {count} station(s)")


def _check_connections(stations, connections, network, report):
    """Verify connection relationships between declared stations."""
    declared = {station.get("name") for station in stations}
    seen_pairs = set()
    for index, conn in enumerate(connections):
        source = conn.get("source")
        dest = conn.get("dest")
        line = conn.get("line")
        if source not in declared:
            report.errors.append(f"Connection {index}: station '{source}' is not declared")
        if dest not in declared:
            report.errors.append(f"Connection {index}: station '{dest}' is not declared")
        if source == dest:
            report.errors.append(f"Connection {index}: station '{source}' connects to itself")
        key = (frozenset((source, dest)), line)
        if key in seen_pairs:
            report.warnings.append(f"Duplicate connection {source} - {dest} on '{line}'")
        seen_pairs.add(key)

    isolated = [name for name in network.station_names()
                if network.graph.degree(network.number_of(name)) == 0]
    for name in isolated:
        report.warnings.append(f"Station '{name}' has no connections")

    connected_nodes = [v for v in network.graph.nodes() if network.graph.degree(v) > 0]
    if connected_nodes:
        seen = set()
        components = 0
        for start in connected_nodes:
            if start in seen:
                continue
            components += 1
            seen.add(start)
            stack = [start]
            while stack:
                vertex = stack.pop()
                for edge in network.graph.adjacent(vertex):
                    other = edge.other(vertex)
                    if other not in seen:
                        seen.add(other)
                        stack.append(other)
        if components > 1:
            report.warnings.append(f"Network is split into {components} disconnected components")


def _check_distances(connections, report):
    """Verify that distance data is numeric, positive and plausible."""
    for index, conn in enumerate(connections):
        distance = conn.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            report.errors.append(f"Connection {index}: distance is not numeric")
            continue
        if distance <= 0:
            report.errors.append(f"Connection {index}: distance {distance} must be positive")
        elif not (MIN_REASONABLE_DISTANCE_M <= distance <= MAX_REASONABLE_DISTANCE_M):
            report.warnings.append(
                f"Connection {index} ({conn.get('source')} - {conn.get('dest')}): "
                f"distance {distance} m is outside the plausible range"
            )


def check_data_integrity(data, network=None):
    """Run all integrity checks and return an IntegrityReport."""
    report = IntegrityReport()
    try:
        if network is None:
            network = build_network(data)
    except (KeyError, TypeError, ValueError) as exc:
        report.errors.append(f"Network cannot be built from the data: {exc}")
        return report

    stations = data.get("stations", [])
    connections = data.get("connections", [])
    report.summary = [
        f"Stations: {len(network.station_names())}",
        f"Lines: {len(network.line_names())}",
        f"Connections: {len(connections)}",
    ]
    _check_station_coverage(network, report)
    _check_connections(stations, connections, network, report)
    _check_distances(connections, report)
    return report
