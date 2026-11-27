"""
Path visualization and export: console text and JSON reports.
"""

import json


def format_distance(meters):
    if meters >= 1000:
        return f"{meters:g} meters ({meters / 1000:.2f} km)"
    return f"{meters:g} meters ({meters / 1000:.3f} km)"


def generate_summary(route):
    """Key information of a route."""
    return {
        "total_distance_km": route.total_distance_km,
        "total_distance_meters": route.total_distance_meters,
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time_minutes,
    }


def format_text(route, network=None):
    transfer_stations = {t.station_name for t in route.transfers}
    seq = []
    for name in route.station_sequence:
        if name in transfer_stations:
            seq.append(f"{name} [transfer]")
        else:
            seq.append(name)
    out = ["=" * 50,
           f"Route: {route.start} -> {route.end}",
           f"Mode: {route.mode}",
           "-" * 50,
           f"Stations ({len(route.station_sequence)}):",
           "  " + " -> ".join(seq),
           "Line segments:"]
    for i, seg in enumerate(route.segments, 1):
        out.append(f"  {i}. {seg['line']}: {seg['from']} -> {seg['to']} "
                   f"({seg['stops']} stop(s), {format_distance(seg['distance'])})")
    if route.transfers:
        out.append(f"Transfers ({len(route.transfers)}):")
        for t in route.transfers:
            out.append(f"  - At {t.station_name}: {t.from_line} -> {t.to_line}")
    else:
        out.append("Transfers: none")
    out.append("Lines involved: " + ", ".join(str(l) for l in route.involved_lines))
    out.append(f"Total distance: {format_distance(route.total_distance_meters)}")
    out.append(f"Transfer count: {route.transfer_count}")
    out.append(f"Estimated time: {route.estimated_time_minutes} minutes")
    out.append(f"Fare: {route.fare} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json(route):
    return json.dumps(route.to_dict(), ensure_ascii=False, indent=2)


def render(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)


def export_routes(routes, path, fmt="text"):
    """Write all routes to a file in the given format."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = routes[0].to_dict() if len(routes) == 1 else [r.to_dict() for r in routes]
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(format_text(r) for r in routes))
        fh.write("\n")
