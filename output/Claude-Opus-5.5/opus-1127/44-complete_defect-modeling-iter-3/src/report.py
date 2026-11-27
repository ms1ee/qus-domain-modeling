"""Route building, path summaries and report formatting (text / JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from models import PathSummary, Route


def build_route(network, stations, edges):
    """Build a ``Route`` from station numbers and edges produced by ShortestPath."""
    names = [network.number_to_station[n] for n in stations]
    segments = []
    for edge in edges:
        src = network.number_to_station[edge.source]
        dst = network.number_to_station[edge.dest]
        if segments and segments[-1]["line"] == edge.line:
            segments[-1]["stations"].append(dst)
            segments[-1]["distance"] += edge.weight
        else:
            segments.append({"line": edge.line, "stations": [src, dst], "distance": edge.weight})
    transfer_stations = [seg["stations"][0] for seg in segments[1:]]
    involved = []
    for seg in segments:
        if seg["line"] not in involved:
            involved.append(seg["line"])
    total = sum(e.weight for e in edges)
    transfers = max(len(segments) - 1, 0)
    return Route(
        station_sequence=names,
        total_distance=total,
        transfer_count=transfers,
        involved_lines=involved,
        estimated_time=calculate_estimated_time(total, transfers),
        fare=Sum_money(total),
        segments=segments,
        transfer_stations=transfer_stations,
    )


def generate_summary(route):
    return PathSummary(
        total_distance_km=round(route.total_distance / 1000.0, 2),
        total_fare=route.fare,
        transfer_count=route.transfer_count,
        estimated_time=route.estimated_time,
    )


def format_distance(meters):
    """Meters for short distances, kilometers for long ones."""
    if meters < 1000:
        return f"{meters:g} m"
    return f"{meters / 1000.0:.2f} km"


def format_text_report(route, summary=None, query=None):
    summary = summary or generate_summary(route)
    query = query or {}
    start = route.station_sequence[0] if route.station_sequence else ""
    end = route.station_sequence[-1] if route.station_sequence else ""
    out = ["=" * 60, f"Route: {start} -> {end}"]
    if query.get("mode"):
        out.append(f"Mode: {query['mode']}")
    out.append("-" * 60)
    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    out.append("  " + " -> ".join(route.station_sequence))
    out.append("Line segments:")
    for i, seg in enumerate(route.segments, 1):
        if i > 1:
            prev = route.segments[i - 2]["line"]
            out.append(f"  ** Transfer at {seg['stations'][0]}: {prev} -> {seg['line']}")
        out.append(f"  [{i}] {seg['line']}: {' -> '.join(seg['stations'])} "
                   f"({len(seg['stations']) - 1} stops, {format_distance(seg['distance'])})")
    out.append("Transfer stations: " + (", ".join(route.transfer_stations) or "None"))
    out.append("Lines involved: " + (", ".join(route.involved_lines) or "None"))
    out.append(f"Number of transfers: {summary.transfer_count}")
    out.append(f"Total distance: {format_distance(route.total_distance)} "
               f"({route.total_distance} meters / {summary.total_distance_km:.2f} km)")
    out.append(f"Estimated time: {summary.estimated_time:.1f} minutes")
    out.append(f"Fare: {summary.total_fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def route_to_dict(route, summary=None, query=None):
    summary = summary or generate_summary(route)
    return {
        "query": dict(query or {}),
        "path": list(route.station_sequence),
        "segments": [{"line": s["line"], "stations": list(s["stations"]), "distance": s["distance"]}
                     for s in route.segments],
        "distance": {"meters": route.total_distance, "kilometers": summary.total_distance_km,
                     "display": format_distance(route.total_distance)},
        "fare": summary.total_fare,
        "fare_display": f"Fare: {summary.total_fare} yuan",
        "estimated_time": summary.estimated_time,
        "transfer_count": summary.transfer_count,
        "transfer_stations": list(route.transfer_stations),
        "lines": list(route.involved_lines),
    }


def format_json_report(route, summary=None, query=None):
    return json.dumps(route_to_dict(route, summary, query), ensure_ascii=False, indent=2)
