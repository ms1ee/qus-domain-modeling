"""Path visualisation, summary generation and report export (text and JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Format a distance: meters for short distances, kilometres for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km"


def format_distance_both(meters):
    """Format a distance showing both meters and kilometres."""
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.3f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def _build_segments(route):
    """Group consecutive edges served by the same line into segments."""
    segments = []
    current = None
    stations = route.stations
    for index, edge in enumerate(route.edges):
        start_name = stations[index]
        end_name = stations[index + 1]
        if current is None or current["line"] != edge.line:
            current = {
                "line": edge.line,
                "from": start_name,
                "to": end_name,
                "stops": 0,
                "distance_m": 0,
            }
            segments.append(current)
        current["to"] = end_name
        current["stops"] += 1
        current["distance_m"] += edge.distance
    return segments


def _build_transfers(route, network):
    """Describe every station where the traveller changes line."""
    transfers = []
    stations = route.stations
    for index in range(1, len(route.edges)):
        previous_edge = route.edges[index - 1]
        next_edge = route.edges[index]
        if previous_edge.line != next_edge.line:
            station = stations[index]
            transfers.append({
                "station": station,
                "from_line": previous_edge.line,
                "to_line": next_edge.line,
                "station_lines": network.lines_of(station),
            })
    return transfers


def build_report(route, network, query_info):
    """Build a structured summary dictionary for a computed route.

    ``query_info`` is a dict describing the query (start, end, mode, ...).
    """
    distance = route.distance
    fare = Sum_money(distance)
    estimated_minutes = calculate_estimated_time(distance, route.transfer_count)

    lines_involved = []
    for edge in route.edges:
        if edge.line not in lines_involved:
            lines_involved.append(edge.line)

    return {
        "query": dict(query_info),
        "path": list(route.stations),
        "path_length": len(route.stations),
        "distance_m": distance,
        "distance_km": round(distance / 1000.0, 3),
        "fare": fare,
        "estimated_time_min": round(estimated_minutes, 1),
        "transfer_count": route.transfer_count,
        "lines": lines_involved,
        "transfers": _build_transfers(route, network),
        "segments": _build_segments(route),
    }


def render_text(summary):
    """Render a summary as console-friendly text."""
    query = summary["query"]
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"From: {query['start']}    To: {query['end']}")
    max_transfers = query.get("max_transfers")
    preference = query.get("line_preference") or []
    out.append(f"Mode: {query['mode']}    Max transfers: "
               f"{'unlimited' if max_transfers is None else max_transfers}")
    out.append(f"Line preference: {', '.join(preference) if preference else 'none'}")
    out.append("-" * 60)

    out.append(f"Route ({summary['path_length']} stations):")
    for index, station in enumerate(summary["path"], start=1):
        out.append(f"  {index:>3}. {station}")

    out.append("")
    out.append("Line segments:")
    for segment in summary["segments"]:
        out.append(f"  [{segment['line']}] {segment['from']} -> {segment['to']} "
                   f"({segment['stops']} stops, {format_distance(segment['distance_m'])})")

    out.append("")
    out.append("Transfers:")
    if not summary["transfers"]:
        out.append("  None (no transfers)")
    for transfer in summary["transfers"]:
        out.append(f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
                   f"  (lines at station: {', '.join(transfer['station_lines'])})")

    out.append("")
    out.append("-" * 60)
    out.append(f"Total distance: {format_distance_both(summary['distance_m'])}")
    out.append(f"Number of transfers: {summary['transfer_count']}")
    out.append(f"Lines involved: {', '.join(summary['lines'])}")
    out.append(f"Estimated time: {summary['estimated_time_min']:.1f} min")
    out.append(f"Fare: {summary['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def render_json(summary):
    """Render a summary as a JSON document string."""
    return json.dumps(summary, ensure_ascii=False, indent=2)
