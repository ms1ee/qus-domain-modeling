"""Data integrity checks and data maintenance helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from data_loader import save_subway_data
from models import SubwayNetwork

LEVEL_ERROR = "ERROR"
LEVEL_WARNING = "WARNING"

CATEGORY_COVERAGE = "coverage"
CATEGORY_CONNECTION = "connection"
CATEGORY_DISTANCE = "distance"

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range of inter-station distances in meters.
MIN_REASONABLE_DISTANCE = 200
MAX_REASONABLE_DISTANCE = 5000


@dataclass(frozen=True)
class CheckIssue:
    """A single finding of the integrity check."""

    level: str
    category: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] ({self.category}) {self.message}"


def check_station_coverage(network: SubwayNetwork) -> list[CheckIssue]:
    """Verify that main lines and stations are represented in the data."""
    issues: list[CheckIssue] = []
    if network.station_count() == 0:
        issues.append(CheckIssue(LEVEL_ERROR, CATEGORY_COVERAGE, "No stations are loaded"))
        return issues

    available = {line.casefold(): line for line in network.lines()}
    for line in MAIN_LINES:
        official = available.get(line.casefold())
        if official is None:
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_COVERAGE,
                f"Main line '{line}' is not present in the network data"))
            continue
        count = len(network.stations_on_line(official))
        if count < 2:
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_COVERAGE,
                f"Main line '{line}' has only {count} station(s)"))

    for name in network.station_names():
        if not network.station_lines(name):
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_COVERAGE,
                f"Station '{name}' has no line assignment"))
    return issues


def _connected_components(network: SubwayNetwork) -> list[list[int]]:
    graph = network.graph
    seen: set[int] = set()
    components: list[list[int]] = []
    for start in graph.vertices():
        if start in seen:
            continue
        component = []
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            component.append(node)
            for edge in graph.neighbors(node):
                other = edge.other(node)
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        components.append(component)
    return components


def check_connections(network: SubwayNetwork) -> list[CheckIssue]:
    """Verify connection relationships between stations."""
    issues: list[CheckIssue] = []
    graph = network.graph

    for name in network.station_names():
        if not graph.neighbors(network.number_of(name)):
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_CONNECTION,
                f"Station '{name}' has no connections"))

    seen: set[tuple] = set()
    for edge in graph.edges():
        src = network.name_of(edge.source)
        dst = network.name_of(edge.dest)
        for name in (src, dst):
            if edge.line not in network.station_lines(name):
                issues.append(CheckIssue(
                    LEVEL_WARNING, CATEGORY_CONNECTION,
                    f"Connection {src}-{dst} is on line '{edge.line}', but station "
                    f"'{name}' is not registered on that line"))
        key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
        if key in seen:
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_CONNECTION,
                f"Duplicate connection {src}-{dst} on line '{edge.line}'"))
        seen.add(key)

    components = _connected_components(network)
    if len(components) > 1:
        sizes = sorted((len(c) for c in components), reverse=True)
        smallest = min(components, key=len)
        sample = [network.name_of(n) for n in smallest[:5]]
        issues.append(CheckIssue(
            LEVEL_WARNING, CATEGORY_CONNECTION,
            f"Network has {len(components)} disconnected groups (sizes {sizes[:5]}); "
            f"smallest group includes {sample}"))
    return issues


def check_distances(network: SubwayNetwork) -> list[CheckIssue]:
    """Verify that inter-station distances are positive and plausible."""
    issues: list[CheckIssue] = []
    for edge in network.graph.edges():
        src = network.name_of(edge.source)
        dst = network.name_of(edge.dest)
        if edge.distance <= 0:
            issues.append(CheckIssue(
                LEVEL_ERROR, CATEGORY_DISTANCE,
                f"Connection {src}-{dst} has non-positive distance {edge.distance}"))
        elif not MIN_REASONABLE_DISTANCE <= edge.distance <= MAX_REASONABLE_DISTANCE:
            issues.append(CheckIssue(
                LEVEL_WARNING, CATEGORY_DISTANCE,
                f"Connection {src}-{dst} on '{edge.line}' has suspicious distance "
                f"{edge.distance} m (expected {MIN_REASONABLE_DISTANCE}-"
                f"{MAX_REASONABLE_DISTANCE} m)"))
    return issues


def run_integrity_check(network: SubwayNetwork) -> list[CheckIssue]:
    """Run all integrity checks and return the combined findings."""
    return (check_station_coverage(network)
            + check_connections(network)
            + check_distances(network))


def has_errors(issues: list[CheckIssue]) -> bool:
    return any(issue.level == LEVEL_ERROR for issue in issues)


def format_check_report(issues: list[CheckIssue]) -> str:
    """Render integrity check findings as text."""
    if not issues:
        return "Data integrity check passed: no issues found."
    errors = sum(1 for issue in issues if issue.level == LEVEL_ERROR)
    warnings = len(issues) - errors
    lines = ["Data integrity check results:"]
    lines.extend(f"  {issue}" for issue in issues)
    lines.append(f"Summary: {errors} error(s), {warnings} warning(s)")
    return "\n".join(lines)


def export_network_dict(network: SubwayNetwork) -> dict:
    """Convert the network back into the subway data file structure."""
    stations = [
        {"name": name, "lines": network.station_lines(name)}
        for name in network.station_names()
    ]
    connections = []
    for edge in network.graph.edges():
        connections.append({
            "source": network.name_of(edge.source),
            "dest": network.name_of(edge.dest),
            "distance": int(edge.distance),
            "line": edge.line,
        })
    return {"stations": stations, "connections": connections}


def save_network(network: SubwayNetwork, path) -> None:
    """Persist the (possibly updated) network to a JSON data file."""
    save_subway_data(export_network_dict(network), path)
