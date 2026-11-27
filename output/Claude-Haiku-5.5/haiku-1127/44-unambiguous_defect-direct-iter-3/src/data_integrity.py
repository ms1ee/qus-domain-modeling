"""Data integrity checks for the subway network (used by ``--check_data``)."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Sequence

from network import SubwayNetwork

REQUIRED_MAIN_LINES: tuple = (
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
MAX_REASONABLE_DISTANCE_M: int = 6000
MIN_STATIONS_PER_LINE: int = 2


class IntegrityReport:
    """Collects errors, warnings and informational messages."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.info.append(message)

    def format(self) -> str:
        out = ["Data integrity check", "=" * 40]
        out.append(f"Errors: {len(self.errors)}, warnings: {len(self.warnings)}")
        for title, items in (
            ("ERRORS", self.errors),
            ("WARNINGS", self.warnings),
            ("INFO", self.info),
        ):
            if items:
                out.append(f"{title}:")
                out.extend(f"  - {item}" for item in items)
        out.append("Result: PASSED" if self.ok else "Result: FAILED")
        return "\n".join(out)


def check_network(
    network: SubwayNetwork,
    required_lines: Sequence[str] = REQUIRED_MAIN_LINES,
    max_distance: int = MAX_REASONABLE_DISTANCE_M,
) -> IntegrityReport:
    """Run all integrity checks and return the resulting report."""
    report = IntegrityReport()
    for issue in network.issues:
        report.add_warning(issue)

    _check_coverage(network, required_lines, report)
    _check_stations(network, report)
    _check_connections(network, report)
    _check_line_continuity(network, report)
    _check_distances(network, max_distance, report)

    report.add_info(
        f"stations={len(network.station_to_number)}, "
        f"connections={network.graph.num_edges}, "
        f"lines={len(network.line_names())}"
    )
    transfer_stations = sum(
        1 for name in network.station_to_number if len(network.lines_of(name)) >= 2
    )
    report.add_info(f"interchange (multi-line) stations: {transfer_stations}")
    return report


def _check_coverage(
    network: SubwayNetwork, required_lines: Sequence[str], report: IntegrityReport
) -> None:
    present = set(network.connection_line_names())
    for line in required_lines:
        if line not in present:
            report.add_error(f"required main line '{line}' has no connections in the data")
            continue
        count = len(network.stations_on_line(line))
        if count < MIN_STATIONS_PER_LINE:
            report.add_error(
                f"line '{line}' covers only {count} station(s); expected at least "
                f"{MIN_STATIONS_PER_LINE}"
            )


def _check_stations(network: SubwayNetwork, report: IntegrityReport) -> None:
    for name, number in network.station_to_number.items():
        if not network.lines_of(name):
            report.add_warning(f"station '{name}' has no line assignment")
        if not network.graph.adjacent(number):
            report.add_warning(f"station '{name}' has no connections")


def _check_connections(network: SubwayNetwork, report: IntegrityReport) -> None:
    for edge in network.graph.edges():
        source = network.name_of(edge.source)
        dest = network.name_of(edge.dest)
        if not isinstance(edge.distance, int) or edge.distance <= 0:
            report.add_error(
                f"connection {source} - {dest} on '{edge.line}' has invalid distance"
            )
        for name in (source, dest):
            if edge.line not in network.lines_of(name):
                report.add_warning(
                    f"station '{name}' is connected on '{edge.line}' but its line "
                    f"list does not include it"
                )


def _check_line_continuity(network: SubwayNetwork, report: IntegrityReport) -> None:
    adjacency: Dict[str, Dict[int, List[int]]] = {}
    for edge in network.graph.edges():
        per_line = adjacency.setdefault(edge.line, {})
        per_line.setdefault(edge.source, []).append(edge.dest)
        per_line.setdefault(edge.dest, []).append(edge.source)

    for line, graph in adjacency.items():
        seen = set()
        components = 0
        for start in graph:
            if start in seen:
                continue
            components += 1
            seen.add(start)
            queue = deque([start])
            while queue:
                current = queue.popleft()
                for nxt in graph[current]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        if components > 1:
            report.add_warning(
                f"line '{line}' is split into {components} disconnected segments"
            )


def _check_distances(
    network: SubwayNetwork, max_distance: int, report: IntegrityReport
) -> None:
    for edge in network.graph.edges():
        if edge.distance > max_distance:
            report.add_warning(
                f"distance {network.name_of(edge.source)} - {network.name_of(edge.dest)} "
                f"on '{edge.line}' is {edge.distance} m (above {max_distance} m); "
                f"please verify"
            )
