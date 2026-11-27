"""Route reports and summaries."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(d):
    if d < 1000:
        return "%d m" % d
    return "%.2f km (%d m)" % (d / 1000.0, d)


def build_result(network, src, dst, path, edges, transfers):
    names = [network.number_to_station[n] for n in path]
    dist = sum(e.distance for e in edges)
    segments = []
    transfer_stations = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = network.number_to_station[e.dest]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfer_stations.append(network.number_to_station[e.source])
            segments.append({"line": e.line, "from": network.number_to_station[e.source],
                             "to": network.number_to_station[e.dest], "stations": 1})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    return {
        "query": {"start": src, "end": dst},
        "path": names,
        "segments": segments,
        "transfer_stations": transfer_stations,
        "distance": dist,
        "fare": Sum_money(dist),
        "estimated_time": round(calculate_estimated_time(dist, transfers), 1),
        "transfer_count": transfers,
        "lines": lines,
    }


def to_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def to_text(result):
    out = []
    q = result["query"]
    out.append("Route: %s -> %s" % (q["start"], q["end"]))
    out.append("Stations (%d): %s" % (len(result["path"]), " -> ".join(result["path"])))
    for s in result["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (s["line"], s["from"], s["to"], s["stations"]))
    if result["transfer_stations"]:
        out.append("Transfers at: %s" % ", ".join(result["transfer_stations"]))
    out.append("Lines: %s" % ", ".join(result["lines"]))
    out.append("Total distance: %s" % format_distance(result["distance"]))
    out.append("Transfer count: %d" % result["transfer_count"])
    out.append("Estimated time: %.1f minutes" % result["estimated_time"])
    out.append("Fare: %d yuan" % result["fare"])
    return "\n".join(out)
