"""Route reports (text / JSON)."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


def build_report(system, start, end, route):
    nodes, edges = route["nodes"], route["edges"]
    names = [system.number_to_station[n] for n in nodes]
    segments = []
    transfers = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = names[i + 1]
            segments[-1]["distance"] += e.distance
            segments[-1]["stops"] += 1
        else:
            if segments:
                transfers.append({"station": names[i], "from_line": segments[-1]["line"],
                                  "to_line": e.line})
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                             "distance": e.distance, "stops": 1})
    dist = route["distance"]
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "distance_m": dist,
        "distance_km": round(dist / 1000.0, 2),
        "fare": Sum_money(dist),
        "estimated_time_min": calculate_estimated_time(dist, route["transfers"]),
        "transfer_count": route["transfers"],
        "lines": sorted({s["line"] for s in segments}),
        "segments": segments,
        "transfers": transfers,
    }


def format_json(rep):
    return json.dumps(rep, ensure_ascii=False, indent=2)


def format_text(rep):
    L = ["Route: %s -> %s" % (rep["query"]["start"], rep["query"]["end"]),
         "Stations (%d): %s" % (len(rep["path"]), " -> ".join(rep["path"])),
         "Total distance: %d m (%.2f km)" % (rep["distance_m"], rep["distance_km"])]
    for s in rep["segments"]:
        L.append("  [%s] %s -> %s (%d stops, %d m)" % (s["line"], s["from"], s["to"], s["stops"], s["distance"]))
    if rep["transfers"]:
        for t in rep["transfers"]:
            L.append("Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    else:
        L.append("No transfers")
    L.append("Transfers: %d" % rep["transfer_count"])
    L.append("Lines: %s" % ", ".join(rep["lines"]))
    L.append("Estimated time: %.1f minutes" % rep["estimated_time_min"])
    L.append("Fare: %d yuan" % rep["fare"])
    return "\n".join(L)
