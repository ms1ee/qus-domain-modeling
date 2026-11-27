"""Data integrity checks for the subway network.

The checks cover station coverage of the main lines, the integrity of the
connection relationships, and the plausibility of distance data. Results are
collected in an ``IntegrityReport``, which is printed by the ``--check_data``
command-line option.
"""

from collections import deque

# Main lines that the dataset is expected to cover (PRD section 4.1).
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations per main line, used for coverage checks.
# Adjust these names if the dataset naming convention differs.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "天安门西", "国贸"],
    "Line 2": ["西直门", "建国门"],
    "Line 4": ["圆明园", "北京南站"],
    "Line 5": ["宋家庄", "天通苑北"],
    "Line 6": ["海淀五路居", "草房"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["国贸"],
    "Line 13": ["西直门", "立水桥"],
}

# Distances outside this range (meters) are reported as suspicious.
MIN_PLAUSIBLE_DISTANCE = 50
MAX_PLAUSIBLE_DISTANCE = 10000


class IntegrityReport:
    """Collection of errors and warnings produced by integrity checks."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def is_ok(self):
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def format(self):
        """Return a human-readable summary of the report."""
        lines = ["Data integrity check report", "=" * 40]
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        for error in self.errors:
            lines.append(f"[ERROR] {error}")
        for warning in self.warnings:
            lines.append(f"[WARNING] {warning}")
        lines.append("=" * 40)
        lines.append(
            f"Result: {'PASSED' if self.is_ok else 'FAILED'} "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join(lines)


def check_data_integrity(network):
    """Run all integrity checks on a ``SubwayNetwork``.

    Returns:
        IntegrityReport: The collected findings.
    """
    report = IntegrityReport()
    _check_coverage(network, report)
    _check_stations(network, report)
    _check_connections(network, report)
    _check_connectivity(network, report)
    _check_lines(network, report)
    return report


def _check_coverage(network, report):
    """Verify that main lines and their representative stations are present."""
    known_lines = set(network.line_names())
    for line in MAIN_LINES:
        if line not in known_lines:
            report.warnings.append(f"Main line '{line}' is not present in the dataset")
    for line, stations in REPRESENTATIVE_STATIONS.items():
        for station in stations:
            if not network.has_station(station):
                report.warnings.append(
                    f"Representative station '{station}' of {line} is missing"
                )


def _check_stations(network, report):
    """Verify station records: each station needs lines and at least one connection."""
    for name in network.station_names():
        number = network.get_number(name)
        if not network.lines_of(name):
            report.errors.append(f"Station '{name}' is not assigned to any line")
        if len(network.graph.adj(number)) == 0:
            report.warnings.append(f"Station '{name}' has no connections (isolated)")


def _check_connections(network, report):
    """Verify connection records: endpoints, distances, duplicates and symmetry."""
    seen = set()
    for edge in network.graph.edges():
        src_name = network.name_of(edge.source)
        dst_name = network.name_of(edge.dest)
        label = f"{src_name} - {dst_name} ({edge.line})"

        if edge.source == edge.dest:
            report.errors.append(f"Self-loop connection at '{src_name}' ({edge.line})")

        distance = edge.distance
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            report.errors.append(f"Invalid distance {distance!r} for {label}")
        elif not MIN_PLAUSIBLE_DISTANCE <= distance <= MAX_PLAUSIBLE_DISTANCE:
            report.warnings.append(f"Suspicious distance {distance} m for {label}")

        for name in (src_name, dst_name):
            if edge.line not in network.lines_of(name):
                report.warnings.append(
                    f"Station '{name}' does not list line '{edge.line}' of connection {label}"
                )

        key = (min(src_name, dst_name), max(src_name, dst_name), edge.line)
        if key in seen:
            report.errors.append(f"Duplicate connection {label}")
        seen.add(key)

        if not (any(e is edge for e in network.graph.adj(edge.source))
                and any(e is edge for e in network.graph.adj(edge.dest))):
            report.errors.append(f"Connection {label} is not bidirectionally registered")


def _connected_components(graph):
    """Return the connected components of the graph as lists of vertices."""
    seen = set()
    components = []
    for start in graph.vertices():
        if start in seen:
            continue
        component = []
        queue = deque([start])
        seen.add(start)
        while queue:
            vertex = queue.popleft()
            component.append(vertex)
            for edge in graph.adj(vertex):
                other = edge.other(vertex)
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        components.append(component)
    return components


def _check_connectivity(network, report):
    """Verify that the network forms a single connected component."""
    components = [c for c in _connected_components(network.graph) if len(c) > 1]
    if len(components) > 1:
        sizes = sorted((len(c) for c in components), reverse=True)
        report.warnings.append(
            f"Network is split into {len(components)} disconnected groups (sizes {sizes})"
        )


def _check_lines(network, report):
    """Verify each line has stations and a consistent number of connections."""
    for line in network.line_names():
        stations = network.line_stations(line)
        if not stations:
            report.warnings.append(f"Line '{line}' has no stations or connections")
            continue
        edge_count = sum(1 for e in network.graph.edges() if e.line == line)
        if edge_count != len(stations) - 1:
            report.warnings.append(
                f"Line '{line}' has {len(stations)} stations but {edge_count} connections; "
                "the line may be disconnected or non-linear"
            )
