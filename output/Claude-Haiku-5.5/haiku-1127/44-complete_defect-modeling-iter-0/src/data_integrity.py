"""Data integrity checks for the subway network (triggered by ``--check_data``).

Three groups of checks are performed:
* coverage     - main lines have stations and representative stations exist;
* connectivity - connection endpoints exist, no self-loops, graph connectivity;
* distance     - distances are valid positive numbers and plausible in range.
"""

from collections import deque
from dataclasses import dataclass, field

from network import clean_name, is_valid_distance, LOAD_CATEGORY_CONNECTIVITY, LOAD_CATEGORY_DISTANCE

MAIN_LINES = (
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
)

# Representative stations that must be present for coverage to pass.
REPRESENTATIVE_STATIONS = {
    "Line 1": ("Pingguoyuan", "Tiananmen West"),
    "Line 2": ("Xizhimen", "Dongzhimen"),
    "Line 4": ("Beijing South Railway Station",),
    "Line 5": ("Songjiazhuang",),
    "Line 13": ("Xi'erqi",),
}

# Distances outside this range (meters) are reported as suspicious.
MIN_PLAUSIBLE_DISTANCE_M = 100
MAX_PLAUSIBLE_DISTANCE_M = 5000


@dataclass
class DataIntegrityCheck:
    """Outcome of the data integrity checks."""

    coverage_passed: bool = True
    connectivity_passed: bool = True
    distance_accuracy_passed: bool = True
    messages: list = field(default_factory=list)

    @property
    def passed(self):
        """True if every check group passed."""
        return self.coverage_passed and self.connectivity_passed and self.distance_accuracy_passed


def _check_coverage(network, result):
    """Verify that main lines and representative stations are covered."""
    failed = False
    for line in MAIN_LINES:
        if not network.stations_on_line(line):
            failed = True
            result.messages.append("[coverage] Main line '{}' has no stations".format(line))
    for line, stations in REPRESENTATIVE_STATIONS.items():
        for station in stations:
            if network.standardize_station_name(station) is None:
                failed = True
                result.messages.append(
                    "[coverage] Representative station '{}' of {} is missing".format(station, line)
                )
    if failed:
        result.coverage_passed = False
    else:
        result.messages.append("[coverage] Station coverage check passed")


def _check_connectivity(network, raw, result):
    """Verify connection endpoints, self-loops, isolated stations and connectivity."""
    failed = False
    raw_stations = set()
    for item in raw.get("stations") or []:
        if isinstance(item, dict):
            name = clean_name(item.get("name"))
            if name:
                raw_stations.add(name)

    for conn in raw.get("connections") or []:
        if not isinstance(conn, dict):
            failed = True
            result.messages.append("[connectivity] Malformed connection record: {!r}".format(conn))
            continue
        src = clean_name(conn.get("source"))
        dst = clean_name(conn.get("dest"))
        if src not in raw_stations or dst not in raw_stations:
            failed = True
            result.messages.append(
                "[connectivity] Connection '{}' - '{}' references a station missing from the station list".format(src, dst)
            )
        if src and src == dst:
            failed = True
            result.messages.append("[connectivity] Self-loop connection at '{}'".format(src))

    for category, message in network.load_warnings:
        if category == LOAD_CATEGORY_CONNECTIVITY:
            failed = True
            result.messages.append("[connectivity] " + message)

    graph = network.graph
    vertices = graph.vertices()
    isolated = [network.number_to_station[v] for v in vertices if not graph.adj(v)]
    if isolated:
        failed = True
        result.messages.append("[connectivity] Isolated stations without connections: {}".format(", ".join(isolated)))

    seen = set()
    component_sizes = []
    for start in vertices:
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for edge in graph.adj(current):
                neighbor = edge.other(current)
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        component_sizes.append(size)
    if len(component_sizes) > 1:
        failed = True
        result.messages.append(
            "[connectivity] Network is split into {} disconnected components (sizes: {})".format(
                len(component_sizes), ", ".join(str(s) for s in component_sizes))
        )

    if failed:
        result.connectivity_passed = False
    else:
        result.messages.append("[connectivity] Connection integrity check passed")


def _check_distances(network, raw, result):
    """Verify distance values are valid and plausible."""
    failed = False
    for conn in raw.get("connections") or []:
        if not isinstance(conn, dict):
            continue
        distance = conn.get("distance")
        label = "{} - {}".format(clean_name(conn.get("source")), clean_name(conn.get("dest")))
        if not is_valid_distance(distance):
            failed = True
            result.messages.append("[distance] Invalid distance {!r} for {}".format(distance, label))
        elif distance < MIN_PLAUSIBLE_DISTANCE_M or distance > MAX_PLAUSIBLE_DISTANCE_M:
            result.messages.append(
                "[distance] Suspicious distance {} m for {} (outside {}-{} m)".format(
                    distance, label, MIN_PLAUSIBLE_DISTANCE_M, MAX_PLAUSIBLE_DISTANCE_M)
            )

    for category, message in network.load_warnings:
        if category == LOAD_CATEGORY_DISTANCE:
            failed = True
            result.messages.append("[distance] " + message)

    if failed:
        result.distance_accuracy_passed = False
    else:
        result.messages.append("[distance] Distance accuracy check passed")


def run_integrity_check(network):
    """Run all integrity checks on a ``SubwayNetwork`` and return the result."""
    result = DataIntegrityCheck()
    raw = network.raw_data
    _check_coverage(network, result)
    _check_connectivity(network, raw, result)
    _check_distances(network, raw, result)
    if result.passed:
        result.messages.append("All data integrity checks passed")
    return result
