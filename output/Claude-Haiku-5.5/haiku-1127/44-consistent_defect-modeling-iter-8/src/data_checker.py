"""Data integrity checks for the subway network (run via --check_data).

Checks performed:
    * coverage: representative stations and main lines are present;
    * connections: endpoints exist, lines are served by both endpoints,
      no self loops, reverse direction present (warning), connectivity;
    * distances: positive, plausible, and consistent between directions.
"""

from collections import deque

from models import canonical_line, line_matches

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

# Representative stations as (Chinese name, English name); either form is accepted.
REPRESENTATIVE_STATIONS = (
    ("西直门", "Xizhimen"),
    ("东直门", "Dongzhimen"),
    ("建国门", "Jianguomen"),
    ("国贸", "Guomao"),
    ("西单", "Xidan"),
    ("天安门东", "Tiananmen East"),
    ("北京站", "Beijing Railway Station"),
    ("雍和宫", "Yonghegong"),
    ("苹果园", "Pingguoyuan"),
    ("亦庄桥", "Yizhuangqiao"),
    ("良乡大学城", "Liangxiang University Town"),
    ("T3航站楼", "Terminal 3"),
)

# Plausible range for a single inter-station distance, in meters.
MIN_PLAUSIBLE_DISTANCE_M = 1
MAX_PLAUSIBLE_DISTANCE_M = 10000


class DataIntegrityChecker:
    """Runs integrity checks on a SubwayNetwork and collects messages.

    Attributes:
        coverage_valid: Result of the coverage check.
        connections_valid: Result of the connection-integrity check.
        distances_valid: Result of the distance-accuracy check.
        errors: Messages describing failed checks.
        warnings: Non-fatal observations.
    """

    def __init__(self, network):
        self.network = network
        self.coverage_valid = True
        self.connections_valid = True
        self.distances_valid = True
        self.errors = []
        self.warnings = []

    def run(self) -> bool:
        """Run all checks. Returns True if every check passed."""
        self.coverage_valid = True
        self.connections_valid = True
        self.distances_valid = True
        self.errors = []
        self.warnings = []
        self.check_coverage()
        self.check_connections()
        self.check_distances()
        return self.coverage_valid and self.connections_valid and self.distances_valid

    def check_coverage(self) -> None:
        """Verify representative stations and main lines are included."""
        names = {name.lower() for name in self.network.station_names()}
        for chinese, english in REPRESENTATIVE_STATIONS:
            if chinese.lower() not in names and english.lower() not in names:
                self.coverage_valid = False
                self.errors.append(f"Representative station missing: {chinese} ({english})")
        present = {canonical_line(line) for line in self.network.line_names()}
        for line in MAIN_LINES:
            if canonical_line(line) not in present:
                self.coverage_valid = False
                self.errors.append(f"Main line missing: {line}")

    def check_connections(self) -> None:
        """Verify connection endpoints, line membership and connectivity."""
        graph = self.network.graph
        number_to_name = self.network.number_to_name
        for edge in graph.all_edges():
            source_name = number_to_name[edge.source]
            dest_name = number_to_name[edge.dest]
            if edge.source == edge.dest:
                self.connections_valid = False
                self.errors.append(f"Self loop at station {source_name}")
            for name in (source_name, dest_name):
                served = graph.station_lines.get(name, [])
                if not any(line_matches(edge.line, line) for line in served):
                    self.connections_valid = False
                    self.errors.append(
                        f"Station {name} does not serve line {edge.line} "
                        f"used by connection to {dest_name if name == source_name else source_name}"
                    )
            if not graph.find_edges(edge.dest, edge.source):
                self.warnings.append(f"One-way connection {source_name} -> {dest_name} ({edge.line})")
        self._check_connectivity()

    def _check_connectivity(self) -> None:
        graph = self.network.graph
        neighbours = {node: set() for node in graph.nodes()}
        for edge in graph.all_edges():
            neighbours[edge.source].add(edge.dest)
            neighbours[edge.dest].add(edge.source)
        seen = set()
        components = 0
        for start in neighbours:
            if start in seen:
                continue
            components += 1
            queue = deque([start])
            seen.add(start)
            while queue:
                node = queue.popleft()
                for nxt in neighbours[node]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        if components > 1:
            self.warnings.append(f"Network is split into {components} disconnected components")

    def check_distances(self) -> None:
        """Verify distances are plausible and consistent in both directions."""
        graph = self.network.graph
        number_to_name = self.network.number_to_name
        for edge in graph.all_edges():
            if not (MIN_PLAUSIBLE_DISTANCE_M <= edge.distance <= MAX_PLAUSIBLE_DISTANCE_M):
                self.distances_valid = False
                self.errors.append(
                    f"Implausible distance {edge.distance} m between "
                    f"{number_to_name[edge.source]} and {number_to_name[edge.dest]}"
                )
            for reverse in graph.find_edges(edge.dest, edge.source):
                if reverse.line == edge.line and reverse.distance != edge.distance:
                    self.distances_valid = False
                    self.errors.append(
                        f"Inconsistent distances between {number_to_name[edge.source]} and "
                        f"{number_to_name[edge.dest]} on {edge.line}: "
                        f"{edge.distance} m vs {reverse.distance} m"
                    )

    def report(self) -> str:
        """Return a human-readable integrity report."""
        def status(flag):
            return "PASS" if flag else "FAIL"

        lines = [
            "Data integrity check",
            f"  Coverage    : {status(self.coverage_valid)}",
            f"  Connections : {status(self.connections_valid)}",
            f"  Distances   : {status(self.distances_valid)}",
        ]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {message}" for message in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {message}" for message in self.warnings)
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        return "\n".join(lines)
