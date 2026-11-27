"""Route summary, visualization and export formatting."""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import count_transfers


def build_segments(stations, edges, number_to_station):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["stations"].append(number_to_station[e.dest])
            seg["distance"] += e.distance
        else:
            segments.append({
                "line": e.line,
                "stations": [number_to_station[e.source], number_to_station[e.dest]],
                "distance": e.distance,
            })
    return segments


def build_route_info(start, end, stations, edges, number_to_station, config=None):
    """Build a summary dict of a computed route."""
    names = [number_to_station[s] for s in stations]
    distance = sum(e.distance for e in edges)
    transfers = count_transfers(edges)
    segments = build_segments(stations, edges, number_to_station)
    transfer_stations = [seg["stations"][0] for seg in segments[1:]]
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    fare = Sum_money(distance)
    est = calculate_estimated_time(distance, transfers)
    if isinstance(distance, float) and distance.is_integer():
        distance = int(distance)
    query = {"start": start, "end": end}
    if config is not None:
        query.update({
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        })
    return {
        "query": query,
        "path": names,
        "station_count": len(names),
        "distance": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time": est,
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def format_distance(meters):
    if meters < 1000:
        return f"{meters} m ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({meters} m)"


def format_text_report(info):
    """Console-formatted text report."""
    q = info["query"]
    lines = []
    sep = "=" * 50
    lines.append(sep)
    lines.append(f"Route: {q['start']} -> {q['end']}")
    if "mode" in q:
        lines.append(f"Mode: {q['mode']}")
    lines.append("-" * 50)
    lines.append(f"Stations ({info['station_count']}): " + " -> ".join(info["path"]))
    lines.append("Line segments:")
    prev = None
    for seg in info["segments"]:
        if prev is not None:
            lines.append(f"  >> Transfer at {seg['stations'][0]}: {prev['line']} -> {seg['line']}")
        stops = len(seg["stations"]) - 1
        lines.append(
            f"  [{seg['line']}] {' -> '.join(seg['stations'])} "
            f"({stops} stop{'s' if stops != 1 else ''}, {seg['distance'] / 1000.0:.2f} km)")
        prev = seg
    lines.append("Transfer stations: " + (", ".join(info["transfer_stations"]) or "None"))
    lines.append("Lines involved: " + (", ".join(info["lines"]) or "None"))
    lines.append(f"Total distance: {format_distance(info['distance'])}")
    lines.append(f"Transfers: {info['transfer_count']}")
    lines.append(f"Estimated time: {info['estimated_time']} minutes")
    lines.append(f"Fare: {info['fare']} yuan")
    lines.append(sep)
    return "\n".join(lines)


def format_json_report(info, indent=2):
    """Structured JSON report."""
    return json.dumps(info, ensure_ascii=False, indent=indent)


def format_report(info, fmt="text"):
    if fmt == "json":
        return format_json_report(info)
    return format_text_report(info)
