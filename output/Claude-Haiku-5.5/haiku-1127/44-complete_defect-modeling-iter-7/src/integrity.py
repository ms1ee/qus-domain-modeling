"""Data integrity checks for the subway network (triggered by --check_data)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .network import SubwayNetwork

# Main lines that must be present in the network (PRD section 4.1).
REQUIRED_LINES: tuple[str, ...] = (
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

# Representative stations of main lines used for coverage checks (missing ones are warnings).
REPRESENTATIVE_STATIONS: dict[str, list[str]] = {
    "Line 1": ["苹果园", "四惠东"],
    "Line 2": ["西直门", "建国门"],
    "Line 4": ["安河桥北"],
    "Line 5": ["天通苑北"],
    "Line 6": ["海淀五路居"],
    "Line 8": ["朱辛庄"],
    "Line 10": ["慈云寺"],
    "Line 13": ["东直门"],
}

# Plausible range of inter-station distances in meters.
MIN_DISTANCE_M = 100.0
MAX_DISTANCE_M = 5000.0


@dataclass
class IntegrityReport:
    """Outcome of an integrity check run."""

    coverage_passed: bool = True
    connectivity_passed: bool = True
    distance_passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all three checks passed."""
        return self.coverage_passed and self.connectivity_passed and self.distance_passed

    def render(self) -> str:
        """Render the report as human-readable text."""

        def status(flag: bool) -> str:
            return "PASS" if flag else "FAIL"

        lines = [
            "Data integrity check",
            f"  Station coverage : {status(self.coverage_passed)}",
            f"  Connectivity     : {status(self.connectivity_passed)}",
            f"  Distance accuracy: {status(self.distance_passed)}",
        ]
        for message in self.errors:
            lines.append(f"  ERROR: {message}")
        for message in self.warnings:
            lines.append(f"  WARNING: {message}")
        lines.append(f"Overall: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


class IntegrityChecker:
    """Validates station coverage, connection integrity and distance accuracy."""

    def __init__(self, network: "SubwayNetwork") -> None:
        self.network = network
        self.coverage_passed = False
        self.connectivity_passed = False
        self.distance_passed = False

    def run(self) -> IntegrityReport:
        """Run all checks and return the report."""
        report = IntegrityReport()
        self._check_coverage(report)
        self._check_connectivity(report)
        self._check_distances(report)
        self.coverage_passed = report.coverage_passed
        self.connectivity_passed = report.connectivity_passed
        self.distance_passed = report.distance_passed
        return report

    def _check_coverage(self, report: IntegrityReport) -> None:
        """Verify required lines exist and stations are properly registered."""
        present = set(self.network.lines())
        for line in REQUIRED_LINES:
            if line not in present:
                report.coverage_passed = False
                report.errors.append(f"required line '{line}' is missing from the network data")
        for line, stations in REPRESENTATIVE_STATIONS.items():
            for name in stations:
                if self.network.standard_name(name) is None:
                    report.warnings.append(f"representative station '{name}' of {line} not found")
        if self.network.graph.station_count == 0:
            report.coverage_passed = False
            report.errors.append("network contains no stations")
        for name, lines in self.network.graph.station_lines.items():
            if not lines:
                report.coverage_passed = False
                report.errors.append(f"station '{name}' does not belong to any line")

    def _check_connectivity(self, report: IntegrityReport) -> None:
        """Verify connection endpoints, line consistency, duplicates and graph connectivity."""
        graph = self.network.graph
        declared = self.network.declared_stations
        seen: set[tuple[int, int, str]] = set()

        for edge in graph.edges():
            src_name = self.network.station_name(edge.source)
            dst_name = self.network.station_name(edge.dest)
            for name in (src_name, dst_name):
                if name not in declared:
                    report.connectivity_passed = False
                    report.errors.append(
                        f"station '{name}' used in a connection but not declared in station data"
                    )
                if edge.line not in graph.get_station_lines(name):
                    report.connectivity_passed = False
                    report.errors.append(
                        f"connection on '{edge.line}' references station '{name}', "
                        "which is not listed as serving that line"
                    )
            key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
            if key in seen:
                report.connectivity_passed = False
                report.errors.append(
                    f"duplicate connection between '{src_name}' and '{dst_name}' on '{edge.line}'"
                )
            seen.add(key)

        vertices = graph.vertices()
        if not vertices:
            report.connectivity_passed = False
            report.errors.append("graph has no vertices")
            return
        for vertex in vertices:
            if not graph.adjacent(vertex):
                report.connectivity_passed = False
                report.errors.append(f"station '{self.network.station_name(vertex)}' is isolated")

        visited = {vertices[0]}
        queue = deque([vertices[0]])
        while queue:
            node = queue.popleft()
            for edge in graph.adjacent(node):
                nxt = edge.other(node)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        unreachable = [self.network.station_name(v) for v in vertices if v not in visited]
        if unreachable:
            report.connectivity_passed = False
            report.errors.append(
                "network is not connected; unreachable stations: " + ", ".join(unreachable)
            )

    def _check_distances(self, report: IntegrityReport) -> None:
        """Verify each inter-station distance lies in a plausible range."""
        for edge in self.network.graph.edges():
            distance = edge.distance
            if not (MIN_DISTANCE_M <= distance <= MAX_DISTANCE_M):
                report.distance_passed = False
                src_name = self.network.station_name(edge.source)
                dst_name = self.network.station_name(edge.dest)
                report.errors.append(
                    f"distance {distance} m between '{src_name}' and '{dst_name}' on "
                    f"'{edge.line}' is outside [{MIN_DISTANCE_M}, {MAX_DISTANCE_M}] m"
                )
