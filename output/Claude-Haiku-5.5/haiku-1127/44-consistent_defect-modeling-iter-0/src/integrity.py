"""Data integrity checks for the subway dataset (triggered by --check_data)."""

from dataclasses import dataclass, field

# Lines that must be present in the dataset (PRD section 4.1).
EXPECTED_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

# Representative stations of main lines used for coverage validation.
REPRESENTATIVE_STATIONS = {
    "Line 1": ["Pingguoyuan"],
    "Line 2": ["Xizhimen", "Jianguomen"],
    "Line 4": ["Beijing Zoo"],
    "Line 5": ["Songjiazhuang"],
    "Line 10": ["Shuangjing"],
}

# Plausible distance range between adjacent stations (meters).
MIN_DISTANCE_METERS = 50
MAX_DISTANCE_METERS = 20000


@dataclass
class DataIntegrityCheck:
    """Outcome of the integrity check."""

    coverage_valid: bool = True
    connections_valid: bool = True
    distances_valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def all_valid(self):
        return self.coverage_valid and self.connections_valid and self.distances_valid

    def summary_text(self):
        lines = ["Data integrity check"]
        lines.append(f"  Coverage:    {'OK' if self.coverage_valid else 'FAILED'}")
        lines.append(f"  Connections: {'OK' if self.connections_valid else 'FAILED'}")
        lines.append(f"  Distances:   {'OK' if self.distances_valid else 'FAILED'}")
        for msg in self.errors:
            lines.append(f"  ERROR: {msg}")
        for msg in self.warnings:
            lines.append(f"  WARNING: {msg}")
        lines.append(f"Result: {'PASSED' if self.all_valid else 'FAILED'}")
        return "\n".join(lines)


def run_integrity_check(network):
    """Validate station coverage, connection relationships and distance accuracy."""
    result = DataIntegrityCheck()
    data = network.raw_data
    stations = data["stations"]
    connections = data["connections"]
    station_names = {str(st["name"]) for st in stations}

    # --- Coverage -----------------------------------------------------
    present_lines = set(network.line_names())
    for line in EXPECTED_LINES:
        if line not in present_lines:
            result.coverage_valid = False
            result.errors.append(f"expected line '{line}' is missing")
    for line, reps in REPRESENTATIVE_STATIONS.items():
        for name in reps:
            if name not in network.station_to_number:
                result.coverage_valid = False
                result.errors.append(f"representative station '{name}' of {line} is missing")
    for st in stations:
        if not st.get("lines"):
            result.warnings.append(f"station '{st['name']}' has no line assignment")

    # --- Connections --------------------------------------------------
    seen = set()
    by_pair = {}
    for conn in connections:
        src, dst, line = conn.get("source"), conn.get("dest"), conn.get("line")
        if src not in station_names or dst not in station_names:
            result.connections_valid = False
            result.errors.append(f"connection {src} -> {dst} references an unknown station")
            continue
        if src == dst:
            result.connections_valid = False
            result.errors.append(f"self-loop connection at '{src}'")
        key = (src, dst, line)
        if key in seen:
            result.connections_valid = False
            result.errors.append(f"duplicate connection {src} -> {dst} on {line}")
        seen.add(key)
        by_pair.setdefault((src, dst), conn)

    for (src, dst), conn in by_pair.items():
        reverse = by_pair.get((dst, src))
        if reverse is None:
            result.warnings.append(f"no reverse connection for {src} -> {dst}")
        elif reverse.get("distance") != conn.get("distance"):
            result.warnings.append(
                f"asymmetric distance between '{src}' and '{dst}': "
                f"{conn.get('distance')} vs {reverse.get('distance')}")

    # --- Distances ----------------------------------------------------
    for conn in connections:
        dist = conn.get("distance")
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist <= 0:
            result.distances_valid = False
            result.errors.append(f"invalid distance {dist!r} on {conn.get('source')} -> {conn.get('dest')}")
        elif not (MIN_DISTANCE_METERS <= dist <= MAX_DISTANCE_METERS):
            result.distances_valid = False
            result.errors.append(
                f"implausible distance {dist} m on {conn.get('source')} -> {conn.get('dest')}")

    return result
