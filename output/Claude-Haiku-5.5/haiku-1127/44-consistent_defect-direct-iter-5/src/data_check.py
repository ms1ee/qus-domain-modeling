"""Data integrity checks for the subway network (used by ``--check_data``)."""

from network import SubwayNetwork  # noqa: F401  (documented type of the argument)

ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"

# Main lines expected to be present in the dataset.
MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Distances above this value (meters) between adjacent stations are suspicious.
MAX_PLAUSIBLE_DISTANCE_M = 5000


def run_integrity_check(network):
    """Run coverage, connection and distance checks on the network.

    Returns:
        A list of ``(level, message)`` tuples where level is one of
        ``ERROR``, ``WARNING`` or ``INFO``.
    """
    issues = []
    graph = network.graph

    # 1. Station data coverage -------------------------------------------
    if not network.station_names():
        issues.append((ERROR, "No stations found in the dataset"))
    available_lines = set(network.line_names())
    for line in MAIN_LINES:
        if line not in available_lines:
            issues.append((WARNING, f"Main line '{line}' is not represented in the dataset"))
        elif len(network.stations_on_line(line)) < 2:
            issues.append((ERROR, f"Main line '{line}' has fewer than two stations"))

    for name in network.station_names():
        if not network.lines_of(name):
            issues.append((WARNING, f"Station '{name}' is not assigned to any line"))

    # 2. Connection integrity ---------------------------------------------
    seen = set()
    touched = set()
    one_way = 0
    for edge in graph.edges():
        source_name = network.name_of(edge.source)
        dest_name = network.name_of(edge.dest)
        touched.add(edge.source)
        touched.add(edge.dest)

        key = (edge.source, edge.dest, edge.line)
        if key in seen:
            issues.append((ERROR, f"Duplicate connection {source_name} -> {dest_name} "
                                  f"on '{edge.line}'"))
        seen.add(key)

        for name in (source_name, dest_name):
            if edge.line not in network.lines_of(name):
                issues.append((WARNING, f"Connection {source_name} -> {dest_name} uses "
                                        f"'{edge.line}', which is not listed for '{name}'"))

        if not graph.get_edges_between(edge.dest, edge.source):
            one_way += 1

        # 3. Distance accuracy --------------------------------------------
        if edge.distance <= 0:
            issues.append((ERROR, f"Connection {source_name} -> {dest_name} has non-positive "
                                  f"distance {edge.distance}"))
        elif edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
            issues.append((WARNING, f"Connection {source_name} -> {dest_name} has a "
                                    f"suspiciously long distance of {edge.distance} m"))

    for number in network.graph.vertices():
        if number not in touched:
            issues.append((WARNING, f"Station '{network.name_of(number)}' has no connections"))

    if one_way:
        issues.append((INFO, f"{one_way} connection(s) exist only in one direction"))

    if not issues:
        issues.append((INFO, "No integrity problems found"))
    return issues


def has_errors(issues) -> bool:
    """Return True if any issue has the ERROR level."""
    return any(level == ERROR for level, _ in issues)
