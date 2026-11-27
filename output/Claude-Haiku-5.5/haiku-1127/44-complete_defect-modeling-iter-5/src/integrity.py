"""Data integrity checks for the subway network."""

from datetime import datetime

# Main lines that must be represented in the dataset.
REQUIRED_MAIN_LINES = (
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

# Plausible range for distances between adjacent stations, in meters.
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000


class IntegrityReport:
    """Result of a data integrity check.

    Attributes:
        errors: List of error messages (data is unusable for some features).
        warnings: List of warning messages (suspicious but usable data).
        checked_at: datetime of the check.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checked_at = None

    def is_valid(self):
        """Return True if no errors were found."""
        return not self.errors

    def to_text(self):
        """Render the report as human-readable text."""
        lines = [f"Data integrity check at {self.checked_at}"]
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        for message in self.errors:
            lines.append(f"ERROR: {message}")
        for message in self.warnings:
            lines.append(f"WARNING: {message}")
        lines.append(
            f"Result: {'PASSED' if self.is_valid() else 'FAILED'} "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join(lines)


class DataIntegrityChecker:
    """Validates station coverage, connection integrity and distance accuracy."""

    def __init__(self, network):
        self.network = network
        self.last_check_time = None

    def run(self):
        """Run all checks and return an ``IntegrityReport``."""
        report = IntegrityReport()
        self._check_station_coverage(report)
        self._check_stations(report)
        self._check_connections(report)
        self._check_line_connectivity(report)
        self.last_check_time = datetime.now()
        report.checked_at = self.last_check_time
        return report

    def _check_station_coverage(self, report):
        available = set(self.network.line_names())
        for line in REQUIRED_MAIN_LINES:
            if line not in available:
                report.errors.append(f"Main line '{line}' is missing from the network data")
            elif len(self.network.stations_on_line(line)) < 2:
                report.warnings.append(f"Main line '{line}' has fewer than two stations")

    def _check_stations(self, report):
        graph = self.network.graph
        for name in self.network.station_names():
            if not self.network.station_lines(name):
                report.errors.append(f"Station '{name}' does not belong to any line")
            number = self.network.station_number(name)
            if not graph.neighbors(number):
                report.warnings.append(f"Station '{name}' has no connections")

    def _check_connections(self, report):
        graph = self.network.graph
        for edge in graph.edges():
            source_name = self.network.number_to_station.get(edge.source)
            dest_name = self.network.number_to_station.get(edge.dest)
            if source_name is None or dest_name is None:
                report.errors.append(f"Connection references an unknown station: {edge!r}")
                continue
            for name in (source_name, dest_name):
                if edge.line not in self.network.station_lines(name):
                    report.errors.append(
                        f"Connection '{source_name}' - '{dest_name}' is on line "
                        f"'{edge.line}' but station '{name}' is not on that line"
                    )
            if isinstance(edge.distance, bool) or not isinstance(edge.distance, int) or edge.distance <= 0:
                report.errors.append(
                    f"Connection '{source_name}' - '{dest_name}' has invalid distance {edge.distance!r}"
                )
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= edge.distance <= MAX_PLAUSIBLE_DISTANCE_M):
                report.warnings.append(
                    f"Connection '{source_name}' - '{dest_name}' has distance "
                    f"{edge.distance} m outside the plausible range"
                )

    def _check_line_connectivity(self, report):
        graph = self.network.graph
        for line in self.network.line_names():
            numbers = {
                self.network.station_number(name)
                for name in self.network.stations_on_line(line)
            }
            if not numbers:
                continue
            start = min(numbers)
            visited = {start}
            stack = [start]
            while stack:
                node = stack.pop()
                for edge in graph.neighbors(node):
                    if edge.line != line:
                        continue
                    nxt = edge.other(node)
                    if nxt in numbers and nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
            if visited != numbers:
                report.warnings.append(
                    f"Line '{line}' is not fully connected: "
                    f"{len(numbers - visited)} station(s) unreachable along the line"
                )
