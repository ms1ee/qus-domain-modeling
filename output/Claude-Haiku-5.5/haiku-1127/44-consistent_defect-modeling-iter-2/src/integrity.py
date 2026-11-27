"""Data integrity checks for the subway dataset (used by --check_data)."""

import re
from typing import List, Set, Tuple

# Representative main lines that must be present in the dataset.
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

MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 10000

_LINE_ALIASES = (
    ("changping", "changping"),
    ("昌平", "changping"),
    ("yizhuang", "yizhuang"),
    ("亦庄", "yizhuang"),
    ("fangshan", "fangshan"),
    ("房山", "fangshan"),
    ("airport", "airport"),
    ("机场", "airport"),
)


def line_key(name: str) -> str:
    """Return a canonical key identifying a line regardless of naming style.

    "Line 1", "1号线" and "1" all map to "line-1"; "Changping Line" and
    "昌平线" map to "changping".
    """
    text = str(name).strip().lower()
    digits = re.search(r"\d+", text)
    if digits:
        return f"line-{int(digits.group())}"
    for needle, key in _LINE_ALIASES:
        if needle in text:
            return key
    return re.sub(r"\s+", "", text)


class DataIntegrityChecker:
    """Runs coverage, connection and distance checks on a SubwayNetwork.

    Attributes:
        coverageCheckPassed: Result of the station/line coverage check.
        connectionCheckPassed: Result of the connection integrity check.
        distanceCheckPassed: Result of the distance accuracy check.
    """

    def __init__(self, network) -> None:
        self.network = network
        self.coverageCheckPassed = False
        self.connectionCheckPassed = False
        self.distanceCheckPassed = False
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def run(self) -> bool:
        """Run all checks and return True if every check passed."""
        self.errors = []
        self.warnings = []
        self.check_coverage()
        self.check_connections()
        self.check_distances()
        return self.coverageCheckPassed and self.connectionCheckPassed and self.distanceCheckPassed

    def check_coverage(self) -> bool:
        """Verify that representative main lines and stations are present."""
        problems: List[str] = []
        if not self.network.station_names():
            problems.append("the dataset contains no stations")
        present = {line_key(name) for name in self.network.line_names()}
        for line in MAIN_LINES:
            if line_key(line) not in present:
                problems.append(f"main line '{line}' is not covered by the dataset")
        self.errors.extend(problems)
        self.coverageCheckPassed = not problems
        return self.coverageCheckPassed

    def check_connections(self) -> bool:
        """Verify connection endpoints, self-loops, duplicates and reverse links."""
        problems: List[str] = []
        raw = self.network.raw_data()
        station_names = {st["name"] for st in raw["stations"]}
        declared_lines = {st["name"]: set(st.get("lines", [])) for st in raw["stations"]}
        seen: Set[Tuple[str, str, str]] = set()

        for index, conn in enumerate(raw["connections"]):
            src, dst, line = conn.get("source"), conn.get("dest"), conn.get("line")
            label = f"connection #{index} ({src} -> {dst}, {line})"
            if src == dst:
                problems.append(f"{label}: self-loop")
            if src not in station_names or dst not in station_names:
                self.warnings.append(f"{label}: endpoint is missing from the station list")
            for end in (src, dst):
                if end in declared_lines and line not in declared_lines[end]:
                    self.warnings.append(f"{label}: line not listed for station '{end}'")
            if (src, dst, line) in seen:
                problems.append(f"{label}: duplicate connection")
            seen.add((src, dst, line))

        for src, dst, line in sorted(seen):
            if (dst, src, line) not in seen:
                self.warnings.append(f"no reverse direction for {src} -> {dst} ({line})")

        if not self._is_connected():
            self.warnings.append("the network is not fully connected")

        self.errors.extend(problems)
        self.connectionCheckPassed = not problems
        return self.connectionCheckPassed

    def check_distances(self) -> bool:
        """Verify that every distance is a positive number of plausible size."""
        problems: List[str] = []
        for index, conn in enumerate(self.network.raw_data()["connections"]):
            distance = conn.get("distance")
            label = f"connection #{index} ({conn.get('source')} -> {conn.get('dest')})"
            if isinstance(distance, bool) or not isinstance(distance, (int, float)):
                problems.append(f"{label}: distance is not numeric")
            elif distance <= 0:
                problems.append(f"{label}: distance must be positive")
            elif not (MIN_PLAUSIBLE_DISTANCE_M <= distance <= MAX_PLAUSIBLE_DISTANCE_M):
                self.warnings.append(f"{label}: distance {distance} m is outside the plausible range")
        self.errors.extend(problems)
        self.distanceCheckPassed = not problems
        return self.distanceCheckPassed

    def _is_connected(self) -> bool:
        """Return True if all stations form one weakly connected component."""
        graph = self.network.graph
        vertices = graph.vertices()
        if not vertices:
            return True
        undirected = {v: set() for v in vertices}
        for v in vertices:
            for edge in graph.adjacent(v):
                undirected[v].add(edge.dest)
                undirected[edge.dest].add(v)
        seen = {vertices[0]}
        stack = [vertices[0]]
        while stack:
            current = stack.pop()
            for nxt in undirected[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(vertices)

    def report(self) -> str:
        """Return a human-readable summary of the last run."""

        def status(flag: bool) -> str:
            return "PASS" if flag else "FAIL"

        lines = [
            "Data integrity check report",
            f"  Coverage check:   {status(self.coverageCheckPassed)}",
            f"  Connection check: {status(self.connectionCheckPassed)}",
            f"  Distance check:   {status(self.distanceCheckPassed)}",
        ]
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {msg}" for msg in self.errors)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {msg}" for msg in self.warnings)
        if not self.errors and not self.warnings:
            lines.append("No problems found.")
        overall = self.coverageCheckPassed and self.connectionCheckPassed and self.distanceCheckPassed
        lines.append(f"Overall: {status(overall)}")
        return "\n".join(lines)
