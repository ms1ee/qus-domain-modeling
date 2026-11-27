"""Path visualization and export (console text and JSON)."""

import json


def format_distance(meters):
    """Return distance shown in both meters and kilometers."""
    km = meters / 1000.0
    return "%s meters (%.2f km)" % (_num(meters), km)


def _num(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_report(route):
    """Build a structured summary dictionary for a Route."""
    return {
        "query": {
            "start": route.start,
            "end": route.end,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": list(route.line_preference),
        },
        "path": list(route.stations),
        "station_count": len(route.stations),
        "distance": route.total_distance,
        "distance_m": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 2),
        "fare": route.fare,
        "fare_text": "Fare: %d yuan" % route.fare,
        "estimated_time": route.estimated_time,
        "estimated_time_minutes": route.estimated_time,
        "transfer_count": route.transfer_count,
        "transfer_stations": list(route.transfer_stations),
        "lines": list(route.lines),
        "segments": [
            {"line": s["line"], "from": s["from"], "to": s["to"], "stops": s["stops"],
             "distance": s["distance"], "stations": list(s["stations"])}
            for s in route.segments
        ],
    }


def format_text(report):
    """Console-formatted text report."""
    q = report["query"]
    out = []
    out.append("=" * 60)
    out.append("Route: %s -> %s" % (q["start"], q["end"]))
    out.append("Mode: %s" % q["mode"])
    out.append("-" * 60)
    out.append("Stations (%d): %s" % (report["station_count"], " -> ".join(report["path"])))
    out.append("Segments:")
    segs = report["segments"]
    for i, s in enumerate(segs, 1):
        out.append("  %d. [%s] %s -> %s (%d stop(s), %.2f km)"
                   % (i, s["line"], s["from"], s["to"], s["stops"], s["distance"] / 1000.0))
        if i < len(segs):
            out.append("     Transfer at %s: %s -> %s" % (s["to"], s["line"], segs[i]["line"]))
    out.append("Transfer stations: %s" % (", ".join(report["transfer_stations"]) or "None"))
    out.append("Lines involved: %s" % ", ".join(str(l) for l in report["lines"]))
    out.append("Total distance: %s" % format_distance(report["distance"]))
    out.append("Transfers: %d" % report["transfer_count"])
    out.append("Estimated time: %.1f minutes" % report["estimated_time"])
    out.append(report["fare_text"])
    out.append("=" * 60)
    return "\n".join(out)


def format_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2)


def render(report, fmt="text"):
    return format_json(report) if fmt == "json" else format_text(report)


def write_reports(path, reports, fmt="text"):
    """Write reports to a file (a single JSON object or a list for several)."""
    if fmt == "json":
        payload = reports[0] if len(reports) == 1 else reports
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        content = "\n\n".join(format_text(r) for r in reports)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
        fh.write("\n")
