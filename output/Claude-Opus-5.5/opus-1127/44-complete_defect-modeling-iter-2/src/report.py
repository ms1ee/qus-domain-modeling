"""
Route visualization and export (console text and JSON).
"""

import json


def format_distance(meters):
    """Short distances in meters, long distances in kilometers."""
    if meters < 1000:
        return f"{int(round(meters))} meters"
    return f"{meters / 1000.0:.2f} km"


def format_fare(fare):
    return f"Fare: {fare} yuan"


def route_to_text(route):
    sep = "=" * 56
    out = [sep, f"Route: {route.start} -> {route.end}", f"Mode: {route.mode}", "-" * 56]
    out.append(f"Station sequence ({len(route.station_sequence)} stations):")
    out.append("  " + " -> ".join(route.station_sequence))
    out.append("")
    out.append("Line segments:")
    for i, seg in enumerate(route.segments):
        if i > 0:
            prev = route.segments[i - 1]["line"]
            out.append(f"  ** Transfer at {seg['stations'][0]}: {prev} -> {seg['line']} **")
        stops = len(seg["stations"]) - 1
        out.append(f"  [{seg['line']}] {' -> '.join(seg['stations'])} ({stops} stop{'s' if stops != 1 else ''})")
    out.append("")
    out.append(f"Lines involved: {', '.join(str(l) for l in route.involved_lines)}")
    if route.transfer_count:
        out.append(f"Transfers: {route.transfer_count} (at {', '.join(route.transfer_stations)})")
    else:
        out.append("Transfers: 0 (direct route)")
    out.append(f"Total distance: {format_distance(route.total_distance_m)} "
               f"({route.total_distance_m} m / {route.total_distance_km:.2f} km)")
    out.append(f"Estimated time: {route.estimated_time} minutes")
    out.append(format_fare(route.fare))
    out.append(sep)
    return "\n".join(out)


def route_to_json(route, indent=2):
    return json.dumps(route.to_dict(), ensure_ascii=False, indent=indent)


def render(route, fmt="text"):
    return route_to_json(route) if fmt == "json" else route_to_text(route)


def write_results(path, routes, fmt="text"):
    """Write all routes queried so far to ``path``."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            data = routes[0].to_dict() if len(routes) == 1 else [r.to_dict() for r in routes]
            json.dump(data, fh, ensure_ascii=False, indent=2)
        else:
            fh.write("\n\n".join(route_to_text(r) for r in routes))
        fh.write("\n")
