"""Data integrity checks for the subway network."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from network import SubwayNetwork

# Main lines that must be represented in the dataset (PRD section 4.1).
REQUIRED_LINES = [
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

# Plausible range for a single inter-station distance (meters).
MIN_DISTANCE_M = 50
MAX_DISTANCE_M = 10_000


@dataclass
class DataChecker:
    """Result of a data integrity check."""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)


def check_network(network: SubwayNetwork) -> DataChecker:
    """Run coverage, connection integrity, distance accuracy and connectivity checks."""
    errors: List[str] = []
    _check_line_coverage(network, errors)
    _check_connections(network, errors)
    _check_connectivity(network, errors)
    return DataChecker(is_valid=not errors, errors=errors)


def _check_line_coverage(network: SubwayNetwork, errors: List[str]) -> None:
    present = set(network.line_names())
    for line in REQUIRED_LINES:
        if line not in present:
            errors.append(f"coverage: main line '{line}' is missing from the dataset")
    if not network.stations():
        errors.append("coverage: dataset contains no stations")


def _check_connections(network: SubwayNetwork, errors: List[str]) -> None:
    seen_pairs = set()
    for conn in network.raw["connections"]:
        src = str(conn.get("source", "")).strip()
        dst = str(conn.get("dest", "")).strip()
        line = conn.get("line", "")
        label = f"{src} - {dst} ({line})"

        if not src or not dst:
            errors.append(f"integrity: connection {label} has an empty station name")
            continue
        if src == dst:
            errors.append(f"integrity: connection {label} links a station to itself")
            continue
        if src not in network.station_to_number or dst not in network.station_to_number:
            errors.append(f"integrity: connection {label} references an unknown station")
            continue

        distance = conn.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            errors.append(f"accuracy: connection {label} has a non-numeric distance")
        elif distance <= 0:
            errors.append(f"accuracy: connection {label} has a non-positive distance {distance}")
        elif not (MIN_DISTANCE_M <= distance <= MAX_DISTANCE_M):
            errors.append(
                f"accuracy: connection {label} distance {distance} m is outside "
                f"the plausible range {MIN_DISTANCE_M}-{MAX_DISTANCE_M} m"
            )

        for end in (src, dst):
            if line not in network.lines_of(end):
                errors.append(f"integrity: line '{line}' is not listed for station '{end}'")

        key = (tuple(sorted((src, dst))), line)
        if key in seen_pairs:
            errors.append(f"integrity: duplicate connection {label}")
        seen_pairs.add(key)

    for skipped in network.skipped_connections:
        errors.append(f"integrity: invalid connection skipped: {skipped}")


def _check_connectivity(network: SubwayNetwork, errors: List[str]) -> None:
    graph = network.graph
    vertices = graph.vertices()
    if not vertices:
        return
    for v in vertices:
        if not graph.adjacent(v):
            errors.append(f"integrity: station '{network.name_of(v)}' has no connections")

    start = vertices[0]
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for edge in graph.adjacent(v):
            w = edge.other(v)
            if w not in seen:
                seen.add(w)
                stack.append(w)
    unreachable = [network.name_of(v) for v in vertices if v not in seen]
    if unreachable:
        errors.append(
            f"integrity: {len(unreachable)} station(s) unreachable from "
            f"'{network.name_of(start)}': {', '.join(unreachable[:10])}"
        )
