"""Data integrity checks for the subway network (used by ``--check_data``)."""

from dataclasses import dataclass, field

from network import REQUIRED_MAIN_LINES

MAX_REASONABLE_DISTANCE_M = 10000.0
DISTANCE_TOLERANCE_M = 1e-6


@dataclass
class IntegrityReport:
    """Outcome of the data integrity checks."""

    passed: bool = True
    coverage_check: bool = True
    connection_check: bool = True
    distance_check: bool = True
    messages: list = field(default_factory=list)


def check_integrity(network):
    """Run coverage, connection and distance checks on a ``SubwayNetwork``.

    Returns:
        IntegrityReport: the detailed result of the checks.
    """
    report = IntegrityReport()
    graph = network.graph
    names = network.station_names()

    # --- Coverage: stations and main lines -----------------------------
    if not names:
        report.coverage_check = False
        report.messages.append("Coverage: no stations loaded.")

    line_counts = {}
    for name in names:
        lines = network.lines_of_station(name)
        if not lines:
            report.coverage_check = False
            report.messages.append(f"Coverage: station '{name}' is not assigned to any line.")
        for line in lines:
            line_counts[line] = line_counts.get(line, 0) + 1

    for required in REQUIRED_MAIN_LINES:
        official = network.normalize_line(required)
        if official is None or line_counts.get(official, 0) == 0:
            report.coverage_check = False
            report.messages.append(f"Coverage: main line '{required}' is missing from the network.")

    for warning in network.load_warnings:
        report.connection_check = False
        report.messages.append(f"Connection: {warning}")

    # --- Connections ----------------------------------------------------
    incoming = set()
    for node in graph.nodes():
        for edge in graph.adj(node):
            incoming.add(edge.dest)

    for node in graph.nodes():
        station = network.get_station_name(node)
        if not graph.adj(node):
            report.connection_check = False
            report.messages.append(f"Connection: station '{station}' has no outgoing connection.")
        if node not in incoming:
            report.connection_check = False
            report.messages.append(f"Connection: station '{station}' has no incoming connection.")

    for node in graph.nodes():
        source_name = network.get_station_name(node)
        for edge in graph.adj(node):
            dest_name = network.get_station_name(edge.dest)

            if edge.distance < 0 or edge.distance > MAX_REASONABLE_DISTANCE_M:
                report.distance_check = False
                report.messages.append(
                    f"Distance: {source_name} -> {dest_name} has an implausible distance "
                    f"of {edge.distance} m.")

            reverse_edges = graph.get_edges(edge.dest, edge.source)
            if not reverse_edges:
                report.connection_check = False
                report.messages.append(
                    f"Connection: missing reverse direction {dest_name} -> {source_name}.")
            for reverse in reverse_edges:
                if abs(reverse.distance - edge.distance) > DISTANCE_TOLERANCE_M:
                    report.distance_check = False
                    report.messages.append(
                        f"Distance: {source_name} <-> {dest_name} has inconsistent distances "
                        f"({edge.distance} m vs {reverse.distance} m).")

            served_source = network.lines_of_station(source_name)
            served_dest = network.lines_of_station(dest_name)
            if edge.line not in served_source or edge.line not in served_dest:
                report.connection_check = False
                report.messages.append(
                    f"Connection: line '{edge.line}' does not serve both {source_name} "
                    f"and {dest_name}.")

    report.passed = report.coverage_check and report.connection_check and report.distance_check
    if report.passed:
        report.messages.append("All integrity checks passed.")
    return report


def format_integrity_report(report):
    """Format an ``IntegrityReport`` as console text."""
    lines = [
        "Data integrity check",
        f"  Coverage check : {'PASS' if report.coverage_check else 'FAIL'}",
        f"  Connection check: {'PASS' if report.connection_check else 'FAIL'}",
        f"  Distance check : {'PASS' if report.distance_check else 'FAIL'}",
        f"  Overall        : {'PASSED' if report.passed else 'FAILED'}",
    ]
    if report.messages:
        lines.append("Messages:")
        lines.extend(f"  - {message}" for message in report.messages)
    return "\n".join(lines)
