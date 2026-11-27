"""
Route visualization, summary and report generation.

Turns a list of station names and edges from the path search into a Route,
extracts a PathSummary, and renders the result as console text or JSON.
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from models import PathSummary, Report, Route, RouteSegment, TransferPoint


def build_route(station_names, edges, mode):
    """Build a Route (segments, transfers, totals) from a path.

    Args:
        station_names: Station names from origin to destination.
        edges: Edge objects along the path (len = len(station_names) - 1).
        mode: The query mode used.

    Returns:
        Route: The assembled route.
    """
    segments = []
    transfers = []
    if edges:
        start = 0
        for i in range(1, len(edges) + 1):
            if i == len(edges) or edges[i].line != edges[start].line:
                seg_edges = edges[start:i]
                segments.append(
                    RouteSegment(
                        line_name=edges[start].line,
                        start_station=station_names[start],
                        end_station=station_names[i],
                        distance_meters=float(sum(e.distance for e in seg_edges)),
                    )
                )
                if i < len(edges):
                    transfers.append(
                        TransferPoint(
                            station_name=station_names[i],
                            lines_involved=[edges[start].line, edges[i].line],
                        )
                    )
                start = i
    total = float(sum(e.distance for e in edges))
    return Route(
        total_distance_meters=total,
        mode=mode,
        transfer_count=len(transfers),
        station_sequence=list(station_names),
        segments=segments,
        transfers=transfers,
    )


def lines_involved(route):
    """Return the unique line names used by a route, in order of first use."""
    result = []
    for segment in route.segments:
        if segment.line_name not in result:
            result.append(segment.line_name)
    return result


def build_summary(route):
    """Extract the key figures (distance, fare, transfers, time) from a route."""
    fare = Sum_money(route.total_distance_meters)
    minutes = calculate_estimated_time(route.total_distance_meters, route.transfer_count)
    return PathSummary(
        total_distance_meters=route.total_distance_meters,
        total_fare=fare,
        transfer_count=route.transfer_count,
        estimated_time_minutes=minutes,
    )


def format_distance(meters):
    """Format a distance: meters for short trips, meters plus kilometers for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters:.0f} m ({meters / 1000:.2f} km)"


def text_report(route, summary, query):
    """Render a console-formatted report."""
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"From: {query.origin}")
    out.append(f"To: {query.destination}")
    out.append(f"Mode: {query.mode}")
    if query.max_transfers is not None:
        out.append(f"Max transfers: {query.max_transfers}")
    if query.line_preference:
        out.append(f"Line preference: {query.line_preference}")
    out.append("")
    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    out.append("  " + " -> ".join(route.station_sequence))
    out.append("")
    out.append("Line segments:")
    for index, seg in enumerate(route.segments, 1):
        out.append(
            f"  {index}. [{seg.line_name}] {seg.start_station} -> {seg.end_station} "
            f"({format_distance(seg.distance_meters)})"
        )
    out.append("")
    out.append("Transfers:")
    if route.transfers:
        for transfer in route.transfers:
            out.append(f"  - {transfer.station_name}: {' / '.join(transfer.lines_involved)}")
    else:
        out.append("  None (no transfer required)")
    out.append("")
    out.append(f"Lines involved: {', '.join(lines_involved(route)) or 'none'}")
    out.append(f"Total distance: {format_distance(summary.total_distance_meters)}")
    out.append(f"Transfers: {summary.transfer_count}")
    out.append(f"Estimated time: {summary.estimated_time_minutes:.1f} minutes")
    out.append(f"Fare: {summary.total_fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def json_report(route, summary, query):
    """Render a structured JSON report for programmatic use."""
    payload = {
        "query": {
            "origin": query.origin,
            "destination": query.destination,
            "mode": query.mode,
            "max_transfers": query.max_transfers,
            "line_preference": query.line_preference,
        },
        "path": route.station_sequence,
        "distance_meters": round(summary.total_distance_meters, 1),
        "distance_kilometers": round(summary.total_distance_meters / 1000.0, 3),
        "fare_yuan": summary.total_fare,
        "estimated_time_minutes": round(summary.estimated_time_minutes, 2),
        "transfer_count": summary.transfer_count,
        "lines": lines_involved(route),
        "segments": [
            {
                "line": seg.line_name,
                "start": seg.start_station,
                "end": seg.end_station,
                "distance_meters": seg.distance_meters,
            }
            for seg in route.segments
        ],
        "transfers": [
            {"station": t.station_name, "lines": t.lines_involved} for t in route.transfers
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_report(route, summary, query, fmt):
    """Generate a Report in the requested format ('text' or 'json')."""
    if fmt == "text":
        content = text_report(route, summary, query)
    elif fmt == "json":
        content = json_report(route, summary, query)
    else:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return Report(format=fmt, content=content)
