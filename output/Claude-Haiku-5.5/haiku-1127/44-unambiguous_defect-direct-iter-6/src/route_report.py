"""Path visualization and export.

Builds a structured result describing a route (stations, line segments,
transfers, distance, fare, time) and renders it as console text or JSON.
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def _build_segments(names, edges):
    """Group consecutive edges that share a line into segments.

    Args:
        names: Station names along the path (length = len(edges) + 1).
        edges: Edges traversed along the path.
    """
    segments = []
    if not edges:
        return segments
    start = 0
    for i in range(1, len(edges) + 1):
        if i == len(edges) or edges[i].line != edges[start].line:
            seg_edges = edges[start:i]
            segments.append({
                "line": edges[start].line,
                "from": names[start],
                "to": names[i],
                "stations": names[start:i + 1],
                "stop_count": i - start,
                "distance_m": sum(e.distance for e in seg_edges),
            })
            start = i
    return segments


def build_route_result(network, start, end, mode, stations, edges, transfer_count,
                       max_transfers=None, preferred_lines=None):
    """Assemble the full route result and its summary.

    Args:
        network: The ``SubwayNetwork`` used for name lookups.
        start: Starting station name.
        end: Ending station name.
        mode: Query mode used.
        stations: Station numbers from source to target.
        edges: Edges along the path.
        transfer_count: Number of transfers on the path.
        max_transfers: Transfer limit used for the query (or None).
        preferred_lines: Preferred lines used for the query (or None).

    Returns:
        A dictionary with query info, path, segments, transfers, summary fields.
    """
    names = [network.name_of(n) for n in stations]
    total_m = sum(e.distance for e in edges)
    segments = _build_segments(names, edges)

    transfers = []
    for previous, following in zip(segments, segments[1:]):
        transfers.append({
            "station": previous["to"],
            "from_line": previous["line"],
            "to_line": following["line"],
        })

    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])

    fare = Sum_money(total_m)
    estimated_time = calculate_estimated_time(total_m, transfer_count)

    return {
        "query": {
            "start": start,
            "end": end,
            "mode": mode,
            "max_transfers": max_transfers,
            "line_preference": list(preferred_lines or []),
        },
        "path": names,
        "segments": segments,
        "transfers": transfers,
        "distance_m": total_m,
        "distance_km": round(total_m / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": estimated_time,
        "transfer_count": transfer_count,
        "lines": lines,
    }


def format_text(result):
    """Render a route result as human-readable console text."""
    query = result["query"]
    out = []
    out.append("=" * 60)
    out.append(f"Route: {query['start']} -> {query['end']}")
    out.append(f"Query mode: {query['mode']}")
    if query["max_transfers"] is not None:
        out.append(f"Max transfers: {query['max_transfers']}")
    if query["line_preference"]:
        out.append(f"Preferred lines: {', '.join(query['line_preference'])}")
    out.append("-" * 60)

    path = result["path"]
    out.append(f"Station sequence ({len(path)} stations):")
    for index, name in enumerate(path, 1):
        out.append(f"  {index:>3}. {name}")

    out.append("")
    out.append("Line segments:")
    if not result["segments"]:
        out.append("  (no travel required)")
    for index, seg in enumerate(result["segments"], 1):
        out.append(f"  [{index}] {seg['line']}: {seg['from']} -> {seg['to']} "
                   f"({seg['stop_count']} stops, {seg['distance_m']} m)")

    out.append("")
    out.append("Transfers:")
    if not result["transfers"]:
        out.append("  None")
    for transfer in result["transfers"]:
        out.append(f"  Transfer at {transfer['station']}: "
                   f"{transfer['from_line']} -> {transfer['to_line']}")

    out.append("")
    out.append("Summary:")
    out.append(f"  Total distance: {result['distance_m']} m "
               f"({result['distance_km']:.2f} km)")
    out.append(f"  Number of transfers: {result['transfer_count']}")
    out.append(f"  Lines involved: {', '.join(result['lines']) if result['lines'] else 'None'}")
    out.append(f"  Estimated time: {result['estimated_time_min']} min")
    out.append(f"  Fare: {result['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(result):
    """Render a route result as an indented JSON document."""
    return json.dumps(result, ensure_ascii=False, indent=2)
