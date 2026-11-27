"""
Data integrity checks for the subway dataset.

The checker validates:
  * station coverage of the main lines,
  * the consistency of station and connection records,
  * the plausibility of distance data,
  * the connectivity of the network.
"""

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Plausible range of a single inter-station distance, in meters.
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000


class DataIntegrityChecker:
    """
    Runs integrity checks on a subway dataset dictionary.

    Attributes:
        last_check_passed: Result of the most recent check.
        main_lines: Main line names that must be covered by the dataset.
        errors: Errors found by the last check (fail the check).
        warnings: Warnings found by the last check (do not fail the check).
    """

    def __init__(self, main_lines=None,
                 min_distance_m=MIN_PLAUSIBLE_DISTANCE_M,
                 max_distance_m=MAX_PLAUSIBLE_DISTANCE_M):
        self.main_lines = list(main_lines or MAIN_LINES)
        self.min_distance_m = min_distance_m
        self.max_distance_m = max_distance_m
        self.last_check_passed = False
        self.errors = []
        self.warnings = []

    def check(self, data):
        """
        Run all integrity checks.

        Args:
            data: dict with ``stations`` and ``connections`` lists.

        Returns:
            bool: True if no errors were found.
        """
        self.errors = []
        self.warnings = []
        stations = data.get("stations", []) or []
        connections = data.get("connections", []) or []

        names, station_lines = self._check_stations(stations)
        self._check_coverage(station_lines, connections)
        self._check_connections(connections, names, station_lines)
        self._check_connectivity(connections, names)

        self.last_check_passed = not self.errors
        return self.last_check_passed

    def report_lines(self):
        """Return a list of printable lines summarising the last check."""
        lines = ["Data integrity check: " + ("PASSED" if self.last_check_passed else "FAILED")]
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            lines.extend(f"  [ERROR] {msg}" for msg in self.errors)
        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            lines.extend(f"  [WARN] {msg}" for msg in self.warnings)
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        return lines

    # ------------------------------------------------------------ helpers
    def _check_stations(self, stations):
        """Validate station records. Returns (set of names, dict name -> lines)."""
        names = set()
        station_lines = {}
        for index, st in enumerate(stations):
            if not isinstance(st, dict):
                self.errors.append(f"Station record #{index} is not an object")
                continue
            name = str(st.get("name", "")).strip()
            if not name:
                self.errors.append(f"Station record #{index} has no name")
                continue
            if name in names:
                self.errors.append(f"Duplicate station name '{name}'")
                continue
            names.add(name)
            lines = st.get("lines")
            if not isinstance(lines, list) or not lines:
                self.warnings.append(f"Station '{name}' has no line information")
                station_lines[name] = []
            else:
                station_lines[name] = [str(x).strip() for x in lines]
        return names, station_lines

    def _check_coverage(self, station_lines, connections):
        """Verify that representative main lines are present in the dataset."""
        covered = set()
        for lines in station_lines.values():
            covered.update(lines)
        for conn in connections:
            if isinstance(conn, dict) and conn.get("line"):
                covered.add(str(conn["line"]).strip())

        for line in self.main_lines:
            count = sum(1 for lines in station_lines.values() if line in lines)
            if line not in covered:
                self.warnings.append(f"Main line '{line}' is not covered by the dataset")
            elif count < 2:
                self.warnings.append(
                    f"Main line '{line}' has only {count} station(s) in the dataset")

    def _check_connections(self, connections, names, station_lines):
        """Validate connection records, distances and line consistency."""
        seen = set()
        for index, conn in enumerate(connections):
            if not isinstance(conn, dict):
                self.errors.append(f"Connection record #{index} is not an object")
                continue
            missing = [k for k in ("source", "dest", "distance", "line") if k not in conn]
            if missing:
                self.errors.append(
                    f"Connection record #{index} is missing field(s): {', '.join(missing)}")
                continue

            src = str(conn["source"]).strip()
            dst = str(conn["dest"]).strip()
            line = str(conn["line"]).strip()
            valid_endpoints = True
            for endpoint in (src, dst):
                if endpoint not in names:
                    self.errors.append(
                        f"Connection #{index} references unknown station '{endpoint}'")
                    valid_endpoints = False
            if src == dst:
                self.errors.append(f"Connection #{index} joins station '{src}' to itself")

            dist = conn["distance"]
            if isinstance(dist, bool) or not isinstance(dist, (int, float)):
                self.errors.append(
                    f"Connection #{index} ({src} - {dst}) has a non-numeric distance")
            elif dist <= 0:
                self.errors.append(
                    f"Connection #{index} ({src} - {dst}) has a non-positive distance {dist}")
            elif not (self.min_distance_m <= dist <= self.max_distance_m):
                self.warnings.append(
                    f"Distance {dist} m between '{src}' and '{dst}' is outside the "
                    f"plausible range [{self.min_distance_m}, {self.max_distance_m}]")

            if valid_endpoints:
                for endpoint in (src, dst):
                    lines = station_lines.get(endpoint, [])
                    if lines and line not in lines:
                        self.warnings.append(
                            f"Line '{line}' of connection '{src}' - '{dst}' is not listed "
                            f"for station '{endpoint}'")
                key = (frozenset((src, dst)), line)
                if key in seen:
                    self.warnings.append(
                        f"Duplicate connection '{src}' - '{dst}' on line '{line}'")
                seen.add(key)

    def _check_connectivity(self, connections, names):
        """Check for isolated stations and disconnected network components."""
        adjacency = {name: set() for name in names}
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            src = str(conn.get("source", "")).strip()
            dst = str(conn.get("dest", "")).strip()
            if src in adjacency and dst in adjacency and src != dst:
                adjacency[src].add(dst)
                adjacency[dst].add(src)

        for name in sorted(n for n in names if not adjacency[n]):
            self.warnings.append(f"Station '{name}' has no connections")

        seen = set()
        components = 0
        for start in sorted(names):
            if start in seen:
                continue
            components += 1
            seen.add(start)
            stack = [start]
            while stack:
                current = stack.pop()
                for neighbour in adjacency[current]:
                    if neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)
        if components > 1:
            self.warnings.append(
                f"Network is split into {components} disconnected components")
