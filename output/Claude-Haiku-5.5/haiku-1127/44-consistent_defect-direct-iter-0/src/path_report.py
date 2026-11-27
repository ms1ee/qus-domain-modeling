"""Path visualisation, summary generation, and report export (text and JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Format a distance: meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def build_route_segments(network, route):
    """Split a route into consecutive single-line segments.

    Returns:
        list of dicts with keys: line, from, to, station_count, distance_m.
    """
    edges = route.edges
    stations = route.station_numbers
    if not edges:
        return []

    segments = []

    def make_segment(line, start_idx, end_idx, distance):
        return {
            "line": line,
            "from": network.name_of(stations[start_idx]),
            "to": network.name_of(stations[end_idx]),
            "station_count": end_idx - start_idx + 1,
            "distance_m": distance,
        }

    start_idx = 0
    current_line = edges[0].line
    distance = 0
    for i, edge in enumerate(edges):
        if edge.line != current_line:
            # Transfer happens at station index i.
            segments.append(make_segment(current_line, start_idx, i, distance))
            start_idx = i
            current_line = edge.line
            distance = 0
        distance += edge.distance
    segments.append(make_segment(current_line, start_idx, len(edges), distance))
    return segments


def build_transfers(network, route):
    """Describe every transfer station on the route.

    Returns:
        list of dicts with keys: station, from_line, to_line, lines.
    """
    edges = route.edges
    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            station_name = network.name_of(route.station_numbers[i])
            transfers.append({
                "station": station_name,
                "from_line": edges[i - 1].line,
                "to_line": edges[i].line,
                "lines": network.lines_of(station_name),
            })
    return transfers


def build_report(network, route, query):
    """Assemble the complete report for a route query.

    Args:
        network: SubwayNetwork used to resolve names and lines.
        route: RouteResult from pathfinding.compute_route.
        query: dict describing the query (start, end, mode, max_transfers,
            line_preference).

    Returns:
        dict containing query info, path, distance, fare, estimated time,
        transfer count, involved lines, transfers, and segments.

    Raises:
        ValueError: If the fare cannot be calculated.
    """
    path_names = [network.name_of(n) for n in route.station_numbers]
    distance_m = int(route.distance_m)
    fare = Sum_money(distance_m)
    transfer_count = route.transfer_count
    estimated = calculate_estimated_time(distance_m, transfer_count)

    lines_involved = []
    for edge in route.edges:
        if edge.line not in lines_involved:
            lines_involved.append(edge.line)

    return {
        "query": query,
        "path": path_names,
        "path_order": "start_to_end",
        "station_count": len(path_names),
        "distance_m": distance_m,
        "distance_km": round(distance_m / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(estimated, 1),
        "transfer_count": transfer_count,
        "lines": lines_involved,
        "transfers": build_transfers(network, route),
        "segments": build_route_segments(network, route),
        "summary": {
            "distance_m": distance_m,
            "fare": fare,
            "transfer_count": transfer_count,
            "estimated_time_min": round(estimated, 1),
        },
    }


def format_text(report):
    """Render a report as human-readable console text."""
    q = report["query"]
    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Route and Fare")
    out.append("=" * 60)
    out.append(f"Starting station : {q['start']}")
    out.append(f"Ending station   : {q['end']}")
    out.append(f"Query mode       : {q['mode']}")
    if q.get("max_transfers") is not None:
        out.append(f"Max transfers    : {q['max_transfers']}")
    if q.get("line_preference"):
        out.append(f"Line preference  : {', '.join(q['line_preference'])}")
    out.append("")
    out.append("Station sequence (end -> start):")
    out.append("  " + " -> ".join(reversed(report["path"])))
    out.append("")
    out.append("Line segments (start -> end):")
    if report["segments"]:
        for idx, seg in enumerate(report["segments"], 1):
            out.append(
                f"  {idx}. {seg['line']}: {seg['from']} -> {seg['to']} "
                f"({seg['station_count']} stations, {format_distance(seg['distance_m'])})")
    else:
        out.append("  (no segments)")
    out.append("")
    if report["transfers"]:
        out.append(f"Transfer stations ({len(report['transfers'])}):")
        for t in report["transfers"]:
            out.append(f"  - {t['station']}: {t['from_line']} -> {t['to_line']} "
                       f"(station lines: {', '.join(t['lines'])})")
    else:
        out.append("Transfer stations: none")
    out.append("")
    out.append(f"Lines involved   : {', '.join(report['lines']) if report['lines'] else 'none'}")
    out.append(f"Total distance   : {format_distance(report['distance_m'])}")
    out.append(f"Transfers        : {report['transfer_count']}")
    out.append(f"Estimated time   : {report['estimated_time_min']} min")
    out.append(f"Fare: {report['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(report, indent=2):
    """Render a report as a JSON string (indent=None gives a single line)."""
    return json.dumps(report, ensure_ascii=False, indent=indent)
