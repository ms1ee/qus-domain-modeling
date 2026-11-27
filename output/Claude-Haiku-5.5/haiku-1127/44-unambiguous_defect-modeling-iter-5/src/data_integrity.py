"""Data integrity checks for the subway network (used by --check_data)."""

from collections import deque

from data_manager import normalize_line_name

# Representative main lines that must be present: (display name, normalized key).
REPRESENTATIVE_LINES = (
    ("Line 1", "1"),
    ("Line 2", "2"),
    ("Line 4", "4"),
    ("Line 5", "5"),
    ("Line 6", "6"),
    ("Line 8", "8"),
    ("Line 10", "10"),
    ("Line 13", "13"),
    ("Line 14", "14"),
    ("Line 15", "15"),
    ("Changping Line", "changping"),
    ("Yizhuang Line", "yizhuang"),
    ("Fangshan Line", "fangshan"),
    ("Airport Line", "airport"),
)

# Plausible range for inter-station distances in meters (used for accuracy warnings).
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


class DataIntegrityChecker:
    """Runs coverage, connection and distance checks over a DataManager's data.

    Attributes:
        last_check_passed: Result of the most recent run (False before any run).
        error_count: Number of errors found by the most recent run.
        errors: List of error messages.
        warnings: List of warning messages.
    """

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.last_check_passed = False
        self.error_count = 0
        self.errors = []
        self.warnings = []

    def run(self):
        """Execute all checks and return True if no errors were found."""
        self.errors = []
        self.warnings = []
        self._check_station_coverage()
        self._check_connection_integrity()
        self._check_distance_accuracy()
        self.error_count = len(self.errors)
        self.last_check_passed = self.error_count == 0
        return self.last_check_passed

    def _check_station_coverage(self):
        dm = self.data_manager
        if not dm.station_names():
            self.errors.append("No stations found in the dataset")
            return
        normalized = {}
        for line in dm.line_names():
            normalized.setdefault(normalize_line_name(line), []).append(line)
        for display, key in REPRESENTATIVE_LINES:
            if key not in normalized:
                self.errors.append(f"Main line '{display}' is missing from the dataset")
                continue
            count = sum(len(dm.stations_on_line(line)) for line in normalized[key])
            if count < 2:
                self.errors.append(f"Main line '{display}' has fewer than 2 stations")
        for name in dm.station_names():
            if not dm.station_lines.get(name):
                self.errors.append(f"Station '{name}' is not served by any line")

    def _check_connection_integrity(self):
        dm = self.data_manager
        graph = dm.graph
        seen = set()
        for conn in dm.connections:
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            if src not in dm.station_to_number:
                self.errors.append(f"Connection references unknown station '{src}'")
                continue
            if dst not in dm.station_to_number:
                self.errors.append(f"Connection references unknown station '{dst}'")
                continue
            if src == dst:
                self.errors.append(f"Connection from '{src}' to itself on '{line}'")
            for name in (src, dst):
                if line not in dm.station_lines.get(name, []):
                    self.errors.append(f"Station '{name}' does not list line '{line}' of its connection")
            key = (frozenset((src, dst)), line)
            if key in seen:
                self.warnings.append(f"Duplicate connection {src} - {dst} on '{line}'")
            seen.add(key)

        for name, number in dm.station_to_number.items():
            if not graph.adjacent(number):
                self.errors.append(f"Station '{name}' has no connections")

        nodes = graph.nodes()
        if nodes:
            visited = {nodes[0]}
            queue = deque([nodes[0]])
            while queue:
                node = queue.popleft()
                for edge in graph.adjacent(node):
                    other = edge.other(node)
                    if other not in visited:
                        visited.add(other)
                        queue.append(other)
            if len(visited) != len(nodes):
                self.warnings.append(
                    f"Network is not fully connected: {len(nodes) - len(visited)} station(s) unreachable from the rest"
                )

    def _check_distance_accuracy(self):
        for conn in self.data_manager.connections:
            dist = conn["distance"]
            label = f"{conn['source']} - {conn['dest']} ({conn['line']})"
            if dist <= 0:
                self.errors.append(f"Non-positive distance {dist} m for {label}")
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= dist <= MAX_PLAUSIBLE_DISTANCE_M):
                self.warnings.append(f"Distance {dist} m for {label} is outside the plausible range")

    def report(self):
        """Return a human-readable summary of the most recent check."""
        dm = self.data_manager
        status = "PASSED" if self.last_check_passed else "FAILED"
        lines = [
            f"Data integrity check: {status}",
            f"  Stations:    {len(dm.station_names())}",
            f"  Lines:       {len(dm.line_names())}",
            f"  Connections: {len(dm.connections)}",
            f"  Errors:      {self.error_count}",
            f"  Warnings:    {len(self.warnings)}",
        ]
        for msg in self.errors:
            lines.append(f"  [ERROR] {msg}")
        for msg in self.warnings:
            lines.append(f"  [WARN]  {msg}")
        return "\n".join(lines)
