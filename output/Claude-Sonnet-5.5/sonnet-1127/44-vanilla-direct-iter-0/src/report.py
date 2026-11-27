"""Route report generation (text and JSON)."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def _fmt_distance(m):
    if m < 1000:
        return "%d m" % m
    return "%.2f km" % (m / 1000.0)


def build_summary(start, end, nodes, edges, n2s):
    total = sum(e.distance for e in edges)
    stations = [n2s[n] for n in nodes]
    segments = []
    transfers = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = n2s[e.dest]
            segments[-1]["distance"] += e.distance
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfers.append({"station": n2s[e.source],
                                  "from_line": segments[-1]["line"], "to_line": e.line})
            segments.append({"line": e.line, "from": n2s[e.source], "to": n2s[e.dest],
                             "distance": e.distance, "stations": 1})
    tc = len(transfers)
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": start, "end": end},
        "path": stations,
        "distance_meters": total,
        "distance_km": round(total / 1000.0, 2),
        "distance_text": _fmt_distance(total),
        "fare": Sum_money(total),
        "estimated_time_minutes": round(calculate_estimated_time(total, tc), 1),
        "transfer_count": tc,
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
    }


def format_text(s):
    out = ["Route: %s -> %s" % (s["query"]["start"], s["query"]["end"]),
           "Stations (%d): %s" % (len(s["path"]), " -> ".join(s["path"])),
           "Total distance: %s" % s["distance_text"]]
    for seg in s["segments"]:
        out.append("  [%s] %s -> %s (%d stops, %s)" % (
            seg["line"], seg["from"], seg["to"], seg["stations"], _fmt_distance(seg["distance"])))
    out.append("Transfers: %d" % s["transfer_count"])
    for t in s["transfers"]:
        out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("Lines: %s" % ", ".join(s["lines"]))
    out.append("Estimated time: %.1f minutes" % s["estimated_time_minutes"])
    out.append("Fare: %d yuan" % s["fare"])
    return "\n".join(out)


def format_json(s):
    return json.dumps(s, ensure_ascii=False, indent=2)
