"""
Report generation for route query results.

Supported formats:
  * ``text`` - human-readable console report with line segments and transfers.
  * ``json`` - structured data for programmatic integration.
"""

import json

from route_service import RouteResult

SUPPORTED_FORMATS = ("text", "json")


def format_distance(meters):
    """
    Format a distance showing both meters and kilometers.

    Short distances lead with meters, long distances lead with kilometers.
    """
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({meters:.0f} m)"


def build_segments(station_names, edges):
    """
    Group consecutive edges operated by the same line into segments.

    Returns:
        list[dict]: Each item has ``line``, ``start``, ``end``, ``hops``, ``distance_m``.
    """
    segments = []
    for index, edge in enumerate(edges):
        if segments and segments[-1]["line"] == edge.line:
            segment = segments[-1]
            segment["end"] = station_names[index + 1]
            segment["hops"] += 1
            segment["distance_m"] += edge.weight
        else:
            segments.append({
                "line": edge.line,
                "start": station_names[index],
                "end": station_names[index + 1],
                "hops": 1,
                "distance_m": float(edge.weight),
            })
    return segments


def _max_transfers_label(max_transfers):
    return "unlimited (default limit applies)" if max_transfers is None else str(max_transfers)


def render_text(result):
    """Render a ``RouteResult`` as a console-formatted text report."""
    if not isinstance(result, RouteResult):
        raise TypeError("render_text expects a RouteResult")

    divider = "=" * 60
    preference = ", ".join(result.preferred_lines) if result.preferred_lines else "none"
    segments = build_segments(result.station_names, result.edges)

    out = []
    out.append(divider)
    out.append("Beijing Subway Fare Query")
    out.append(divider)
    out.append(f"Query:           {result.start_station} -> {result.end_station}")
    out.append(f"Mode:            {result.mode}")
    out.append(f"Max transfers:   {_max_transfers_label(result.max_transfers)}")
    out.append(f"Line preference: {preference}")
    out.append("")

    out.append(f"Station sequence ({len(result.station_names)} stations):")
    for index, name in enumerate(result.station_names, start=1):
        marker = ""
        if 1 < index < len(result.station_names) and result.station_names[index - 1] is not None:
            if any(t["station"] == name for t in result.transfers):
                marker = "  [transfer]"
        out.append(f"  {index}. {name}{marker}")
    out.append("")

    out.append("Line segments:")
    for segment in segments:
        out.append(
            f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({segment['hops']} interval(s), {format_distance(segment['distance_m'])})"
        )
    out.append("")

    if result.transfers:
        out.append(f"Transfer stations ({len(result.transfers)}):")
        for transfer in result.transfers:
            out.append(f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}")
    else:
        out.append("Transfer stations: none (no transfer required)")
    out.append("")

    out.append("Lines involved: " + (", ".join(result.lines) if result.lines else "none"))
    out.append("")

    out.append("Summary:")
    out.append(f"  Total distance:    {format_distance(result.total_distance_m)}")
    out.append(f"  Transfers:         {result.transfer_count}")
    out.append(f"  Estimated time:    {result.estimated_time_minutes:.1f} min")
    out.append(f"Fare: {result.fare_yuan} yuan")
    out.append(divider)
    return "\n".join(out)


def build_json_data(result):
    """Build the JSON-serialisable dictionary for a ``RouteResult``."""
    return {
        "query": {
            "start_station": result.start_station,
            "end_station": result.end_station,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": list(result.station_names),
        "segments": build_segments(result.station_names, result.edges),
        "distance_meters": round(result.total_distance_m, 2),
        "distance_kilometers": round(result.total_distance_km, 3),
        "fare_yuan": result.fare_yuan,
        "estimated_time_minutes": round(result.estimated_time_minutes, 1),
        "transfer_count": result.transfer_count,
        "transfers": list(result.transfers),
        "lines": list(result.lines),
    }


def render_json(result):
    """Render a ``RouteResult`` as an indented JSON string."""
    if not isinstance(result, RouteResult):
        raise TypeError("render_json expects a RouteResult")
    return json.dumps(build_json_data(result), ensure_ascii=False, indent=2)


def render_report(result, fmt="text"):
    """
    Render a route result in the requested format.

    Args:
        result: A ``RouteResult``.
        fmt: "text" or "json".

    Raises:
        ValueError: If the format is unsupported.
    """
    if fmt == "text":
        return render_text(result)
    if fmt == "json":
        return render_json(result)
    raise ValueError(f"unsupported output format '{fmt}', expected one of {SUPPORTED_FORMATS}")
