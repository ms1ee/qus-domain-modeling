"""Data integrity checks for the subway network (triggered by ``--check_data``).

Three families of checks are performed:

* Coverage: main lines are present and have enough stations.
* Connectivity: every station has connections, the network is one component,
  and station line lists agree with the connections.
* Distance accuracy: distances are positive and within plausible bounds.
"""

from collections import deque

try:
    from .network import normalize_line_name
except ImportError:  # pragma: no cover - src/ directory used directly on sys.path
    from network import normalize_line_name


# Main lines that the dataset must cover (normalised keys, see normalize_line_name).
EXPECTED_MAIN_LINES = (
    "1", "2", "4", "5", "6", "8", "10", "13", "14", "15",
    "changping", "yizhuang", "fangshan", "airport",
)
MIN_STATIONS_PER_MAIN_LINE = 2
MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 5000


def _display_line(key):
    """Return a human readable name for a normalised line key."""
    if key.isdigit():
        return f"Line {key}"
    return f"{key.capitalize()} Line"


class IntegrityReport:
    """Collected results of the integrity checks."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def passed(self):
        """True if no errors were found (warnings are allowed)."""
        return not self.errors

    def render(self):
        """Return a printable text summary."""
        lines = ["Data integrity check report", "=" * 40]
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        for message in self.errors:
            lines.append(f"[ERROR]   {message}")
        for message in self.warnings:
            lines.append(f"[WARNING] {message}")
        lines.append("-" * 40)
        lines.append("Result: PASSED" if self.passed else "Result: FAILED")
        return "\n".join(lines)


class DataIntegrityChecker:
    """Runs coverage, connectivity and distance checks on a ``SubwayNetwork``."""

    def __init__(self, network):
        self.network = network

    def run(self):
        """Run all checks and return an ``IntegrityReport``."""
        report = IntegrityReport()
        self.check_coverage(report)
        self.check_connectivity(report)
        self.check_distances(report)
        return report

    def check_coverage(self, report):
        """Verify that main lines and their representative stations are present."""
        if not self.network.stations():
            report.errors.append("The network contains no stations")
            return
        present = {normalize_line_name(line): line for line in self.network.line_names}
        for key in EXPECTED_MAIN_LINES:
            display = _display_line(key)
            if key not in present:
                report.errors.append(f"Main line '{display}' is missing from the dataset")
                continue
            count = len(self.network.line_stations.get(present[key], []))
            if count < MIN_STATIONS_PER_MAIN_LINE:
                report.errors.append(
                    f"Main line '{display}' has only {count} station(s)"
                )
        for name in self.network.stations():
            if not self.network.graph.get_station_lines(name):
                report.warnings.append(f"Station '{name}' is not assigned to any line")

    def check_connectivity(self, report):
        """Verify adjacency consistency and overall network connectivity."""
        graph = self.network.graph
        for number in graph.vertices():
            name = self.network.name_of(number)
            if not graph.adjacent(number):
                report.errors.append(f"Station '{name}' has no connections")
        for edge in graph.edges():
            for number in (edge.source, edge.dest):
                name = self.network.name_of(number)
                if edge.line not in graph.get_station_lines(name):
                    report.errors.append(
                        f"Connection on {edge.line} touches '{name}', which is not listed on that line"
                    )
        components = self._components()
        if len(components) > 1:
            sizes = ", ".join(str(size) for size in components)
            report.errors.append(
                f"Network is split into {len(components)} disconnected groups (sizes: {sizes})"
            )

    def _components(self):
        """Return the sizes of the connected components of the graph."""
        graph = self.network.graph
        seen = set()
        sizes = []
        for start in graph.vertices():
            if start in seen:
                continue
            seen.add(start)
            queue = deque([start])
            size = 0
            while queue:
                current = queue.popleft()
                size += 1
                for other, _edge in graph.neighbors(current):
                    if other not in seen:
                        seen.add(other)
                        queue.append(other)
            sizes.append(size)
        return sizes

    def check_distances(self, report):
        """Verify that distances are positive and plausible."""
        for edge in self.network.graph.edges():
            source = self.network.name_of(edge.source)
            dest = self.network.name_of(edge.dest)
            label = f"{source} - {dest} ({edge.line})"
            if edge.distance <= 0:
                report.errors.append(f"Non-positive distance {edge.distance} m on {label}")
            elif edge.distance < MIN_PLAUSIBLE_DISTANCE_M:
                report.warnings.append(f"Unusually short distance {edge.distance} m on {label}")
            elif edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
                report.warnings.append(f"Unusually long distance {edge.distance} m on {label}")
