"""Data management: integrity checks and data update operations for the subway network."""

import math
from collections import deque

from data_loader import DATA_FILE_PATH, save_subway_data
from input_validator import normalize_key
from models import SubwayNetwork

LEVEL_ERROR = "ERROR"
LEVEL_WARNING = "WARNING"
LEVEL_INFO = "INFO"

# Expected main lines and the aliases under which they may appear in the dataset.
EXPECTED_MAIN_LINES = {
    "Line 1": ("Line 1", "1号线"),
    "Line 2": ("Line 2", "2号线"),
    "Line 4": ("Line 4", "4号线"),
    "Line 5": ("Line 5", "5号线"),
    "Line 6": ("Line 6", "6号线"),
    "Line 8": ("Line 8", "8号线"),
    "Line 10": ("Line 10", "10号线"),
    "Line 13": ("Line 13", "13号线"),
    "Line 14": ("Line 14", "14号线"),
    "Line 15": ("Line 15", "15号线"),
    "Changping Line": ("Changping Line", "昌平线"),
    "Yizhuang Line": ("Yizhuang Line", "亦庄线"),
    "Fangshan Line": ("Fangshan Line", "房山线"),
    "Airport Line": ("Airport Line", "机场线"),
}

# One representative station per main line, used for coverage checks.
REPRESENTATIVE_STATIONS = {
    "Line 1": "苹果园",
    "Line 2": "西直门",
    "Line 4": "圆明园",
    "Line 5": "宋家庄",
    "Line 6": "海淀五路居",
    "Line 8": "鼓楼大街",
    "Line 10": "国贸",
    "Line 13": "回龙观",
    "Line 14": "张郭庄",
    "Line 15": "望京东",
    "Changping Line": "西二旗",
    "Yizhuang Line": "亦庄火车站",
    "Fangshan Line": "郭公庄",
    "Airport Line": "T3航站楼",
}

# Plausible range for inter-station distances in meters (sanity check only).
PLAUSIBLE_MIN_DISTANCE = 100
PLAUSIBLE_MAX_DISTANCE = 8000


class IntegrityIssue:
    """A single finding from the integrity check."""

    def __init__(self, level, category, message):
        self.level = level
        self.category = category
        self.message = message

    def __str__(self):
        return f"[{self.level}] ({self.category}) {self.message}"


class IntegrityReport:
    """Collection of integrity findings plus summary statistics."""

    def __init__(self):
        self.issues = []
        self.stats = {}

    def add(self, level, category, message):
        """Record an issue."""
        self.issues.append(IntegrityIssue(level, category, message))

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == LEVEL_ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == LEVEL_WARNING)

    @property
    def passed(self) -> bool:
        """True if no errors were found (warnings are allowed)."""
        return self.error_count == 0

    def format(self) -> str:
        """Return a console-formatted report."""
        lines = ["Data integrity check", "=" * 64]
        for key in ("stations", "lines", "connections"):
            if key in self.stats:
                lines.append(f"{key.capitalize()}: {self.stats[key]}")
        lines.append("-" * 64)
        if not self.issues:
            lines.append("No issues found.")
        for issue in self.issues:
            lines.append(str(issue))
        lines.append("-" * 64)
        verdict = "PASSED" if self.passed else "FAILED"
        lines.append(f"Result: {verdict} ({self.error_count} errors, {self.warning_count} warnings)")
        return "\n".join(lines)


def _is_valid_distance(value) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value > 0)


def check_data_integrity(data, network=None) -> IntegrityReport:
    """Run data coverage, connection and distance checks on a dataset.

    Args:
        data: Dataset dictionary (stations and connections).
        network: Optional prebuilt SubwayNetwork for data; built from ``data`` if None.

    Returns:
        An IntegrityReport describing all findings.
    """
    report = IntegrityReport()
    if network is None:
        network = SubwayNetwork.from_data(data)
    stations = data.get("stations", []) if isinstance(data, dict) else []
    connections = data.get("connections", []) if isinstance(data, dict) else []

    report.stats = {
        "stations": len(network.station_names()),
        "lines": len(network.lines()),
        "connections": network.graph.num_edges(),
    }
    for warning in network.build_warnings:
        report.add(LEVEL_WARNING, "loading", warning)

    # --- Station records ---
    raw_lines = {}
    seen_names = set()
    for item in stations:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) \
                or not item["name"].strip():
            report.add(LEVEL_ERROR, "stations", f"Malformed station record: {item!r}")
            continue
        name = item["name"].strip()
        if name in seen_names:
            report.add(LEVEL_WARNING, "stations", f"Duplicate station record: '{name}'")
        seen_names.add(name)
        lines = item.get("lines", [])
        if not isinstance(lines, list):
            report.add(LEVEL_ERROR, "stations", f"Station '{name}' has a non-list 'lines' field")
            continue
        if not lines:
            report.add(LEVEL_WARNING, "stations", f"Station '{name}' is not assigned to any line")
        raw_lines.setdefault(name, set()).update(
            str(line).strip() for line in lines if isinstance(line, str))

    # --- Station data coverage ---
    line_keys = {normalize_key(line) for line in network.lines()}
    for expected, aliases in EXPECTED_MAIN_LINES.items():
        if not any(normalize_key(alias) in line_keys for alias in aliases):
            report.add(LEVEL_ERROR, "coverage", f"Main line '{expected}' is missing from the dataset")
    station_keys = {normalize_key(name) for name in network.station_names()}
    for line, station in REPRESENTATIVE_STATIONS.items():
        if normalize_key(station) not in station_keys:
            report.add(LEVEL_WARNING, "coverage",
                       f"Representative station '{station}' of {line} is not in the dataset")

    # --- Connection integrity and distance accuracy ---
    distances_by_pair = {}
    for index, conn in enumerate(connections, 1):
        if not isinstance(conn, dict) or any(k not in conn for k in ("source", "dest", "distance", "line")):
            report.add(LEVEL_ERROR, "connections", f"Malformed connection record #{index}: {conn!r}")
            continue
        src = str(conn["source"]).strip()
        dst = str(conn["dest"]).strip()
        line = str(conn["line"]).strip()
        label = f"{src} - {dst} ({line})"
        if src == dst:
            report.add(LEVEL_ERROR, "connections", f"Self-connection at {label}")
            continue
        ok = True
        for name in (src, dst):
            if name not in raw_lines:
                report.add(LEVEL_ERROR, "connections", f"Connection {label} references unknown station '{name}'")
                ok = False
            elif line not in raw_lines[name]:
                report.add(LEVEL_ERROR, "connections",
                           f"Station '{name}' in connection {label} is not listed as serving {line}")
                ok = False
        distance = conn["distance"]
        if not _is_valid_distance(distance):
            report.add(LEVEL_ERROR, "distances", f"Invalid distance {distance!r} for {label}")
            continue
        if distance < PLAUSIBLE_MIN_DISTANCE or distance > PLAUSIBLE_MAX_DISTANCE:
            report.add(LEVEL_WARNING, "distances",
                       f"Distance {distance} m for {label} is outside the plausible range "
                       f"({PLAUSIBLE_MIN_DISTANCE}-{PLAUSIBLE_MAX_DISTANCE} m)")
        if ok:
            key = (frozenset((src, dst)), line)
            distances_by_pair.setdefault(key, []).append(distance)

    for (pair, line), values in distances_by_pair.items():
        names = " - ".join(sorted(pair))
        if len(set(values)) > 1:
            report.add(LEVEL_ERROR, "distances",
                       f"Conflicting distances {sorted(set(values))} recorded for {names} ({line})")
        elif len(values) > 1:
            report.add(LEVEL_WARNING, "connections",
                       f"Duplicate connection recorded for {names} ({line})")

    # --- Network connectivity ---
    graph = network.graph
    for name in network.station_names():
        number = network.station_to_number[name]
        if not graph.adjacent(number):
            report.add(LEVEL_WARNING, "connectivity", f"Station '{name}' has no connections")
    components = []
    visited = set()
    for number in graph.vertices():
        if number in visited:
            continue
        size = 0
        queue = deque([number])
        visited.add(number)
        while queue:
            current = queue.popleft()
            size += 1
            for edge in graph.adjacent(current):
                nxt = edge.other(current)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        components.append(size)
    if len(components) > 1:
        report.add(LEVEL_WARNING, "connectivity",
                   f"Network has {len(components)} disconnected components "
                   f"(sizes: {sorted(components, reverse=True)})")

    transfer_count = len(network.transfer_stations())
    report.add(LEVEL_INFO, "transfers", f"{transfer_count} interchange (multi-line) stations found")
    return report


class DataManager:
    """Data update operations on a SubwayNetwork, plus integrity checks and persistence."""

    def __init__(self, network):
        self.network = network

    def add_line(self, line_name, station_names, distances):
        """Add a new line with ordered stations and consecutive distances (meters)."""
        self.network.add_line(line_name, station_names, distances)

    def modify_station(self, old_name, new_name=None, lines=None) -> str:
        """Rename a station and/or replace its lines. Returns the resulting name."""
        return self.network.modify_station(old_name, new_name, lines)

    def update_distance(self, source, dest, distance, line=None) -> int:
        """Update the distance of connection(s) between two stations. Returns count updated."""
        return self.network.update_distance(source, dest, distance, line)

    def check_integrity(self) -> IntegrityReport:
        """Run integrity checks on the current network state."""
        data = self.export_data()
        return check_data_integrity(data, None)

    def export_data(self) -> dict:
        """Export the current network to the dataset format."""
        return self.network.export_data()

    def save(self, path=DATA_FILE_PATH):
        """Persist the current network to a dataset JSON file."""
        save_subway_data(self.export_data(), path)
