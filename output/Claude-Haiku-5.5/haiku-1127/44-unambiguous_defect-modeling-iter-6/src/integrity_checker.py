"""Data integrity checks for the subway dataset (triggered by --check_data)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from data_loader import build_network, parse_distance
from models import SubwayNetwork

# Representative stations of the main lines used for coverage checks.
REPRESENTATIVE_STATIONS = [
    "苹果园", "西直门", "东直门", "建国门", "国贸", "天安门东", "四惠东",
    "西单", "东单", "北京南站", "宋家庄", "北海北", "东大桥", "巴沟",
    "大钟寺", "回龙观", "西二旗", "望京西", "首都机场", "郭公庄",
]

MIN_PLAUSIBLE_DISTANCE_METERS = 100.0
MAX_PLAUSIBLE_DISTANCE_METERS = 10000.0


@dataclass
class IntegrityReport:
    """Outcome of a data integrity check."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no errors were found (warnings are allowed)."""
        return not self.errors

    def to_text(self) -> str:
        """Render the report as text."""
        lines = [f"Data integrity check: {'PASSED' if self.ok else 'FAILED'}"]
        lines.extend(f"  [info]    {message}" for message in self.info)
        lines.extend(f"  [warning] {message}" for message in self.warnings)
        lines.extend(f"  [error]   {message}" for message in self.errors)
        return "\n".join(lines)


class DataIntegrityChecker:
    """Runs coverage, connection and distance checks on the dataset."""

    def __init__(self) -> None:
        self.last_check_result: str = ""

    def check(self, data: Dict[str, Any], network: Optional[SubwayNetwork] = None) -> IntegrityReport:
        """Run all checks and store the textual result in ``last_check_result``."""
        if network is None:
            network = build_network(data)
        report = IntegrityReport()
        self._check_station_entries(data, report)
        self._check_station_coverage(network, report)
        self._check_connections(data, network, report)
        self._check_connectivity(network, report)
        report.info.append(
            f"{network.graph.vertex_count} stations, {network.graph.edge_count} connections, "
            f"{len(network.line_names)} lines"
        )
        self.last_check_result = report.to_text()
        return report

    @staticmethod
    def _check_station_entries(data: Dict[str, Any], report: IntegrityReport) -> None:
        seen: Set[str] = set()
        for index, entry in enumerate(data.get("stations", []), 1):
            name = str(entry.get("name", "")).strip()
            if not name:
                report.errors.append(f"Station entry #{index} has no name")
                continue
            if name in seen:
                report.errors.append(f"Duplicate station name: '{name}'")
            seen.add(name)
            if not entry.get("lines"):
                report.warnings.append(f"Station '{name}' has no line information")

    @staticmethod
    def _check_station_coverage(network: SubwayNetwork, report: IntegrityReport) -> None:
        missing = [name for name in REPRESENTATIVE_STATIONS if name not in network.station_to_number]
        if missing:
            report.warnings.append(
                f"Representative stations missing from dataset: {', '.join(missing)}"
            )

    @staticmethod
    def _check_connections(data: Dict[str, Any], network: SubwayNetwork, report: IntegrityReport) -> None:
        station_lines: Dict[str, Set[str]] = {}
        for entry in data.get("stations", []):
            name = str(entry.get("name", "")).strip()
            station_lines.setdefault(name, set()).update(str(l).strip() for l in entry.get("lines", []))

        seen_keys: Dict[tuple, int] = {}
        for index, conn in enumerate(data.get("connections", []), 1):
            try:
                src = str(conn["source"]).strip()
                dst = str(conn["dest"]).strip()
                line = str(conn["line"]).strip()
            except (KeyError, TypeError):
                report.errors.append(f"Connection #{index} is missing a required field")
                continue
            label = f"Connection #{index} ({src} - {dst}, {line})"
            if src == dst:
                report.errors.append(f"{label} connects a station to itself")
                continue
            for name in (src, dst):
                if name not in station_lines:
                    report.errors.append(f"{label} references unknown station '{name}'")
                elif line not in station_lines[name]:
                    report.warnings.append(f"{label}: station '{name}' does not list line '{line}'")
            distance = parse_distance(conn.get("distance"))
            if distance is None:
                report.errors.append(f"{label} has an invalid distance: {conn.get('distance')!r}")
            else:
                if not float(distance).is_integer():
                    report.warnings.append(f"{label} distance {distance} is not an integer number of meters")
                if not (MIN_PLAUSIBLE_DISTANCE_METERS <= distance <= MAX_PLAUSIBLE_DISTANCE_METERS):
                    report.warnings.append(
                        f"{label} distance {distance:.0f} m is outside the plausible range "
                        f"({MIN_PLAUSIBLE_DISTANCE_METERS:.0f}-{MAX_PLAUSIBLE_DISTANCE_METERS:.0f} m)"
                    )
            key = (min(src, dst), max(src, dst), line)
            if key in seen_keys:
                report.warnings.append(f"{label} duplicates connection #{seen_keys[key]}")
            else:
                seen_keys[key] = index

        for name, number in network.station_to_number.items():
            if not network.graph.adjacent(number):
                report.warnings.append(f"Station '{name}' has no connections")

    @staticmethod
    def _check_connectivity(network: SubwayNetwork, report: IntegrityReport) -> None:
        components = network.graph.connected_components()
        if len(components) > 1:
            sizes = sorted((len(c) for c in components), reverse=True)
            report.warnings.append(
                f"Network is split into {len(components)} disconnected components (sizes {sizes})"
            )
