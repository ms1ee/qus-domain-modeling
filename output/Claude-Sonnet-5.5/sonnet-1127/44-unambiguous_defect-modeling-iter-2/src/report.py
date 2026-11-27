"""Report generation (text and JSON)."""
import json


def segments(edges, names):
    """Group edges by line: list of dicts(line, from, to, stops)."""
    segs = []
    for e in edges:
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = names[e.dest]
            segs[-1]["stops"] += 1
        else:
            segs.append({"line": e.line, "from": names[e.source], "to": names[e.dest], "stops": 1})
    return segs


def format_distance(d):
    return f"{d} m ({d / 1000:.2f} km)" if d < 1000 else f"{d / 1000:.2f} km ({d} m)"


def build_summary(start, end, mode, station_names, edges, names, distance, fare, minutes):
    segs = segments(edges, names)
    transfers = [{"station": s["to"], "from_line": s["line"], "to_line": n["line"]}
                 for s, n in zip(segs, segs[1:])]
    lines = []
    for s in segs:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": station_names,
        "segments": segs,
        "distance_m": distance,
        "distance_km": round(distance / 1000, 2),
        "fare": fare,
        "estimated_time_min": minutes,
        "transfer_count": len(transfers),
        "transfers": transfers,
        "lines": lines,
    }


def render(summary, fmt="text"):
    if fmt == "json":
        return json.dumps(summary, ensure_ascii=False, indent=2)
    q = summary["query"]
    out = [f"Route: {q['start']} -> {q['end']} (mode: {q['mode']})",
           f"Stations ({len(summary['path'])}): " + " -> ".join(summary["path"]),
           f"Total distance: {format_distance(summary['distance_m'])}",
           f"Transfers: {summary['transfer_count']}",
           f"Estimated time: {summary['estimated_time_min']} min",
           "Lines: " + ", ".join(summary["lines"]),
           "Segments:"]
    for s in summary["segments"]:
        out.append(f"  [{s['line']}] {s['from']} -> {s['to']} ({s['stops']} stops)")
    for t in summary["transfers"]:
        out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append(f"Fare: {summary['fare']} yuan")
    return "\n".join(out)
