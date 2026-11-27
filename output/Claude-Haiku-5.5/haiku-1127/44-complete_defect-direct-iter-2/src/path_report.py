"""Path visualization, summary generation and report export.

Produces:
    * the complete station sequence,
    * line segments and transfer details,
    * distance summaries (meters for short, kilometers for long distances),
    * console text and JSON representations.
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time

MODE_DESCRIPTIONS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Minimum transfers",
    "comprehensive": "Comprehensive optimal",
}


def _normalize_number(value):
    """Return an int for integral floats so that output stays tidy."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def format_distance(distance_m):
    """Format a distance: meters for short trips, kilometers for long trips."""
    if distance_m < 1000:
        return f"{distance_m} m"
    return f"{distance_m / 1000:.2f} km ({distance_m} m)"


def meters_to_km(distance_m):
    """Convert meters to kilometers rounded to two decimals."""
    return round(distance_m / 1000.0, 2)


def involved_lines(edges):
    """Return the line names used by the path, in order of first appearance."""
    result = []
    for edge in edges:
        if edge.line not in result:
            result.append(edge.line)
    return result


def build_segments(names, edges):
    """Group consecutive edges on the same line into segments.

    Each segment is a dict with: line, from, to, stations, stop_count, distance_m.
    """
    if not edges:
        return []

    def make_segment(first, last):
        # Segment covers edges[first:last], i.e. stations names[first..last].
        stations = names[first:last + 1]
        distance = _normalize_number(sum(edges[k].distance for k in range(first, last)))
        return {
            "line": edges[first].line,
            "from": stations[0],
            "to": stations[-1],
            "stations": stations,
            "stop_count": len(stations) - 1,
            "distance_m": distance,
        }

    segments = []
    seg_start = 0
    current_line = edges[0].line
    for i, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append(make_segment(seg_start, i))
            seg_start = i
            current_line = edge.line
    segments.append(make_segment(seg_start, len(edges)))
    return segments


def build_transfers(names, edges):
    """Return the list of transfer points (station and the two lines involved)."""
    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append({
                "station": names[i],
                "from_line": edges[i - 1].line,
                "to_line": edges[i].line,
            })
    return transfers


def count_transfers(edges):
    """Count line changes along the path."""
    return sum(1 for i in range(1, len(edges)) if edges[i - 1].line != edges[i].line)


def generate_summary(names, edges, transfer_count=None):
    """Extract the key path summary: distance, fare, transfers and time."""
    distance_m = _normalize_number(sum(e.distance for e in edges))
    if transfer_count is None:
        transfer_count = count_transfers(edges)
    fare = Sum_money(distance_m)
    estimated_time = calculate_estimated_time(distance_m, transfer_count)
    return {
        "distance_m": distance_m,
        "distance_km": meters_to_km(distance_m),
        "fare": fare,
        "transfer_count": transfer_count,
        "estimated_time_min": estimated_time,
    }


def build_report(start, end, config, names, edges, transfer_count=None):
    """Assemble the complete report dictionary for one query.

    Args:
        start, end: official station names of the query.
        config: the PathfindingConfig used for the query.
        names: station names along the path, from start to end.
        edges: Edge objects along the path.
        transfer_count: optional transfer count from the path search.
    """
    summary = generate_summary(names, edges, transfer_count)
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": list(names),
        "segments": build_segments(names, edges),
        "transfers": build_transfers(names, edges),
        "lines": involved_lines(edges),
        "distance_m": summary["distance_m"],
        "distance_km": summary["distance_km"],
        "fare": summary["fare"],
        "transfer_count": summary["transfer_count"],
        "estimated_time_min": summary["estimated_time_min"],
    }


def format_text(report):
    """Render a report as human-readable console text."""
    query = report["query"]
    rule = "=" * 60
    out = [rule, "Beijing Subway Fare Query Result", rule]
    out.append(f"Start station : {query['start']}")
    out.append(f"End station   : {query['end']}")
    out.append(f"Query mode    : {MODE_DESCRIPTIONS.get(query['mode'], query['mode'])}")
    if query["max_transfers"] is not None:
        out.append(f"Max transfers : {query['max_transfers']}")
    if query["line_preference"]:
        out.append("Line preference: " + ", ".join(query["line_preference"]))
    out.append("")

    out.append(f"Station sequence ({len(report['path'])} stations):")
    for index, name in enumerate(report["path"], start=1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for seg in report["segments"]:
        out.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} "
                   f"({seg['stop_count']} stops, {format_distance(seg['distance_m'])})")
    out.append("")

    out.append("Transfers:")
    if report["transfers"]:
        for t in report["transfers"]:
            out.append(f"  {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("  None (direct route)")
    out.append("")

    out.append(f"Total distance : {format_distance(report['distance_m'])}")
    out.append(f"Transfers      : {report['transfer_count']}")
    out.append(f"Estimated time : {report['estimated_time_min']} min")
    out.append(f"Lines involved : {', '.join(report['lines'])}")
    out.append(f"Fare: {report['fare']} yuan")
    out.append(rule)
    return "\n".join(out)


def format_json(report):
    """Render a report as a JSON document for programmatic use."""
    return json.dumps(report, ensure_ascii=False, indent=2)
