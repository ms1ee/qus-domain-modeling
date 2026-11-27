"""Data integrity checks for the subway network (``--check_data``)."""

from collections import deque
from dataclasses import dataclass, field
from typing import List

# Representative stations of main lines used for coverage validation.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "复兴门", "国贸"],
    "Line 2": ["西直门", "建国门", "东直门"],
    "Line 4": ["圆明园", "北京大学东门"],
    "Line 5": ["天通苑北", "宋家庄"],
    "Line 6": ["海淀五路居", "北海北"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["公主坟", "国贸"],
    "Line 13": ["回龙观", "西直门"],
    "Line 14": ["张郭庄"],
    "Line 15": ["俸伯"],
    "Changping Line": ["昌平"],
    "Yizhuang Line": ["亦庄火车站"],
    "Fangshan Line": ["郭公庄"],
    "Airport Line": ["首都机场"],
}

# Distances (meters) above this value are reported as errors; above the warning
# threshold they are reported as warnings.
MAX_PLAUSIBLE_DISTANCE_M = 10000
WARNING_DISTANCE_M = 8000


@dataclass
class IntegrityReport:
    """Result of a data integrity check."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no errors were found (warnings are allowed)."""
        return not self.errors

    def format(self) -> str:
        """Render the report as human-readable text."""
        lines = ["Data integrity check", "-" * 40]
        lines.extend(f"[INFO]    {msg}" for msg in self.info)
        lines.extend(f"[WARNING] {msg}" for msg in self.warnings)
        lines.extend(f"[ERROR]   {msg}" for msg in self.errors)
        lines.append("-" * 40)
        lines.append(
            "Result: PASSED" if self.ok else "Result: FAILED"
        )
        lines.append(
            f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}"
        )
        return "\n".join(lines)


def check_data_integrity(network) -> IntegrityReport:
    """Run all integrity checks on a ``SubwayNetwork``.

    Checks performed:
        * station coverage of representative stations of main lines;
        * connection integrity (endpoints, self-loops, duplicates, isolated
          stations, connectivity, line consistency);
        * distance accuracy (positive, plausible magnitude).

    Returns:
        An ``IntegrityReport`` describing all findings.
    """
    report = IntegrityReport()
    _check_coverage(network, report)
    _check_connections(network, report)
    _check_distances(network, report)
    report.info.append(
        f"Stations: {len(network.station_to_number)}, "
        f"connections: {network.edge_count()}, "
        f"lines: {len(network.all_lines())}, "
        f"transfer stations: {len(network.transfer_stations())}"
    )
    return report


def _check_coverage(network, report: IntegrityReport) -> None:
    lines = set(network.all_lines())
    for line, representatives in REPRESENTATIVE_STATIONS.items():
        if line not in lines:
            report.warnings.append(f"Line '{line}' is not present in the data")
            continue
        for station in representatives:
            if not network.has_station(station):
                report.warnings.append(
                    f"Representative station '{station}' of {line} is missing"
                )


def _check_connections(network, report: IntegrityReport) -> None:
    report.warnings.extend(network.load_warnings)
    graph = network.graph
    seen = set()

    for edge in graph.edges():
        src_name = network.name_of(edge.source)
        dst_name = network.name_of(edge.dest)
        if edge.source == edge.dest:
            report.errors.append(f"Self-loop connection at station '{src_name}'")
            continue
        for number, name in ((edge.source, src_name), (edge.dest, dst_name)):
            if edge.line not in graph.station_lines.get(name, []):
                report.warnings.append(
                    f"Connection {src_name}-{dst_name} on '{edge.line}', but station "
                    f"'{name}' is not registered on that line"
                )
        key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
        if key in seen:
            report.warnings.append(
                f"Duplicate connection {src_name}-{dst_name} on '{edge.line}'"
            )
        seen.add(key)

    for number in graph.vertices():
        if not graph.neighbors(number):
            report.errors.append(
                f"Station '{network.name_of(number)}' has no connections"
            )

    _check_connectivity(network, report)


def _check_connectivity(network, report: IntegrityReport) -> None:
    vertices = network.graph.vertices()
    if not vertices:
        report.errors.append("The network contains no stations")
        return
    unvisited = set(vertices)
    components = 0
    while unvisited:
        components += 1
        start = unvisited.pop()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for edge in network.graph.neighbors(current):
                nxt = edge.other(current)
                if nxt in unvisited:
                    unvisited.discard(nxt)
                    queue.append(nxt)
    if components > 1:
        report.warnings.append(
            f"The network is split into {components} disconnected components"
        )


def _check_distances(network, report: IntegrityReport) -> None:
    for edge in network.graph.edges():
        src_name = network.name_of(edge.source)
        dst_name = network.name_of(edge.dest)
        label = f"{src_name}-{dst_name} on '{edge.line}'"
        if edge.distance <= 0:
            report.errors.append(f"Non-positive distance {edge.distance} m for {label}")
        elif edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
            report.errors.append(f"Implausible distance {edge.distance} m for {label}")
        elif edge.distance > WARNING_DISTANCE_M:
            report.warnings.append(f"Unusually long distance {edge.distance} m for {label}")
