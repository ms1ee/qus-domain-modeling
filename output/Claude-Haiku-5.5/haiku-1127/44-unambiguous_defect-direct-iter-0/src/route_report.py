"""Path visualization and export.

Produces console text reports and structured JSON reports for a computed
route, computes a route summary, and appends results to output files.
"""

import json


def summarize_route(route):
    """Return a dict with the key information of a route."""
    return {
        "start": route.start,
        "end": route.end,
        "station_count": len(route.station_names),
        "total_distance_m": route.distance_m,
        "total_distance_km": round(route.distance_km, 2),
        "fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_min": route.estimated_minutes,
        "lines": list(route.lines),
    }


def route_to_dict(route):
    """Return the structured (JSON-serializable) representation of a route."""
    cfg = route.config
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": cfg.mode,
            "max_transfers": cfg.max_transfers,
            "line_preference": list(cfg.preferred_lines),
        },
        "path": list(route.station_names),
        "distance_m": route.distance_m,
        "distance_km": round(route.distance_km, 2),
        "fare": route.fare,
        "estimated_time_min": route.estimated_minutes,
        "transfer_count": route.transfer_count,
        "transfers": [dict(item) for item in route.transfer_stations],
        "lines": list(route.lines),
        "segments": [dict(item) for item in route.segments],
    }


def format_text(route):
    """Return a human-readable console report for a route."""
    cfg = route.config
    max_t = "unlimited" if cfg.max_transfers is None else str(cfg.max_transfers)
    preference = ", ".join(cfg.preferred_lines) if cfg.preferred_lines else "none"

    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Route Report")
    out.append("=" * 60)
    out.append(f"From: {route.start}")
    out.append(f"To: {route.end}")
    out.append(f"Mode: {cfg.mode} | Max transfers: {max_t} | Line preference: {preference}")
    out.append("")

    out.append("Line segments:")
    for index, segment in enumerate(route.segments, 1):
        out.append(
            f"  {index}. [{segment['line']}] {segment['from']} -> {segment['to']} "
            f"({segment['stations']} stations, {segment['distance_m']} m)"
        )
    out.append("")

    out.append(f"Station sequence ({len(route.station_names)} stations):")
    for index, name in enumerate(route.station_names, 1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append(f"Total distance: {route.distance_m} m ({route.distance_km:.2f} km)")
    out.append(f"Transfers: {route.transfer_count}")
    if route.transfer_stations:
        for item in route.transfer_stations:
            out.append(
                f"  - Transfer at {item['station']}: {item['from_line']} -> {item['to_line']}"
            )
    else:
        out.append("  No transfer required")
    out.append(f"Lines involved: {', '.join(route.lines)}")
    out.append(f"Estimated travel time: {route.estimated_minutes:.1f} min")
    out.append(f"Fare: {route.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(route):
    """Return the route report as a pretty-printed JSON string."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)


def render_route(route, fmt="text"):
    """Render a route in the requested format ('text' or 'json')."""
    if fmt == "text":
        return format_text(route)
    if fmt == "json":
        return format_json(route)
    raise ValueError(f"unsupported output format '{fmt}'")


def export_text(content, path):
    """Append a rendered report to a file, creating it when necessary."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(content)
        fh.write("\n\n")
