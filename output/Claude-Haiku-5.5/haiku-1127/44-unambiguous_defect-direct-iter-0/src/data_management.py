"""Data integrity checks for the subway network.

Checks coverage of the main lines, connection integrity and distance
accuracy. Results are returned as a dictionary with ``errors``,
``warnings`` and ``stats`` entries.
"""


# Main lines the dataset is expected to cover.
REQUIRED_MAIN_LINES = (
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

# Representative hub stations that should be present in the network.
REPRESENTATIVE_STATIONS = (
    "西单",
    "国贸",
    "西直门",
    "东直门",
    "天安门东",
)

# Plausible range for a single inter-station distance in meters.
MIN_PLAUSIBLE_DISTANCE_M = 1
MAX_PLAUSIBLE_DISTANCE_M = 10000


def _connected_components(graph):
    """Return a list of connected components, each a list of station numbers."""
    seen = set()
    components = []
    for start in graph.vertices():
        if start in seen:
            continue
        component = []
        stack = [start]
        seen.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for edge in graph.adj.get(current, []):
                nxt = edge.other(current)
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(component)
    return components


def check_data_integrity(network):
    """Run all integrity checks on a SubwayNetwork.

    Returns a dict::

        {"errors": [str], "warnings": [str],
         "stats": {"stations": int, "connections": int,
                   "lines": int, "transfer_stations": int}}
    """
    errors = []
    warnings = []
    graph = network.graph
    lines_present = set(network.line_names())

    # 1. Coverage of main lines and representative stations.
    for line in REQUIRED_MAIN_LINES:
        if line not in lines_present:
            warnings.append(f"coverage: main line '{line}' is not present in the data")
        elif len(network.get_line_stations(line)) < 2:
            warnings.append(f"coverage: main line '{line}' has fewer than two stations")
    for station in REPRESENTATIVE_STATIONS:
        if network.resolve_station(station) is None:
            warnings.append(f"coverage: representative station '{station}' is missing")

    # 2. Station-level checks.
    for name in network.station_names():
        if not graph.get_station_lines(name):
            warnings.append(f"station '{name}' has no line information")

    # 3. Connection and distance checks.
    seen_pairs = {}
    for edge in graph.edges():
        src_name = network.get_station_name(edge.source)
        dst_name = network.get_station_name(edge.dest)
        label = f"connection '{src_name}' - '{dst_name}' ({edge.line})"

        if not edge.line:
            errors.append(f"{label}: missing line name")
        if not isinstance(edge.distance, int) or edge.distance <= 0:
            errors.append(f"{label}: distance must be a positive integer, got {edge.distance!r}")
        elif edge.distance < MIN_PLAUSIBLE_DISTANCE_M or edge.distance > MAX_PLAUSIBLE_DISTANCE_M:
            warnings.append(
                f"{label}: distance {edge.distance} m is outside the plausible range "
                f"({MIN_PLAUSIBLE_DISTANCE_M}-{MAX_PLAUSIBLE_DISTANCE_M} m)"
            )

        for name in (src_name, dst_name):
            if edge.line not in graph.get_station_lines(name):
                warnings.append(
                    f"connection consistency: '{name}' is not listed as serving '{edge.line}'"
                )

        key = (min(edge.source, edge.dest), max(edge.source, edge.dest), edge.line)
        if key in seen_pairs:
            warnings.append(f"duplicate connection: {label}")
        else:
            seen_pairs[key] = edge

    # 4. Connectivity of the network.
    components = _connected_components(graph)
    if len(components) > 1:
        for component in components:
            names = sorted(network.get_station_name(num) for num in component)
            preview = ", ".join(names[:5])
            warnings.append(
                f"connectivity: a group of {len(names)} station(s) is not connected "
                f"to the rest of the network ({preview})"
            )

    # 5. Problems detected while loading the raw data.
    warnings.extend(f"loading: {message}" for message in network.build_warnings)

    stats = {
        "stations": graph.num_vertices,
        "connections": graph.num_edges,
        "lines": len(lines_present),
        "transfer_stations": len(network.transfer_stations()),
    }
    return {"errors": errors, "warnings": warnings, "stats": stats}


def print_integrity_report(result, out=print):
    """Print the result of check_data_integrity in a readable form."""
    stats = result["stats"]
    out("Data integrity check")
    out(f"  Stations: {stats['stations']}")
    out(f"  Connections: {stats['connections']}")
    out(f"  Lines: {stats['lines']}")
    out(f"  Transfer stations: {stats['transfer_stations']}")
    for message in result["errors"]:
        out(f"ERROR: {message}")
    for message in result["warnings"]:
        out(f"WARNING: {message}")
    if result["errors"]:
        out(f"Result: FAILED ({len(result['errors'])} error(s), "
            f"{len(result['warnings'])} warning(s))")
    else:
        out(f"Result: PASSED ({len(result['warnings'])} warning(s))")
