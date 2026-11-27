"""Path visualization and report export (console text and JSON)."""

import json

from fare_calculator import calculate_estimated_time
from models import PathSummary, Report


def format_distance(meters):
    """Format a distance: meters for short trips, kilometres (plus meters) for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000.0:.2f} km ({meters:.0f} m)"


def build_summary(route):
    """Extract key figures (distance, fare, transfers, estimated time) from a route."""
    minutes = calculate_estimated_time(route.total_distance_meters, route.transfer_count)
    return PathSummary(
        total_distance_meters=route.total_distance_meters,
        total_fare_yuan=route.fare_yuan,
        transfer_count=route.transfer_count,
        estimated_time_minutes=minutes,
    )


def split_segments(route):
    """Group consecutive edges operated by the same line into segments.

    Returns:
        list of (line_name, [station names in that segment]).
    """
    if not route.edges:
        return []
    names = route.station_sequence
    segments = []
    current_line = route.edges[0].line
    seg_stations = [names[0]]
    for i, edge in enumerate(route.edges):
        if edge.line != current_line:
            segments.append((current_line, seg_stations))
            current_line = edge.line
            seg_stations = [names[i]]
        seg_stations.append(names[i + 1])
    segments.append((current_line, seg_stations))
    return segments


def render_route_text(route):
    """Render a route as console-formatted text."""
    summary = build_summary(route)
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"From: {route.start_station}")
    out.append(f"To:   {route.end_station}")
    out.append(f"Mode: {route.mode}")
    if route.max_transfers is not None:
        out.append(f"Max transfers: {route.max_transfers}")
    if route.line_preference:
        out.append(f"Line preference: {route.line_preference}")
    out.append("-" * 60)
    out.append("Station sequence (end -> start):")
    out.append("  " + " -> ".join(reversed(route.station_sequence)))
    out.append("")
    out.append("Route segments:")
    segments = split_segments(route)
    if not segments:
        out.append("  (no travel required)")
    for line, stations in segments:
        out.append(f"  [{line}] {' -> '.join(stations)} ({len(stations) - 1} stops)")
    out.append("")
    out.append("Transfers:")
    if not route.transfers:
        out.append("  None")
    for transfer in route.transfers:
        out.append(f"  - {transfer.station_name}: {' -> '.join(transfer.involved_lines)}")
    out.append("")
    out.append("-" * 60)
    out.append(f"Total distance: {format_distance(summary.total_distance_meters)}")
    out.append(f"Transfers: {summary.transfer_count}")
    out.append(f"Lines involved: {', '.join(route.lines) if route.lines else 'None'}")
    out.append(f"Estimated time: {summary.estimated_time_minutes:.1f} min")
    out.append(f"Fare: {summary.total_fare_yuan} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def render_route_dict(route):
    """Render a route as a JSON-serializable dictionary."""
    summary = build_summary(route)
    return {
        "query": {
            "start_station": route.start_station,
            "end_station": route.end_station,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": list(route.station_sequence),
        "distance": {
            "meters": round(summary.total_distance_meters, 1),
            "kilometers": round(summary.total_distance_meters / 1000.0, 3),
        },
        "fare_yuan": summary.total_fare_yuan,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 1),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station_name, "involved_lines": list(t.involved_lines)}
            for t in route.transfers
        ],
        "involved_lines": list(route.lines),
    }


def build_report(routes, fmt):
    """Build a report covering one or more routes in the requested format.

    Args:
        routes: list of Route objects.
        fmt: 'text' or 'json'.
    """
    if fmt == "json":
        content = json.dumps([render_route_dict(r) for r in routes], ensure_ascii=False, indent=2)
    elif fmt == "text":
        content = "\n\n".join(render_route_text(r) for r in routes)
    else:
        raise ValueError(f"unsupported format '{fmt}'")
    return Report(format=fmt, content=content)


def write_report(report, path):
    """Write a report to a file (overwriting) and record the path in the report."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report.content)
        if report.content and not report.content.endswith("\n"):
            fh.write("\n")
    report.output_file_path = path
    return report
