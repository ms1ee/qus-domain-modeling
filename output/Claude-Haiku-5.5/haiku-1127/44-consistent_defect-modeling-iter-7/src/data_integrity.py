"""
Data integrity checks for the subway network graph.

Checks performed:
    - Coverage: every main line has at least one station in the network.
    - Connectivity: edges reference known stations, no self-loops, no isolated
      stations, and the network is connected (ignoring edge direction).
    - Distance accuracy: distances are positive, within a plausible range, and
      not duplicated with conflicting values.
"""

from collections import deque


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

MIN_SEGMENT_DISTANCE_M = 1
MAX_SEGMENT_DISTANCE_M = 10000


class DataIntegrityChecker:
    """Runs the data integrity checks against a Graph.

    Attributes:
        coverage_passed: Result of the coverage check.
        connectivity_passed: Result of the connectivity check.
        distance_accuracy_passed: Result of the distance accuracy check.
    """

    def __init__(self, graph, number_to_name=None):
        self.graph = graph
        self.number_to_name = number_to_name or {}
        self.coverage_passed = False
        self.connectivity_passed = False
        self.distance_accuracy_passed = False
        self.messages = []
        self.warnings = []

    @staticmethod
    def _normalize(text):
        return " ".join(str(text).split()).lower()

    def _name(self, number):
        return self.number_to_name.get(number, str(number))

    def check_coverage(self):
        """Verify that representative stations of all main lines are present."""
        present = set()
        for lines in self.graph.station_lines.values():
            for line in lines:
                present.add(self._normalize(line))
        missing = [line for line in REQUIRED_MAIN_LINES if self._normalize(line) not in present]
        self.coverage_passed = bool(self.graph.station_lines) and not missing
        if not self.graph.station_lines:
            self.messages.append("Coverage: network contains no stations")
        elif missing:
            self.messages.append("Coverage: missing main lines: " + ", ".join(missing))
        else:
            self.messages.append("Coverage: all main lines are represented")
        return self.coverage_passed

    def check_connectivity(self):
        """Verify edge references, self-loops, isolated stations and connectedness."""
        problems = []
        nodes = set(self.graph.nodes())
        edges = list(self.graph.edges())
        incoming = set()
        edge_pairs = set()
        for edge in edges:
            if edge.source not in nodes or edge.dest not in nodes:
                problems.append(f"edge {edge} references an unknown station")
            if edge.source == edge.dest:
                problems.append(f"self-loop at {self._name(edge.source)}")
            incoming.add(edge.dest)
            edge_pairs.add((edge.source, edge.dest))

        for edge in edges:
            if (edge.dest, edge.source) not in edge_pairs:
                self.warnings.append(
                    f"one-way connection only: {self._name(edge.source)} -> {self._name(edge.dest)}"
                )

        for node in nodes:
            if not self.graph.neighbors(node) and node not in incoming:
                problems.append(f"isolated station {self._name(node)}")

        components = self._count_components(nodes, edges)
        if components > 1:
            problems.append(f"network is split into {components} disconnected components")

        self.connectivity_passed = not problems
        if problems:
            self.messages.extend("Connectivity: " + p for p in problems)
        else:
            self.messages.append("Connectivity: all connections are consistent")
        return self.connectivity_passed

    def _count_components(self, nodes, edges):
        """Count weakly connected components using BFS."""
        undirected = {node: set() for node in nodes}
        for edge in edges:
            if edge.source in undirected and edge.dest in undirected:
                undirected[edge.source].add(edge.dest)
                undirected[edge.dest].add(edge.source)
        seen = set()
        components = 0
        for start in nodes:
            if start in seen:
                continue
            components += 1
            queue = deque([start])
            seen.add(start)
            while queue:
                current = queue.popleft()
                for nxt in undirected[current]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        return components

    def check_distance_accuracy(self):
        """Verify distances are plausible and not conflicting."""
        problems = []
        recorded = {}
        for edge in self.graph.edges():
            distance = edge.distance
            if not isinstance(distance, (int, float)) or not (
                MIN_SEGMENT_DISTANCE_M <= distance <= MAX_SEGMENT_DISTANCE_M
            ):
                problems.append(
                    f"implausible distance {distance} m between "
                    f"{self._name(edge.source)} and {self._name(edge.dest)}"
                )
            key = (edge.source, edge.dest, edge.line)
            if key in recorded and recorded[key] != distance:
                problems.append(
                    f"conflicting distances for {self._name(edge.source)} -> {self._name(edge.dest)}"
                )
            recorded[key] = distance

        self.distance_accuracy_passed = not problems
        if problems:
            self.messages.extend("Distance: " + p for p in problems)
        else:
            self.messages.append("Distance: all distances are plausible")
        return self.distance_accuracy_passed

    def run(self):
        """Run all checks.

        Returns:
            bool: True if every check passed.
        """
        self.messages = []
        self.warnings = []
        self.check_coverage()
        self.check_connectivity()
        self.check_distance_accuracy()
        return self.coverage_passed and self.connectivity_passed and self.distance_accuracy_passed

    def report_lines(self):
        """Return human-readable result lines."""
        lines = list(self.messages)
        lines.extend("Warning: " + w for w in self.warnings)
        lines.append(
            "Overall: " + ("PASSED" if self.coverage_passed and self.connectivity_passed
                           and self.distance_accuracy_passed else "FAILED")
        )
        return lines
