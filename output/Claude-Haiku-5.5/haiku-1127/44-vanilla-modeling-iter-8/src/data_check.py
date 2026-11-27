"""Data integrity checks for the subway network (used by ``--check_data``)."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

# Main lines that must be covered by the dataset.
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]
MIN_STATIONS_PER_LINE = 2
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 8000


@dataclass
class DataIntegrityCheck:
    """Result of a data integrity check.

    Attributes:
        passed: True if no errors were found (warnings do not fail the check).
        messages: Human readable messages prefixed with ERROR, WARNING or INFO.
        checkedAt: ISO timestamp of the check.
    """

    passed: bool
    messages: list = field(default_factory=list)
    checkedAt: str = ""

    def to_text(self):
        status = "PASSED" if self.passed else "FAILED"
        lines = ["Data integrity check %s at %s" % (status, self.checkedAt)]
        lines.extend("  " + message for message in self.messages)
        return "\n".join(lines)


def _unreachable_stations(network):
    """Return names of stations not reachable from the first station."""
    numbers = network.graph.vertices()
    if not numbers:
        return []
    start = numbers[0]
    seen = {start}
    queue = deque([start])
    while queue:
        vertex = queue.popleft()
        for edge in network.graph.adjacent(vertex):
            if edge.dest not in seen:
                seen.add(edge.dest)
                queue.append(edge.dest)
    return [network.get_name(n) for n in numbers if n not in seen]


def run_integrity_check(network):
    """Run all data integrity checks on a ``SubwayNetwork``.

    Checks performed:
        * station coverage of the main lines,
        * connection integrity (declared stations, lines serving endpoints,
          no self loops, no duplicate connections),
        * connectivity of the graph,
        * distance accuracy (positive integer meters, plausible range).

    Returns:
        DataIntegrityCheck: the aggregated result.
    """
    errors = []
    warnings = []
    infos = []

    # 1. Station data coverage.
    covered = set(network.line_names())
    for line in MAIN_LINES:
        if line not in covered:
            errors.append("Main line '%s' is not covered by any station" % line)
        else:
            count = len(network.line_stations(line))
            if count < MIN_STATIONS_PER_LINE:
                errors.append("Main line '%s' has only %d station(s)" % (line, count))
            else:
                infos.append("Main line '%s' covers %d stations" % (line, count))
    for name in network.station_names():
        if not network.lines_of(name):
            warnings.append("Station '%s' does not belong to any line" % name)
    for name in network.raw_undeclared_stations():
        errors.append("Station '%s' is referenced by a connection but not declared" % name)

    # 2. Connection integrity.
    declared = set(network.station_names())
    seen_pairs = set()
    for index, conn in enumerate(network.connections(), start=1):
        source, dest, line = conn["source"], conn["dest"], conn["line"]
        label = "Connection %d (%s - %s, %s)" % (index, source, dest, line)
        if source not in declared:
            errors.append("%s: unknown source station" % label)
        if dest not in declared:
            errors.append("%s: unknown destination station" % label)
        if source == dest:
            errors.append("%s: self loop is not allowed" % label)
        for endpoint in (source, dest):
            if endpoint in declared and line not in network.lines_of(endpoint):
                errors.append("%s: line '%s' does not serve station '%s'" % (label, line, endpoint))
        pair_key = (frozenset((source, dest)), line)
        if pair_key in seen_pairs:
            warnings.append("%s: duplicate connection" % label)
        seen_pairs.add(pair_key)

        # 3. Distance accuracy.
        distance = conn["distance"]
        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            errors.append("%s: distance must be a positive integer in meters, got %r" % (label, distance))
        elif distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
            warnings.append("%s: distance %d m is outside the plausible range [%d, %d]"
                            % (label, distance, MIN_PLAUSIBLE_DISTANCE_M, MAX_PLAUSIBLE_DISTANCE_M))

    # 4. Connectivity.
    unreachable = _unreachable_stations(network)
    if unreachable:
        warnings.append("%d station(s) are not connected to the main network: %s"
                        % (len(unreachable), ", ".join(unreachable)))
    else:
        infos.append("All %d stations are connected" % len(network.station_names()))

    passed = not errors
    messages = ["ERROR: " + m for m in errors] + ["WARNING: " + m for m in warnings] + ["INFO: " + m for m in infos]
    if passed:
        messages.append("INFO: No integrity errors found")
    return DataIntegrityCheck(
        passed=passed,
        messages=messages,
        checkedAt=datetime.now().isoformat(timespec="seconds"),
    )
