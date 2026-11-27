"""Data integrity checks for the subway network (triggered by --check_data)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from network import SubwayNetwork

# Main lines that must be present in the dataset.
MAIN_LINES: Tuple[str, ...] = (
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

# Plausible range of distances between adjacent stations (meters).
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000


@dataclass
class IntegrityReport:
    """Outcome of a data integrity check."""

    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)

    def format_text(self) -> str:
        lines = [
            f"Data integrity check: {'PASSED' if self.passed else 'FAILED'}",
            f"Checked at: {self.checked_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Errors: {len(self.errors)}",
        ]
        for message in self.errors:
            lines.append(f"  [ERROR] {message}")
        lines.append(f"Warnings: {len(self.warnings)}")
        for message in self.warnings:
            lines.append(f"  [WARN]  {message}")
        return "\n".join(lines)


def _count_components(adjacency: Dict[str, Set[str]]) -> int:
    """Count connected components of an undirected adjacency mapping."""
    seen: Set[str] = set()
    components = 0
    for start in adjacency:
        if start in seen:
            continue
        components += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            for neighbour in adjacency.get(node, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
    return components


class DataIntegrityChecker:
    """Checks coverage, connection integrity and distance accuracy of a network."""

    def __init__(self, network: SubwayNetwork) -> None:
        self.network = network
        self.last_check_time: Optional[datetime] = None
        self.passed: Optional[bool] = None

    def run(self) -> IntegrityReport:
        errors: List[str] = []
        warnings: List[str] = []
        self._check_station_coverage(errors, warnings)
        self._check_connection_integrity(errors, warnings)
        self._check_distance_accuracy(errors, warnings)

        report = IntegrityReport(passed=not errors, errors=errors, warnings=warnings)
        self.last_check_time = report.checked_at
        self.passed = report.passed
        return report

    def _check_station_coverage(self, errors: List[str], warnings: List[str]) -> None:
        available = {name.casefold(): name for name in self.network.line_names()}
        for main in MAIN_LINES:
            actual = available.get(main.casefold())
            if actual is None:
                errors.append(f"main line '{main}' is missing from the network")
                continue
            count = len(self.network.stations_on_line(actual))
            if count < 2:
                errors.append(f"main line '{main}' has too few stations ({count})")
        for name in self.network.station_names():
            if not self.network.lines_of(name):
                errors.append(f"station '{name}' does not belong to any line")

    def _check_connection_integrity(self, errors: List[str], warnings: List[str]) -> None:
        for name in sorted(self.network.unlisted_stations):
            warnings.append(f"station '{name}' appears in connections but not in the station list")

        degree: Dict[str, int] = {name: 0 for name in self.network.station_names()}
        per_line: Dict[str, Dict[str, Set[str]]] = {}
        seen_pairs: Set[Tuple[frozenset, str]] = set()

        for conn in self.network.connections():
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            if src == dst:
                errors.append(f"connection on '{line}' links station '{src}' to itself")
                continue
            for endpoint in (src, dst):
                if line not in self.network.lines_of(endpoint):
                    warnings.append(
                        f"connection {src} - {dst} uses line '{line}' which '{endpoint}' does not serve"
                    )
            key = (frozenset((src, dst)), line)
            if key in seen_pairs:
                warnings.append(f"duplicate connection {src} - {dst} on line '{line}'")
            seen_pairs.add(key)

            degree[src] = degree.get(src, 0) + 1
            degree[dst] = degree.get(dst, 0) + 1
            adjacency = per_line.setdefault(line, {})
            adjacency.setdefault(src, set()).add(dst)
            adjacency.setdefault(dst, set()).add(src)

        for name, count in degree.items():
            if count == 0:
                errors.append(f"station '{name}' has no connections")

        for line, adjacency in sorted(per_line.items()):
            components = _count_components(adjacency)
            if components > 1:
                errors.append(f"line '{line}' is disconnected ({components} separate segments)")

    def _check_distance_accuracy(self, errors: List[str], warnings: List[str]) -> None:
        for conn in self.network.connections():
            distance = conn["distance"]
            label = f"{conn['source']} - {conn['dest']} ({conn['line']})"
            if not isinstance(distance, (int, float)) or distance <= 0:
                errors.append(f"connection {label} has a non-positive distance: {distance!r}")
            elif distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
                warnings.append(f"connection {label} distance {distance} m is outside the plausible range")
