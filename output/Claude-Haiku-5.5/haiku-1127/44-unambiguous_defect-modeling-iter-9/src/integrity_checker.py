"""Data integrity checks for the subway dataset."""

# Representative main lines expected to be present in the dataset.
MAIN_LINES = (
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

MIN_PLAUSIBLE_DISTANCE_M = 50
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _norm(text):
    return "".join(str(text).split()).casefold()


class DataIntegrityChecker:
    """Runs coverage, connection, distance and connectivity checks.

    Attributes:
        coverage_threshold: minimum fraction of MAIN_LINES that must be present.
        last_check_result: "PASSED" or a "FAILED: ..." summary of the last run.
    """

    def __init__(self, coverage_threshold=0.9):
        self.coverage_threshold = coverage_threshold
        self.last_check_result = "NOT RUN"

    def check(self, manager):
        """Run all checks on a DataManager and return a list of issue strings."""
        network = manager.network
        raw = manager.raw_data
        issues = []
        issues.extend(self.check_coverage(network))
        issues.extend(self.check_stations(raw, network))
        issues.extend(self.check_connections(network))
        issues.extend(self.check_distances(raw))
        issues.extend(self.check_connectivity(network))
        if issues:
            self.last_check_result = f"FAILED: {len(issues)} issue(s) found"
        else:
            self.last_check_result = "PASSED"
        return issues

    def check_coverage(self, network):
        """Verify that representative main lines are present and populated."""
        issues = []
        found = 0
        for line in MAIN_LINES:
            canonical = network.canonical_line(line)
            if canonical is None:
                issues.append(f"Main line '{line}' is missing from the dataset")
                continue
            found += 1
            if len(network.stations_on_line(canonical)) < 2:
                issues.append(f"Main line '{line}' has fewer than 2 stations")
        ratio = found / len(MAIN_LINES)
        if ratio < self.coverage_threshold:
            issues.append(
                f"Main line coverage {ratio:.0%} is below threshold {self.coverage_threshold:.0%}"
            )
        return issues

    def check_stations(self, raw, network):
        """Check for duplicate names, stations without lines and isolated stations."""
        issues = []
        seen = set()
        for entry in raw.get("stations", []):
            name = " ".join(str(entry.get("name", "")).split())
            if name in seen:
                issues.append(f"Duplicate station entry '{name}'")
            seen.add(name)
            if not entry.get("lines"):
                issues.append(f"Station '{name}' has no lines")
        for name in network.station_names():
            number = network.get_number(name)
            if not network.graph.adjacent(number):
                issues.append(f"Station '{name}' has no connections")
        return issues

    def check_connections(self, network):
        """Check that connections are consistent with station line lists."""
        issues = []
        seen = set()
        for conn in network.connections:
            src, dst, line = conn["source"], conn["dest"], conn["line"]
            if src == dst:
                issues.append(f"Connection on '{line}' links station '{src}' to itself")
                continue
            for name in (src, dst):
                if line not in network.get_station_lines(name):
                    issues.append(
                        f"Connection {src} - {dst} on '{line}': station '{name}' "
                        f"does not list this line"
                    )
            key = (frozenset((src, dst)), line)
            if key in seen:
                issues.append(f"Duplicate connection {src} - {dst} on '{line}'")
            seen.add(key)
        return issues

    def check_distances(self, raw):
        """Check that distances are numeric and within plausible bounds."""
        issues = []
        for conn in raw.get("connections", []):
            label = f"{conn.get('source')} - {conn.get('dest')}"
            value = conn.get("distance")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                issues.append(f"Connection {label} has a non-numeric distance")
                continue
            if value <= 0:
                issues.append(f"Connection {label} has a non-positive distance {value}")
            elif value < MIN_PLAUSIBLE_DISTANCE_M or value > MAX_PLAUSIBLE_DISTANCE_M:
                issues.append(
                    f"Connection {label} distance {value} m is outside the plausible range "
                    f"{MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m"
                )
        return issues

    def check_connectivity(self, network):
        """Check that the whole network forms a single connected component."""
        components = network.graph.connected_components()
        if len(components) > 1:
            sizes = sorted((len(c) for c in components), reverse=True)
            return [f"Network is split into {len(components)} disconnected components (sizes {sizes})"]
        return []

    @staticmethod
    def format_report(issues):
        """Return a human-readable report of the issues."""
        if not issues:
            return "Data integrity check passed: no issues found."
        lines = [f"Data integrity check found {len(issues)} issue(s):"]
        lines.extend(f"  - {issue}" for issue in issues)
        return "\n".join(lines)
