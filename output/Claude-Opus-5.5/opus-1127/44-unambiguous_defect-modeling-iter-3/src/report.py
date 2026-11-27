"""Path visualization and export (console text and JSON)."""

import json


def _fmt_num(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def format_distance(meters):
    km = meters / 1000.0
    return f"{_fmt_num(meters)} meters ({km:.2f} km)"


def route_to_dict(route):
    """Structured representation of a route for programmatic use."""
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": list(route.stations),
        "station_count": len(route.stations),
        "distance": {
            "meters": route.distance,
            "kilometers": round(route.distance / 1000.0, 2),
        },
        "fare": route.fare,
        "fare_text": f"Fare: {route.fare} yuan",
        "estimated_time": route.estimated_time,
        "estimated_time_unit": "minutes",
        "transfer_count": route.transfer_count,
        "transfer_stations": [dict(t) for t in route.transfer_stations],
        "lines": list(route.lines),
        "segments": [
            {"line": s["line"], "from": s["from"], "to": s["to"],
             "stations": list(s["stations"]), "distance": s["distance"]}
            for s in route.segments
        ],
    }


def format_json(route_or_routes):
    if isinstance(route_or_routes, list):
        payload = [route_to_dict(r) for r in route_or_routes]
        if len(payload) == 1:
            payload = payload[0]
    else:
        payload = route_to_dict(route_or_routes)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_text(route):
    """Console-formatted route report."""
    out = []
    out.append("=" * 50)
    out.append(f"Route: {route.start} -> {route.end}  (mode: {route.mode})")
    out.append("-" * 50)
    out.append(f"Stations ({len(route.stations)}): " + " -> ".join(route.stations))
    out.append(f"Total distance: {format_distance(route.distance)}")
    out.append("Lines involved: " + (", ".join(str(l) for l in route.lines) or "-"))
    out.append(f"Transfers: {route.transfer_count}")
    for t in route.transfer_stations:
        out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append("Segments:")
    for seg in route.segments:
        stops = len(seg["stations"]) - 1
        out.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} "
                   f"({stops} stop{'s' if stops != 1 else ''}, {_fmt_num(seg['distance'])} m)")
        out.append("      " + " -> ".join(seg["stations"]))
    out.append(f"Estimated time: {route.estimated_time} minutes")
    out.append(f"Fare: {route.fare} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_route(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)
