"""Data integrity checks for the subway network."""

from models import Graph  # noqa: F401  (kept for type reference)

MAIN_LINES = [
    "Line 1", "Line 2", "Line 4", "Line 5", "Line 6", "Line 8", "Line 10",
    "Line 13", "Line 14", "Line 15", "Changping Line", "Yizhuang Line",
    "Fangshan Line", "Airport Line",
]

MIN_DISTANCE_M = 100
MAX_DISTANCE_M = 20000


class IntegrityReport:
    """Collects errors and warnings found during integrity checks."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    @property
    def ok(self):
        """True if no errors were found (warnings are allowed)."""
        return not self.errors

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def format(self):
        """Return a human-readable report."""
        lines = ["Data integrity check"]
        for key, value in self.stats.items():
            lines.append(f"  {key}: {value}")
        lines.append(f"  errors: {len(self.errors)}")
        lines.append(f"  warnings: {len(self.warnings)}")
        for message in self.errors:
            lines.append(f"  [ERROR] {message}")
        for message in self.warnings:
            lines.append(f"  [WARN] {message}")
        lines.append("Result: PASSED" if self.ok else "Result: FAILED")
        return "\n".join(lines)


def check_integrity(network):
    """Run coverage, connection and distance checks on a ``SubwayNetwork``.

    Returns:
        IntegrityReport: The collected findings.
    """
    report = IntegrityReport()
    graph = network.graph
    all_edges = graph.edges()
    names = network.station_names()
    lines_present = set(network.line_names())

    report.stats = {
        "stations": len(names),
        "connections": len(all_edges),
        "lines": len(lines_present),
    }

    # Coverage of main lines
    if not names:
        report.error("Network contains no stations")
    for line in MAIN_LINES:
        if line not in lines_present:
            report.error(f"Main line '{line}' is missing from the network")
        elif len(network.stations_on_line(line)) < 2:
            report.warn(f"Main line '{line}' has fewer than two stations")

    # Connectivity of stations
    incoming = {e.dest for e in all_edges}
    for name in names:
        number = network.number_of(name)
        if not graph.adj(number) and number not in incoming:
            report.warn(f"Station '{name}' has no connections")

    # Connection and distance checks
    mismatched_line_reported = set()
    for edge in all_edges:
        src_name = network.name_of(edge.source)
        dst_name = network.name_of(edge.dest)
        if edge.source == edge.dest:
            report.error(f"Self-loop connection at station '{src_name}'")
            continue
        if edge.distance <= 0:
            report.error(f"Non-positive distance between '{src_name}' and '{dst_name}'")
        elif not MIN_DISTANCE_M <= edge.distance <= MAX_DISTANCE_M:
            report.warn(
                f"Distance {edge.distance} m between '{src_name}' and '{dst_name}' "
                f"on '{edge.line}' is outside the expected range"
            )
        reverse = graph.edges_between(edge.dest, edge.source)
        if not any(r.line == edge.line and r.distance == edge.distance for r in reverse):
            report.warn(
                f"Connection '{src_name}' -> '{dst_name}' on '{edge.line}' "
                f"has no matching reverse connection"
            )
        key = (edge.line, src_name, dst_name)
        for name in (src_name, dst_name):
            if edge.line not in network.get_lines(name) and key not in mismatched_line_reported:
                mismatched_line_reported.add(key)
                report.warn(f"Station '{name}' is not registered on line '{edge.line}'")

    # Raw dataset consistency
    listed = {}
    for conn in network.raw_connections:
        key = (conn["source"], conn["dest"], conn["line"])
        if key in listed and listed[key] != conn["distance"]:
            report.error(
                f"Conflicting distances listed for '{conn['source']}' -> '{conn['dest']}' "
                f"on '{conn['line']}'"
            )
        listed[key] = conn["distance"]
    for (src, dst, line), distance in listed.items():
        reverse_key = (dst, src, line)
        if reverse_key in listed and listed[reverse_key] != distance:
            report.warn(
                f"Distances differ between directions of '{src}' <-> '{dst}' on '{line}'"
            )

    return report
