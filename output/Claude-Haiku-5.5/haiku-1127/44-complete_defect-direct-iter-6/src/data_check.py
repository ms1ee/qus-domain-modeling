"""Data integrity checks for the subway dataset (used by --check_data).

Checks performed:
    * coverage: main lines and representative stations are present;
    * connections: endpoints exist, no self-loops, no duplicates, lines match;
    * distances: positive integers within plausible bounds;
    * connectivity: the network forms a single connected component.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

MAIN_LINES = [
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

# Representative stations used by the coverage check (official Chinese names).
REPRESENTATIVE_STATIONS = {
    "Line 1": ["苹果园", "天安门西"],
    "Line 2": ["西直门", "东直门"],
    "Line 4": ["动物园"],
    "Line 5": ["宋家庄"],
    "Line 6": ["海淀五路居"],
    "Line 8": ["鼓楼大街"],
    "Line 10": ["西土城"],
    "Line 13": ["大钟寺"],
}

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000


@dataclass
class DataCheckReport:
    """Outcome of a data integrity check."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        """True when no errors were found (warnings are allowed)."""
        return not self.errors


def run_data_check(data: Dict[str, Any]) -> DataCheckReport:
    """Run all integrity checks on a raw subway dataset dictionary."""
    report = DataCheckReport()
    if not isinstance(data, dict):
        report.errors.append("data root must be a JSON object")
        return report

    stations_raw = data.get("stations")
    connections_raw = data.get("connections")
    if not isinstance(stations_raw, list):
        report.errors.append("'stations' must be a list")
        stations_raw = []
    if not isinstance(connections_raw, list):
        report.errors.append("'connections' must be a list")
        connections_raw = []

    # ---- stations
    station_lines: Dict[str, Set[str]] = {}
    for index, entry in enumerate(stations_raw):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("name"), str)
            or not entry["name"].strip()
        ):
            report.errors.append(f"stations[{index}] is malformed")
            continue
        name = entry["name"].strip()
        lines = entry.get("lines", [])
        if not isinstance(lines, list):
            report.errors.append(f"stations[{index}] 'lines' must be a list")
            lines = []
        if name in station_lines:
            report.errors.append(f"duplicate station name '{name}'")
        station_lines.setdefault(name, set()).update(
            line for line in lines if isinstance(line, str)
        )

    # ---- connections
    lines_present: Set[str] = set()
    for lines in station_lines.values():
        lines_present |= lines
    adjacency: Dict[str, Set[str]] = {name: set() for name in station_lines}
    seen_keys = set()
    valid_connection_count = 0

    for index, entry in enumerate(connections_raw):
        if not isinstance(entry, dict):
            report.errors.append(f"connections[{index}] is malformed")
            continue
        source = entry.get("source")
        dest = entry.get("dest")
        line = entry.get("line")
        distance = entry.get("distance")

        if not all(isinstance(v, str) and v.strip() for v in (source, dest, line)):
            report.errors.append(f"connections[{index}] has missing source/dest/line")
            continue
        source, dest, line = source.strip(), dest.strip(), line.strip()

        if source not in station_lines:
            report.errors.append(f"connections[{index}] references unknown station '{source}'")
            continue
        if dest not in station_lines:
            report.errors.append(f"connections[{index}] references unknown station '{dest}'")
            continue
        if source == dest:
            report.errors.append(f"connections[{index}] is a self-loop at '{source}'")
            continue
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            report.errors.append(
                f"connection {source}-{dest} has a non-positive or non-integer distance"
            )
            continue
        if distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
            report.warnings.append(
                f"Accuracy: connection {source}-{dest} distance {distance} m is outside "
                f"the plausible range {MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
            )

        for name in (source, dest):
            if line not in station_lines[name]:
                report.warnings.append(
                    f"Integrity: connection {source}-{dest} uses line '{line}' "
                    f"which is not listed for station '{name}'"
                )

        key = (min(source, dest), max(source, dest), line)
        if key in seen_keys:
            report.warnings.append(f"duplicate connection {source}-{dest} on '{line}'")
        else:
            seen_keys.add(key)

        adjacency[source].add(dest)
        adjacency[dest].add(source)
        lines_present.add(line)
        valid_connection_count += 1

    # ---- coverage
    for line in MAIN_LINES:
        if line not in lines_present:
            report.warnings.append(f"Coverage: main line '{line}' has no stations in the dataset")
        for station in REPRESENTATIVE_STATIONS.get(line, []):
            if station not in station_lines:
                report.warnings.append(
                    f"Coverage: representative station '{station}' of {line} is missing"
                )

    # ---- connectivity
    for name, neighbours in adjacency.items():
        if not neighbours:
            report.warnings.append(f"Connectivity: station '{name}' has no connections")

    components = _connected_components(adjacency)
    if len(components) > 1:
        sizes = sorted((len(c) for c in components), reverse=True)
        report.warnings.append(
            f"Connectivity: network has {len(components)} disconnected components "
            f"(sizes: {sizes})"
        )

    report.info.append(f"Stations checked: {len(station_lines)}")
    report.info.append(f"Valid connections checked: {valid_connection_count}")
    report.info.append(f"Lines found: {len(lines_present)}")
    return report


def _connected_components(adjacency: Dict[str, Set[str]]) -> List[Set[str]]:
    """Return the connected components of an undirected adjacency mapping."""
    remaining = set(adjacency)
    components: List[Set[str]] = []
    while remaining:
        start = remaining.pop()
        component = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbour in adjacency.get(current, ()):
                if neighbour not in component:
                    component.add(neighbour)
                    remaining.discard(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def format_check_report(report: DataCheckReport) -> str:
    """Render a DataCheckReport as human-readable console text."""
    out = [f"Data integrity check: {'PASSED' if report.is_ok() else 'FAILED'}"]
    out.append(f"Errors ({len(report.errors)}):")
    out.extend(f"  - {item}" for item in report.errors or ["  none"])
    out.append(f"Warnings ({len(report.warnings)}):")
    out.extend(f"  - {item}" for item in report.warnings or ["  none"])
    out.append("Summary:")
    out.extend(f"  {item}" for item in report.info)
    return "\n".join(out)
