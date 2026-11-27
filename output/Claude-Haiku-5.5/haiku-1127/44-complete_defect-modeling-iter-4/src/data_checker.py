"""Data integrity checks for the subway network.

Implements the ``--check_data`` validations: station coverage of the main
lines, connection integrity (connectivity, line consistency, duplicates) and
accuracy of distance data.
"""

from collections import deque
from typing import List, Set, Tuple

from network import SubwayNetwork

# Main lines whose representative presence must be verified.
REQUIRED_MAIN_LINES: Tuple[str, ...] = (
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

# Plausible range of a single inter-station distance in meters.
MIN_SEGMENT_METERS = 1
MAX_SEGMENT_METERS = 15000


class DataChecker:
    """Runs integrity checks against a ``SubwayNetwork``.

    Attributes:
        error_messages: Human-readable descriptions of every detected problem.
    """

    def __init__(self, network: SubwayNetwork) -> None:
        self.network = network
        self.error_messages: List[str] = []

    @property
    def passed(self) -> bool:
        """True when no integrity problems were found by the last run."""
        return not self.error_messages

    def run(self) -> bool:
        """Execute all checks and return True if the data passed."""
        self.error_messages = []
        self._check_station_coverage()
        self._check_connection_integrity()
        self._check_distance_accuracy()
        return self.passed

    def _error(self, message: str) -> None:
        self.error_messages.append(message)

    def _check_station_coverage(self) -> None:
        """Verify that main lines and their stations are represented."""
        if not self.network.station_names():
            self._error("No stations are defined in the network data")
            return
        lines: Set[str] = set(self.network.line_names())
        for line in REQUIRED_MAIN_LINES:
            if line not in lines:
                self._error(f"Main line '{line}' is not covered by the network data")
            elif len(self.network.stations_on_line(line)) < 2:
                self._error(f"Main line '{line}' has fewer than two stations")
        for name in self.network.station_names():
            if not self.network.lines_of_station(name):
                self._error(f"Station '{name}' does not serve any line")

    def _check_connection_integrity(self) -> None:
        """Verify station references, line consistency, duplicates and connectivity."""
        graph = self.network.graph
        seen_keys: Set[Tuple[str, str, str]] = set()
        for edge in graph.edges():
            src = self.network.name_of(edge.source)
            dst = self.network.name_of(edge.dest)
            if src == dst:
                self._error(f"Connection on line '{edge.line}' starts and ends at '{src}'")
            for name in (src, dst):
                if name not in graph.station_lines:
                    self._error(f"Connection references unknown station '{name}'")
                elif edge.line not in self.network.lines_of_station(name):
                    self._error(
                        f"Station '{name}' is connected on line '{edge.line}' "
                        f"but does not list that line"
                    )
            key = (min(src, dst), max(src, dst), edge.line)
            if key in seen_keys:
                self._error(
                    f"Duplicate connection between '{src}' and '{dst}' on line '{edge.line}'"
                )
            seen_keys.add(key)

        vertices = graph.vertices()
        if len(vertices) <= 1:
            return
        visited = {vertices[0]}
        queue = deque([vertices[0]])
        while queue:
            node = queue.popleft()
            for edge in graph.adjacent(node):
                neighbour = edge.other_endpoint(node)
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        unreachable = [self.network.name_of(v) for v in vertices if v not in visited]
        if unreachable:
            preview = ", ".join(unreachable[:10])
            self._error(
                f"Network is not connected; {len(unreachable)} station(s) unreachable: {preview}"
            )

    def _check_distance_accuracy(self) -> None:
        """Verify that every connection distance is numeric and plausible."""
        for edge in self.network.graph.edges():
            src = self.network.name_of(edge.source)
            dst = self.network.name_of(edge.dest)
            distance = edge.distance
            if not isinstance(distance, (int, float)) or isinstance(distance, bool):
                self._error(f"Distance between '{src}' and '{dst}' is not numeric")
            elif distance < MIN_SEGMENT_METERS or distance > MAX_SEGMENT_METERS:
                self._error(
                    f"Distance between '{src}' and '{dst}' on line '{edge.line}' "
                    f"is {distance} m, outside the plausible range "
                    f"[{MIN_SEGMENT_METERS}, {MAX_SEGMENT_METERS}] m"
                )
