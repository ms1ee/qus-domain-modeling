"""Data integrity checks for the subway network.

Checks performed:
  * Coverage: representative main lines exist and have stations and connections.
  * Connection integrity: endpoints are declared, lines are served by both
    endpoints, no self-loops or duplicates.
  * Distance accuracy: distances are positive and within a plausible range.
  * Connectivity: every station is reachable from every other station.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List

from network import SubwayNetwork

# Main lines that must be represented in the dataset.
REQUIRED_MAIN_LINES = [
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
]

# Plausible range for distances between adjacent stations (meters).
MIN_DISTANCE_M = 50
MAX_DISTANCE_M = 10000


@dataclass
class IntegrityCheckResult:
    """Outcome of an integrity check.

    Attributes:
        passed: True if no issues were found.
        issues: Human-readable descriptions of every issue found.
    """

    passed: bool
    issues: List[str] = field(default_factory=list)


def _is_number(value) -> bool:
    """Return True for int/float values that are not booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_coverage(network: SubwayNetwork, issues: List[str]) -> None:
    """Verify main-line coverage and station line affiliations."""
    line_stations = defaultdict(set)
    for name, lines in network.stations.items():
        for line in lines:
            line_stations[line].add(name)
    line_connections = Counter(connection["line"] for connection in network.connections)

    for line in REQUIRED_MAIN_LINES:
        if not line_stations.get(line):
            issues.append(f"Main line '{line}' has no stations in the dataset")
        elif not line_connections.get(line):
            issues.append(f"Main line '{line}' has no connection data")

    for name, lines in network.stations.items():
        if not lines:
            issues.append(f"Station '{name}' has no line affiliation")


def _check_connections(network: SubwayNetwork, issues: List[str]) -> None:
    """Verify connection relationships and distance accuracy."""
    seen = set()
    for index, connection in enumerate(network.connections):
        source = connection["source"]
        dest = connection["dest"]
        line = connection["line"]
        distance = connection["distance"]
        label = f"connection #{index} ({source} - {dest}, {line})"

        if source == dest:
            issues.append(f"{label}: station connects to itself")
            continue

        for endpoint in (source, dest):
            if endpoint in network.undeclared_stations:
                issues.append(f"{label}: station '{endpoint}' is not declared in station data")
            elif line not in network.stations.get(endpoint, []):
                issues.append(f"{label}: line '{line}' is not served by station '{endpoint}'")

        if not _is_number(distance) or distance <= 0:
            issues.append(f"{label}: distance must be a positive number")
            continue
        if distance < MIN_DISTANCE_M or distance > MAX_DISTANCE_M:
            issues.append(
                f"{label}: distance {distance} m is outside the plausible range "
                f"{MIN_DISTANCE_M}-{MAX_DISTANCE_M} m"
            )

        key = (frozenset((source, dest)), line)
        if key in seen:
            issues.append(f"{label}: duplicate connection")
        seen.add(key)


def _check_connectivity(network: SubwayNetwork, issues: List[str]) -> None:
    """Verify that every station can be reached from the first station."""
    if not network.stations:
        return
    adjacency = {name: set() for name in network.stations}
    for connection in network.connections:
        source = connection["source"]
        dest = connection["dest"]
        if source != dest and source in adjacency and dest in adjacency:
            adjacency[source].add(dest)
            adjacency[dest].add(source)

    start = next(iter(network.stations))
    visited = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for neighbour in adjacency[current]:
            if neighbour not in visited:
                visited.add(neighbour)
                stack.append(neighbour)

    for name in network.stations:
        if name not in visited:
            issues.append(f"Station '{name}' is not connected to the rest of the network")


def check_network(network: SubwayNetwork) -> IntegrityCheckResult:
    """Run all integrity checks on a network and return the result."""
    issues: List[str] = []
    _check_coverage(network, issues)
    _check_connections(network, issues)
    _check_connectivity(network, issues)
    return IntegrityCheckResult(passed=not issues, issues=issues)
