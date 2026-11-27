"""
Data integrity checks for the subway network.

Checks performed:
  * Station coverage: representative stations of main lines exist.
  * Connection integrity: endpoints exist, lines are consistent, edges are
    stored in both adjacency lists, no duplicate edges, network connectivity.
  * Distance accuracy: distances are finite, positive and plausible.
"""

import math

# Representative stations for main lines used by the coverage check.
MAIN_LINE_REPRESENTATIVES = {
    "Line 1": ["苹果园", "西单", "四惠东"],
    "Line 2": ["西直门", "建国门", "东直门"],
    "Line 4": ["安河桥北", "北京南站"],
    "Line 5": ["天通苑北", "宋家庄"],
    "Line 6": ["海淀五路居", "草房"],
    "Line 8": ["朱辛庄", "鼓楼大街"],
    "Line 10": ["巴沟", "宋家庄"],
    "Line 13": ["西直门", "东直门"],
    "Line 14": ["张郭庄", "望京南"],
    "Line 15": ["望京东"],
}

# Plausible inter-station distance range in meters.
MIN_DISTANCE_M = 50.0
MAX_DISTANCE_M = 15000.0


class DataIntegrityChecker:
    """Runs integrity checks against a SubwayNetwork.

    Attributes:
        main_line_representatives: dict line name -> representative station names.
        distance_tolerance: (min, max) plausible distance range in meters.
        errors: list of error messages from the last run.
        warnings: list of warning messages from the last run.
    """

    def __init__(self, network, representatives=None, min_distance_m=MIN_DISTANCE_M,
                 max_distance_m=MAX_DISTANCE_M):
        self.network = network
        self.main_line_representatives = (
            dict(representatives) if representatives is not None else dict(MAIN_LINE_REPRESENTATIVES)
        )
        self.distance_tolerance = (float(min_distance_m), float(max_distance_m))
        self.errors = []
        self.warnings = []

    def run(self):
        """Execute all checks. Returns True when no errors were found."""
        self.errors = []
        self.warnings = []
        self.check_station_coverage()
        self.check_connection_integrity()
        self.check_distance_accuracy()
        return not self.errors

    def check_station_coverage(self):
        """Verify that representative stations of main lines are present."""
        known_lines = set(self.network.line_names())
        for line, stations in self.main_line_representatives.items():
            if line not in known_lines:
                self.errors.append(f"Main line '{line}' is missing from the network")
                continue
            for station in stations:
                if self.network.resolve_station(station) is None:
                    self.errors.append(f"Representative station '{station}' of {line} is missing")

    def check_connection_integrity(self):
        """Verify endpoints, line consistency, symmetry, duplicates and connectivity."""
        graph = self.network.graph
        if graph.station_count() == 0:
            self.errors.append("Network contains no stations")
            return

        for number in graph.number_to_station:
            name = graph.name_of(number)
            if not graph.station_lines.get(name):
                self.warnings.append(f"Station '{name}' has no line assignment")
            if not graph.adjacent(number):
                self.errors.append(f"Station '{name}' has no connections")

        seen = set()
        for edge in graph.edges:
            src = graph.name_of(edge.source)
            dst = graph.name_of(edge.dest)
            for name in (src, dst):
                if edge.line not in graph.station_lines.get(name, []):
                    self.errors.append(
                        f"Connection {src}-{dst} uses line '{edge.line}' not served by '{name}'"
                    )
            if not any(e is edge for e in graph.adjacent(edge.dest)):
                self.errors.append(f"Connection {src}-{dst} is not bidirectional")
            key = (min(src, dst), max(src, dst), edge.line)
            if key in seen:
                self.warnings.append(f"Duplicate connection {src}-{dst} on {edge.line}")
            seen.add(key)

        numbers = list(graph.number_to_station)
        reached = {numbers[0]}
        stack = [numbers[0]]
        while stack:
            current = stack.pop()
            for edge in graph.adjacent(current):
                other = edge.other(current)
                if other not in reached:
                    reached.add(other)
                    stack.append(other)
        if len(reached) != len(numbers):
            self.errors.append(
                f"{len(numbers) - len(reached)} station(s) are not reachable from "
                f"'{graph.name_of(numbers[0])}'"
            )

    def check_distance_accuracy(self):
        """Verify that every distance is finite, positive and within the plausible range."""
        graph = self.network.graph
        low, high = self.distance_tolerance
        for edge in graph.edges:
            src = graph.name_of(edge.source)
            dst = graph.name_of(edge.dest)
            value = edge.weight
            if math.isnan(value) or math.isinf(value) or value <= 0:
                self.errors.append(f"Invalid distance {value} between {src} and {dst}")
            elif value < low or value > high:
                self.warnings.append(
                    f"Suspicious distance {value:.0f} m between {src} and {dst} "
                    f"(expected {low:.0f}-{high:.0f} m)"
                )

    def report_lines(self):
        """Return human-readable lines summarizing the last run."""
        lines = []
        if not self.errors and not self.warnings:
            lines.append("Data integrity check passed: no issues found.")
        for message in self.errors:
            lines.append(f"[ERROR] {message}")
        for message in self.warnings:
            lines.append(f"[WARNING] {message}")
        if self.errors:
            lines.append(f"Data integrity check FAILED with {len(self.errors)} error(s).")
        elif self.warnings:
            lines.append(f"Data integrity check passed with {len(self.warnings)} warning(s).")
        return lines
