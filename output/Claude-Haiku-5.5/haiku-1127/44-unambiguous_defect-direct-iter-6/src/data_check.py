"""Data integrity checks for the subway network.

Checks cover:
    * coverage of main lines and representative stations;
    * connection integrity (endpoints, line consistency, duplicates);
    * distance accuracy (positive, plausible values);
    * network connectivity.
"""

REQUIRED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan", "Dongdan"],
    "Line 2": ["Xizhimen", "Dongzhimen"],
    "Line 4": ["Beijing Zoo"],
    "Line 5": ["Songjiazhuang"],
}

MAX_PLAUSIBLE_DISTANCE_M = 6000
MIN_PLAUSIBLE_DISTANCE_M = 50


class _UnionFind:
    """Minimal disjoint-set structure used for connectivity checks."""

    def __init__(self, items):
        self._parent = {item: item for item in items}

    def find(self, item):
        while self._parent[item] != item:
            self._parent[item] = self._parent[self._parent[item]]
            item = self._parent[item]
        return item

    def union(self, a, b):
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_b] = root_a

    def component_count(self):
        return len({self.find(item) for item in self._parent})


def run_integrity_checks(network):
    """Run all integrity checks on a ``SubwayNetwork``.

    Returns:
        A dictionary with keys ``errors``, ``warnings`` (lists of strings),
        ``station_count`` and ``connection_count``.
    """
    data = network.to_dict()
    errors = []
    warnings = []

    stations = data["stations"]
    connections = data["connections"]
    station_names = {s["name"] for s in stations}
    station_lines = {s["name"]: set(s["lines"]) for s in stations}
    connection_lines = {c["line"] for c in connections}

    # 1. Coverage of main lines and representative stations.
    declared_lines = set()
    for lines in station_lines.values():
        declared_lines.update(lines)
    for line in REQUIRED_LINES:
        if line not in connection_lines and line not in declared_lines:
            warnings.append(f"Required line '{line}' is not present in the dataset")
    for line, representatives in REPRESENTATIVE_STATIONS.items():
        for station in representatives:
            if station not in station_names:
                warnings.append(f"Representative station '{station}' of {line} is missing")

    # 2. Station data.
    for station in stations:
        if not station["lines"]:
            errors.append(f"Station '{station['name']}' has no line affiliation")

    # 3. Connection integrity and distance accuracy.
    seen = set()
    union = _UnionFind(station_names)
    used_lines = set()
    for index, conn in enumerate(connections, 1):
        source, dest = conn["source"], conn["dest"]
        line, distance = conn["line"], conn["distance"]
        label = f"Connection #{index} ({source} - {dest}, {line})"

        if source not in station_names or dest not in station_names:
            errors.append(f"{label}: endpoint station is not in the station list")
            continue
        if source == dest:
            errors.append(f"{label}: station connects to itself")
            continue

        if isinstance(distance, bool) or not isinstance(distance, int) or distance <= 0:
            errors.append(f"{label}: distance must be a positive integer (meters)")
        elif distance > MAX_PLAUSIBLE_DISTANCE_M or distance < MIN_PLAUSIBLE_DISTANCE_M:
            warnings.append(f"{label}: distance {distance} m is outside the plausible range")

        for end in (source, dest):
            if line not in station_lines[end]:
                errors.append(f"{label}: line '{line}' is not listed for station '{end}'")

        key = (frozenset((source, dest)), line)
        if key in seen:
            warnings.append(f"{label}: duplicate connection")
        seen.add(key)

        union.union(source, dest)
        used_lines.add(line)

    # 4. Connectivity.
    isolated = [s for s in station_names if not any(
        c["source"] == s or c["dest"] == s for c in connections)]
    for name in sorted(isolated):
        warnings.append(f"Station '{name}' has no connections")
    components = union.component_count()
    if components > 1:
        warnings.append(f"Network has {components} disconnected components")

    for line in sorted(declared_lines - used_lines):
        warnings.append(f"Line '{line}' is declared on stations but has no connections")

    return {
        "errors": errors,
        "warnings": warnings,
        "station_count": len(station_names),
        "connection_count": len(connections),
    }


def format_integrity_report(result):
    """Render the output of ``run_integrity_checks`` as console text."""
    lines = [
        "Data integrity report",
        f"  Stations: {result['station_count']}",
        f"  Connections: {result['connection_count']}",
        f"  Errors: {len(result['errors'])}",
        f"  Warnings: {len(result['warnings'])}",
    ]
    for message in result["errors"]:
        lines.append(f"  [ERROR] {message}")
    for message in result["warnings"]:
        lines.append(f"  [WARN] {message}")
    if not result["errors"] and not result["warnings"]:
        lines.append("  Data passed all checks.")
    elif not result["errors"]:
        lines.append("  Data passed with warnings.")
    else:
        lines.append("  Data failed integrity checks.")
    return "\n".join(lines)
