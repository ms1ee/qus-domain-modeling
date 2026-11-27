"""Route query and report generation."""
import json
from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import ShortestPath


def format_distance(m):
    if m < 1000:
        return "%d meters" % m
    return "%.2f km (%d meters)" % (m / 1000.0, m)


def query_route(network, start, end, config):
    s = network.station_to_number[start]
    t = network.station_to_number[end]
    sp = ShortestPath(network.graph, s, config)
    nodes, edges = sp.path_with_edges(t)
    if not nodes:
        raise RuntimeError("No route found from '%s' to '%s' (check max transfers)" % (start, end))
    total = sp.dist_to[t]
    transfers = sp.get_transfer_count(t)
    try:
        fare = Sum_money(total)
    except Exception as e:
        raise ArithmeticError("Fare calculation failed: %s" % e)
    segments = []
    transfer_stations = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = network.number_to_station[e.dest]
            segments[-1]["stops"] += 1
        else:
            if segments:
                transfer_stations.append(network.number_to_station[e.source])
            segments.append({"line": e.line, "from": network.number_to_station[e.source],
                             "to": network.number_to_station[e.dest], "stops": 1})
    lines = []
    for sg in segments:
        if sg["line"] not in lines:
            lines.append(sg["line"])
    return {
        "query": {"start": start, "end": end, "mode": config.mode},
        "path": [network.number_to_station[n] for n in nodes],
        "distance_m": total,
        "distance_km": round(total / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": round(calculate_estimated_time(total, transfers), 1),
        "transfer_count": transfers,
        "transfer_stations": transfer_stations,
        "lines": lines,
        "segments": segments,
    }


def format_text(r):
    out = ["Route: %s -> %s (mode: %s)" % (r["query"]["start"], r["query"]["end"], r["query"]["mode"]),
           "Stations (%d): %s" % (len(r["path"]), " -> ".join(r["path"])),
           "Total distance: %s" % format_distance(r["distance_m"]),
           "Segments:"]
    for sg in r["segments"]:
        out.append("  %s: %s -> %s (%d stops)" % (sg["line"], sg["from"], sg["to"], sg["stops"]))
    if r["transfer_stations"]:
        out.append("Transfers at: %s" % ", ".join(r["transfer_stations"]))
    out.append("Transfer count: %d" % r["transfer_count"])
    out.append("Lines involved: %s" % ", ".join(r["lines"]))
    out.append("Estimated time: %.0f minutes" % r["estimated_time_min"])
    out.append("Fare: %d yuan" % r["fare"])
    return "\n".join(out)


def format_json(r):
    return json.dumps(r, ensure_ascii=False, indent=2)
