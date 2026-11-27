"""Data integrity checks for the subway dataset (triggered by --check_data)."""

from collections import defaultdict

REQUIRED_MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]
MIN_STATIONS_PER_LINE = 2
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


class IntegrityReport:
    """Collects errors, warnings, and informational messages from checks."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    @property
    def ok(self):
        """True when no errors were found."""
        return not self.errors


def run_integrity_check(data):
    """Run coverage, connection, and distance checks on the dataset.

    Args:
        data: Dataset dictionary with "stations" and "connections" lists.

    Returns:
        IntegrityReport with the findings.
    """
    report = IntegrityReport()
    stations = data.get("stations", [])
    connections = data.get("connections", [])

    # Collect station -> lines, including lines only seen in connections.
    station_lines = defaultdict(set)
    seen_names = set()
    for st in stations:
        name = st["name"]
        if name in seen_names:
            report.warnings.append(f"Duplicate station entry: '{name}'")
        seen_names.add(name)
        station_lines[name].update(st.get("lines", []))
    for conn in connections:
        for end in (conn["source"], conn["dest"]):
            station_lines[end].add(conn["line"])

    # 1. Station data coverage of main lines.
    line_stations = defaultdict(set)
    for name, lines in station_lines.items():
        for line in lines:
            line_stations[line].add(name)
    for line in REQUIRED_MAIN_LINES:
        count = len(line_stations.get(line, ()))
        if count == 0:
            report.errors.append(f"Main line '{line}' is missing from the dataset")
        elif count < MIN_STATIONS_PER_LINE:
            report.errors.append(f"Main line '{line}' has too few stations ({count})")
        else:
            report.info.append(f"Main line '{line}' covered with {count} stations")

    # 2. Connection integrity.
    directed_pairs = set()
    seen_pairs = {}
    connected_stations = set()
    for idx, conn in enumerate(connections):
        src, dst, line = conn["source"], conn["dest"], conn["line"]
        label = f"connection #{idx} ({src} -> {dst}, {line})"
        if src not in station_lines or dst not in station_lines:
            report.errors.append(f"{label}: references an unknown station")
            continue
        if src == dst:
            report.errors.append(f"{label}: self-loop is not allowed")
        if line not in station_lines[src] or line not in station_lines[dst]:
            report.warnings.append(f"{label}: line is not listed for both endpoints")
        pair = (src, dst)
        if pair in seen_pairs:
            if seen_pairs[pair] != conn["distance"]:
                report.errors.append(f"{label}: conflicting duplicate distance for {src} -> {dst}")
            else:
                report.warnings.append(f"{label}: duplicate connection")
        seen_pairs[pair] = conn["distance"]
        directed_pairs.add(pair)
        connected_stations.update(pair)

        # 3. Distance accuracy.
        distance = conn["distance"]
        if not isinstance(distance, int) or distance <= 0:
            report.errors.append(f"{label}: distance must be a positive integer")
        elif not (MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M):
            report.warnings.append(
                f"{label}: distance {distance} m is outside the plausible range "
                f"[{MIN_PLAUSIBLE_DISTANCE_M}, {MAX_PLAUSIBLE_DISTANCE_M}] m")

    for src, dst in sorted(directed_pairs):
        if (dst, src) not in directed_pairs:
            report.warnings.append(
                f"One-way connection {src} -> {dst}: reverse direction is not listed")

    for name in sorted(station_lines):
        if name not in connected_stations:
            report.warnings.append(f"Station '{name}' has no connections")

    multi = sum(1 for lines in station_lines.values() if len(lines) > 1)
    report.info.append(f"Stations: {len(station_lines)}, connections: {len(connections)}, "
                       f"transfer stations: {multi}")
    return report


def format_check_report(report):
    """Render an IntegrityReport as console text."""
    out = ["Data integrity check", "-" * 40]
    for msg in report.info:
        out.append(f"[INFO]    {msg}")
    for msg in report.warnings:
        out.append(f"[WARNING] {msg}")
    for msg in report.errors:
        out.append(f"[ERROR]   {msg}")
    status = "PASSED" if report.ok else "FAILED"
    out.append("-" * 40)
    out.append(f"Result: {status} ({len(report.errors)} errors, {len(report.warnings)} warnings)")
    return "\n".join(out)
