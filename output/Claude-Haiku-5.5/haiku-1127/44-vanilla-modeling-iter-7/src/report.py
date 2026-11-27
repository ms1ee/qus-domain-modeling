"""
Path visualization and export.

Builds Route and PathSummary objects from a path, and renders them as console
text or JSON reports. Reports can be written to a file.
"""

import json
import os

from fare_calculator import Sum_money, calculate_estimated_time
from models import PathSummary, Query, Report, Route, Segment, Transfer


def build_route(graph, station_numbers, edges):
    """Create a Route (names, distance, transfers, lines, time) from a path.

    Args:
        graph: The Graph used for name lookup.
        station_numbers: Ordered station numbers from source to target.
        edges: Edges between consecutive stations (len = len(station_numbers) - 1).
    """
    if not station_numbers:
        raise ValueError("Cannot build a route from an empty path")
    if len(station_numbers) != len(edges) + 1:
        raise ValueError("Path and edge lists are inconsistent")

    names = [graph.name_of(n) for n in station_numbers]
    total = sum(edge.weight for edge in edges)

    involved = []
    transfers = []
    for i, edge in enumerate(edges):
        if edge.line not in involved:
            involved.append(edge.line)
        if i > 0 and edges[i - 1].line != edge.line:
            transfers.append(Transfer(names[i], edges[i - 1].line, edge.line))

    segments = []
    seg_start = 0
    seg_dist = 0.0
    for i, edge in enumerate(edges):
        seg_dist += edge.weight
        is_last = i == len(edges) - 1 or edges[i + 1].line != edge.line
        if is_last:
            segments.append(Segment(edge.line, names[seg_start], names[i + 1], seg_dist))
            seg_start = i + 1
            seg_dist = 0.0

    transfer_count = len(transfers)
    estimated = calculate_estimated_time(total, transfer_count)
    return Route(
        station_sequence=names,
        total_distance_m=total,
        transfer_count=transfer_count,
        involved_lines=involved,
        estimated_time_minutes=estimated,
        transfers=transfers,
        segments=segments,
    )


def build_summary(route):
    """Extract key figures (km, fare, transfers, time) from a route."""
    fare = Sum_money(route.total_distance_m)
    return PathSummary(
        total_distance_km=route.total_distance_m / 1000.0,
        fare_yuan=fare,
        transfer_count=route.transfer_count,
        estimated_time_minutes=route.estimated_time_minutes,
    )


def format_distance(meters):
    """Format a distance: meters for short trips, kilometres for long ones (both shown)."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters:.0f} m ({km:.2f} km)"
    return f"{km:.2f} km ({meters:.0f} m)"


def render_text(route, query, summary):
    """Render a console-formatted report."""
    rule = "=" * 60
    max_t = "unlimited" if query.max_transfers is None else str(query.max_transfers)
    out = [
        rule,
        "Beijing Subway Fare Query Result",
        rule,
        f"Start station   : {query.start_station}",
        f"End station     : {query.end_station}",
        f"Query mode      : {query.mode}",
        f"Max transfers   : {max_t}",
        f"Line preference : {query.line_preference or 'none'}",
        "",
        f"Station sequence ({len(route.station_sequence)} stations):",
    ]
    for index, name in enumerate(route.station_sequence, start=1):
        out.append(f"  {index:>3}. {name}")

    out.append("")
    out.append("Line segments:")
    if route.segments:
        for seg in route.segments:
            out.append(
                f"  [{seg.line}] {seg.from_station} -> {seg.to_station} "
                f"({format_distance(seg.distance_m)})"
            )
    else:
        out.append("  none")

    out.append("")
    out.append("Transfers:")
    if route.transfers:
        for transfer in route.transfers:
            out.append(f"  - {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("  none (direct route)")

    out.extend([
        "",
        "Summary:",
        f"  Total distance : {format_distance(route.total_distance_m)}",
        f"  Transfers      : {summary.transfer_count}",
        f"  Estimated time : {summary.estimated_time_minutes:.1f} minutes",
        f"  Lines involved : {', '.join(route.involved_lines) if route.involved_lines else 'none'}",
        "",
        f"Fare: {summary.fare_yuan} yuan",
        rule,
    ])
    return "\n".join(out)


def render_json(route, query, summary):
    """Render a structured JSON report for programmatic use."""
    payload = {
        "query": {
            "start_station": query.start_station,
            "end_station": query.end_station,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": route.station_sequence,
        "distance": {
            "meters": round(route.total_distance_m, 2),
            "kilometers": round(summary.total_distance_km, 3),
        },
        "fare_yuan": summary.fare_yuan,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "involved_lines": route.involved_lines,
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "from_station": s.from_station,
                "to_station": s.to_station,
                "distance_meters": round(s.distance_m, 2),
            }
            for s in route.segments
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def create_report(route, query, summary, fmt="text"):
    """Create a Report in the requested format ('text' or 'json')."""
    if fmt == "text":
        content = render_text(route, query, summary)
    elif fmt == "json":
        content = render_json(route, query, summary)
    else:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return Report(format=fmt, content=content)


def write_report(report, path):
    """Write a report's content to a file (UTF-8), creating directories as needed."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report.content)
        handle.write("\n")
    report.output_file_path = path
    return report
