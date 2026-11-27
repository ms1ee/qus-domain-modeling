"""Data integrity checks for the subway dataset (run via --check_data)."""

# Representative lines that must be present in the network.
REQUIRED_LINES = (
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

MIN_ADJACENT_DISTANCE_M = 1
MAX_ADJACENT_DISTANCE_M = 10000


class DataIntegrityChecker:
    """Runs coverage, connection and distance checks over a SubwayNetwork.

    Attributes:
        is_passed: False if any error (not warning) was found.
        messages: list of human-readable result messages prefixed with ERROR or WARNING.
    """

    def __init__(self):
        self.is_passed = True
        self.messages = []

    def _error(self, text):
        self.is_passed = False
        self.messages.append(f"ERROR: {text}")

    def _warning(self, text):
        self.messages.append(f"WARNING: {text}")

    def check(self, network):
        """Run all checks and return is_passed."""
        self.is_passed = True
        self.messages = []
        data = network.data
        stations = data.get("stations", [])
        connections = data.get("connections", [])

        self._check_coverage(stations, connections)
        self._check_connections(stations, connections)
        self._check_distances(connections)

        if self.is_passed:
            self.messages.append(
                f"INFO: {len(stations)} stations, {len(connections)} connection records checked"
            )
        return self.is_passed

    def _check_coverage(self, stations, connections):
        """Verify that representative stations of main lines are included."""
        present_lines = set()
        for entry in stations:
            present_lines.update(entry.get("lines", []))
        for conn in connections:
            if conn.get("line"):
                present_lines.add(conn["line"])
        for line_name in REQUIRED_LINES:
            if line_name not in present_lines:
                self._error(f"Main line '{line_name}' is missing from the network")

        seen = {}
        for entry in stations:
            name = str(entry.get("name", "")).strip()
            key = "".join(name.split()).lower()
            if not key:
                self._error("A station entry has an empty name")
            elif key in seen and seen[key] != name:
                self._error(f"Station names '{seen[key]}' and '{name}' are duplicates")
            else:
                seen[key] = name

    def _check_connections(self, stations, connections):
        """Verify endpoints exist, no self-loops, and reverse connections are present."""
        known = {entry.get("name") for entry in stations}
        pairs = {}
        for index, conn in enumerate(connections):
            missing_keys = [k for k in ("source", "dest", "distance", "line") if k not in conn]
            if missing_keys:
                self._error(f"Connection #{index} lacks fields {missing_keys}")
                continue
            src, dst = conn["source"], conn["dest"]
            if src not in known:
                self._error(f"Connection #{index} references unknown station '{src}'")
            if dst not in known:
                self._error(f"Connection #{index} references unknown station '{dst}'")
            if src == dst:
                self._error(f"Connection #{index} links station '{src}' to itself")
            key = (src, dst, conn["line"])
            if key in pairs:
                self._warning(f"Duplicate connection {src} -> {dst} on {conn['line']}")
            pairs[key] = conn["distance"]

        for (src, dst, line_name), distance in pairs.items():
            reverse = pairs.get((dst, src, line_name))
            if reverse is None:
                self._warning(f"No reverse connection {dst} -> {src} on {line_name}")
            elif reverse != distance:
                self._warning(
                    f"Distance mismatch between {src} and {dst} on {line_name}: "
                    f"{distance} m vs {reverse} m"
                )

        connected = set()
        for src, dst, _ in pairs:
            connected.add(src)
            connected.add(dst)
        for name in known:
            if name is not None and name not in connected:
                self._warning(f"Station '{name}' has no connections")

    def _check_distances(self, connections):
        """Verify that adjacent-station distances are plausible."""
        for index, conn in enumerate(connections):
            if "distance" not in conn:
                continue
            try:
                distance = int(conn["distance"])
            except (TypeError, ValueError):
                self._error(f"Connection #{index} has a non-numeric distance {conn['distance']!r}")
                continue
            if distance < MIN_ADJACENT_DISTANCE_M:
                self._error(f"Connection #{index} has non-positive distance {distance} m")
            elif distance > MAX_ADJACENT_DISTANCE_M:
                self._warning(
                    f"Connection {conn.get('source')} -> {conn.get('dest')} distance "
                    f"{distance} m looks implausibly large"
                )
