"""
Path visualization and export (console text and JSON).
"""

import json

try:
    from models import PathSummary
except ImportError:  # pragma: no cover
    from .models import PathSummary


def format_distance(meters):
    """Meters for short distances, kilometres for long ones."""
    if meters < 1000:
        return f"{int(round(meters))} meters"
    return f"{meters / 1000.0:.2f} km"


def build_summary(route):
    return PathSummary.from_route(route)


def format_text_report(route):
    summary = build_summary(route)
    out = [f"=== Route: {route.start} -> {route.end} ===",
           f"Mode: {route.mode}",
           f"Stations ({len(route.station_sequence)}): " + " -> ".join(route.station_sequence),
           "Segments:"]
    for i, seg in enumerate(route.segments):
        stops = len(seg["stations"]) - 1
        out.append(f"  [{seg['line'] or 'Unknown line'}] {seg['stations'][0]} -> {seg['stations'][-1]} "
                   f"({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg['distance'])})")
        if i < len(route.transfers):
            t = route.transfers[i]
            out.append(f"    Transfer at {t.station_name}: {t.from_line} -> {t.to_line}")
    transfer_names = [t.station_name for t in route.transfers]
    out.append("Transfer stations: " + (", ".join(transfer_names) if transfer_names else "None"))
    out.append("Lines involved: " + ", ".join(route.involved_lines))
    out.append(f"Total distance: {format_distance(route.total_distance_meters)} "
               f"({route.total_distance_meters} meters / {summary.total_distance_km:.2f} km)")
    out.append(f"Transfers: {summary.transfer_count}")
    out.append(f"Estimated time: {summary.estimated_time:.1f} minutes")
    out.append(f"Fare: {summary.total_fare} yuan")
    return "\n".join(out)


def build_json_report(route, config=None):
    summary = build_summary(route)
    query = {"start": route.start, "end": route.end, "mode": route.mode}
    if config is not None:
        query["max_transfers"] = getattr(config, "max_transfers", None)
        query["line_preference"] = getattr(config, "preferred_lines", [])
    return {
        "query": query,
        "path": list(route.station_sequence),
        "distance": {"meters": route.total_distance_meters, "kilometers": summary.total_distance_km},
        "fare": summary.total_fare,
        "estimated_time": summary.estimated_time,
        "transfer_count": summary.transfer_count,
        "lines": list(route.involved_lines),
        "transfers": [{"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
                      for t in route.transfers],
        "segments": [{"line": s["line"], "stations": list(s["stations"]), "distance": s["distance"]}
                     for s in route.segments],
    }


def format_json_report(route, config=None):
    return json.dumps(build_json_report(route, config), ensure_ascii=False, indent=2)
