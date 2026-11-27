"""Route report generation."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def build_summary(network, start, end, nodes, edges):
    dist = sum(e.weight for e in edges)
    transfers = []
    for a, b in zip(edges, edges[1:]):
        if a.line != b.line:
            transfers.append({"station": network.number_to_station[a.dest],
                              "from_line": a.line, "to_line": b.line})
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    fare = Sum_money(dist)
    return {
        "query": {"start": start, "end": end},
        "path": [network.number_to_station[n] for n in nodes],
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": calculate_estimated_time(dist, len(transfers)),
        "transfer_count": len(transfers),
        "transfers": transfers,
        "lines": lines,
        "segments": _segments(network, edges),
    }


def _segments(network, edges):
    segs = []
    for e in edges:
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = network.number_to_station[e.dest]
            segs[-1]["stations"] += 1
        else:
            segs.append({"line": e.line, "from": network.number_to_station[e.source],
                         "to": network.number_to_station[e.dest], "stations": 1})
    return segs


def format_text(s):
    out = [f"Route: {s['query']['start']} -> {s['query']['end']}",
           "Stations: " + " -> ".join(s["path"])]
    d = s["distance_m"]
    out.append(f"Total distance: {d} m ({s['distance_km']} km)")
    for seg in s["segments"]:
        out.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} ({seg['stations']} stops)")
    if s["transfers"]:
        for t in s["transfers"]:
            out.append(f"Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("No transfers")
    out.append("Lines: " + ", ".join(s["lines"]))
    out.append(f"Transfers: {s['transfer_count']}")
    out.append(f"Estimated time: {s['estimated_time_min']} minutes")
    out.append(f"Fare: {s['fare']} yuan")
    return "\n".join(out)


def format_json(s):
    return json.dumps(s, ensure_ascii=False, indent=2)
