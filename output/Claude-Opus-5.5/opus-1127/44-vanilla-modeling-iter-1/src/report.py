"""Path visualization and export (console text and JSON)."""

import json

MODE_LABELS = {
    "shortest_distance": "Shortest distance",
    "least_transfer": "Least transfers",
    "comprehensive": "Comprehensive optimal",
}


def format_distance(meters):
    """Show both units; meters first for short distances, km for long ones."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters} meters ({km:.2f} km)"
    return f"{km:.2f} km ({meters} meters)"


def format_fare(fare):
    return f"Fare: {fare} yuan"


def build_summary(route):
    """Key information extracted from a route."""
    return {
        "total_distance_km": route["distance_km"],
        "fare": route["fare"],
        "transfer_count": route["transfer_count"],
        "estimated_time": route["estimated_time"],
    }


def format_text(route):
    """Console-formatted report with line segments and transfers."""
    sep = "=" * 60
    sub = "-" * 60
    out = [
        sep,
        f"Route: {route['start']} -> {route['end']}  "
        f"(mode: {MODE_LABELS.get(route['mode'], route['mode'])})",
        sub,
        f"Station sequence ({len(route['path'])} stations):",
        "  " + " -> ".join(route["path"]),
        sub,
        "Line segments:",
    ]
    segs = route["segments"]
    for i, seg in enumerate(segs):
        stops = len(seg["stations"]) - 1
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"])
                   + f"  ({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg['distance'])})")
        if i + 1 < len(segs):
            out.append(f"    * Transfer at {segs[i + 1]['stations'][0]}: "
                       f"{seg['line']} -> {segs[i + 1]['line']}")
    out.append(sub)
    out.append(f"Total distance: {format_distance(route['distance_m'])}")
    if route["transfer_count"]:
        out.append(f"Transfers: {route['transfer_count']} (at {', '.join(route['transfer_stations'])})")
    else:
        out.append("Transfers: 0 (direct)")
    out.append(f"Lines involved: {', '.join(str(l) for l in route['lines'])}")
    out.append(f"Estimated time: {route['estimated_time']} minutes")
    out.append(format_fare(route["fare"]))
    out.append(sep)
    return "\n".join(out)


def to_json_dict(route):
    """Structured data for programmatic integration."""
    return {
        "query": {
            "start": route["start"],
            "end": route["end"],
            "mode": route["mode"],
            "max_transfers": route.get("max_transfers"),
            "line_preference": route.get("line_preference", []),
        },
        "path": route["path"],
        "segments": [
            {"line": s["line"], "stations": s["stations"], "distance": s["distance"]}
            for s in route["segments"]
        ],
        "distance": {"meters": route["distance_m"], "kilometers": route["distance_km"]},
        "fare": route["fare"],
        "estimated_time": route["estimated_time"],
        "transfer_count": route["transfer_count"],
        "transfer_stations": route["transfer_stations"],
        "lines": route["lines"],
    }


def format_json(route):
    return json.dumps(to_json_dict(route), ensure_ascii=False, indent=2)


def render(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)


def export_results(routes, path, fmt="text"):
    """Write all results to ``path`` (JSON: object for one result, list otherwise)."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            items = [to_json_dict(r) for r in routes]
            payload = items[0] if len(items) == 1 else items
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        else:
            fh.write("\n\n".join(format_text(r) for r in routes))
            fh.write("\n")
