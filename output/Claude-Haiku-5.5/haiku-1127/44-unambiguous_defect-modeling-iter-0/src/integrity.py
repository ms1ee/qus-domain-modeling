"""
Data integrity checks for the subway network dataset.

Checks performed:
  * station coverage of the main lines
  * connection integrity (endpoints served by the line, duplicates, connectivity)
  * distance accuracy (positive and plausible distances)
"""

from collections import deque

REQUIRED_MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)
# Distances above this value (meters) between adjacent stations are suspicious.
MAX_PLAUSIBLE_DISTANCE_METERS = 10000


class DataIntegrityChecker:
    """
    Runs integrity checks on a SubwayNetwork.

    Attributes:
        last_check_result (str): Summary of the most recent check run.
        errors (list[str]): Errors found by the most recent run.
        warnings (list[str]): Warnings found by the most recent run.
    """

    def __init__(self):
        self.last_check_result = "NOT_RUN"
        self.errors = []
        self.warnings = []

    def check_station_coverage(self, network):
        """Verify that representative stations of the main lines are present."""
        present = set(network.line_names())
        for line in REQUIRED_MAIN_LINES:
            if line not in present:
                self.warnings.append(f"Main line '{line}' is missing from the dataset")
            elif not network.stations_on_line(line):
                self.warnings.append(f"Main line '{line}' has no stations")

    def check_connections(self, network):
        """Verify connection relationships between stations and lines."""
        graph = network.graph
        seen = set()
        for edge in graph.edges():
            a = network.name_of(edge.source)
            b = network.name_of(edge.dest)
            for name in (a, b):
                if edge.line not in graph.station_lines.get(name, []):
                    self.errors.append(
                        f"Station '{name}' is connected on '{edge.line}' but is not served by it")
            key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
            if key in seen:
                self.warnings.append(
                    f"Duplicate connection between '{a}' and '{b}' on '{edge.line}'")
            seen.add(key)

        nodes = graph.nodes()
        if nodes:
            visited = {nodes[0]}
            queue = deque([nodes[0]])
            while queue:
                node = queue.popleft()
                for edge in graph.adjacent_edges(node):
                    nxt = edge.other(node)
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            unreachable = [network.name_of(n) for n in nodes if n not in visited]
            if unreachable:
                self.errors.append(
                    f"{len(unreachable)} station(s) are not connected to the network: "
                    + ", ".join(unreachable[:10]))

    def check_distances(self, network):
        """Verify that connection distances are positive and plausible."""
        for edge in network.graph.edges():
            a = network.name_of(edge.source)
            b = network.name_of(edge.dest)
            if edge.distance <= 0:
                self.errors.append(f"Non-positive distance between '{a}' and '{b}': {edge.distance}")
            elif edge.distance > MAX_PLAUSIBLE_DISTANCE_METERS:
                self.warnings.append(
                    f"Unusually long distance between '{a}' and '{b}': {edge.distance} m")

    def run(self, network):
        """
        Run all checks.

        Returns:
            bool: True if no errors were found.
        """
        self.errors = []
        self.warnings = []
        self.check_station_coverage(network)
        self.check_connections(network)
        self.check_distances(network)
        passed = not self.errors
        status = "PASSED" if passed else "FAILED"
        self.last_check_result = (f"{status}: {len(self.errors)} error(s), "
                                  f"{len(self.warnings)} warning(s)")
        return passed

    def report(self):
        """Return a human-readable report of the last check run."""
        lines = [f"Data integrity check: {self.last_check_result}"]
        for error in self.errors:
            lines.append(f"  ERROR: {error}")
        for warning in self.warnings:
            lines.append(f"  WARNING: {warning}")
        return "\n".join(lines)
