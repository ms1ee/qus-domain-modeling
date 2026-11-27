"""Route reports: text and JSON."""
import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import ShortestPath, PathfindingConfig


class Route:
    def __init__(self, stations, edges, total_distance, transfer_count, involved_lines):
        self.station_sequence = stations
        self.edges = edges
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.involved_lines = involved_lines


def build_route(graph, start, end, config):
    s, e = graph.station_to_number[start], graph.station_to_number[end]
    sp = ShortestPath(graph, s, config)
    if e not in sp.dist_to:
        raise ValueError("No route found between %s and %s" % (start, end))
    nodes, edges = sp.path_with_edges(e)
    lines = []
    for ed in edges:
        if ed.line not in lines:
            lines.append(ed.line)
    names = [graph.number_to_station[n] for n in nodes]
    return Route(names, edges, sp.dist_to[e], sp.get_transfer_count(e), lines)


def segments(route):
    """Group consecutive edges by line -> list of (line, from, to, stops)."""
    segs = []
    names = route.station_sequence
    for i, ed in enumerate(route.edges):
        if segs and segs[-1][0] == ed.line:
            segs[-1][2] = names[i + 1]
            segs[-1][3] += 1
        else:
            segs.append([ed.line, names[i], names[i + 1], 1])
    return segs


def summary(route, query):
    fare = Sum_money(route.total_distance)
    t = calculate_estimated_time(route.total_distance, route.transfer_count)
    segs = segments(route)
    transfers = [segs[i][2] for i in range(len(segs) - 1)]
    return {
        "query": query,
        "path": route.station_sequence,
        "distance_meters": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_minutes": round(t),
        "transfer_count": route.transfer_count,
        "transfer_stations": transfers,
        "lines": route.involved_lines,
        "segments": [{"line": s[0], "from": s[1], "to": s[2], "stops": s[3]} for s in segs],
    }


def format_text(info):
    q = info["query"]
    out = ["Route: %s -> %s (mode: %s)" % (q["start"], q["end"], q["mode"])]
    out.append("Stations (%d): %s" % (len(info["path"]), " -> ".join(info["path"])))
    m = info["distance_meters"]
    out.append("Distance: %d m (%.2f km)" % (m, m / 1000.0))
    for s in info["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (s["line"], s["from"], s["to"], s["stops"]))
    if info["transfer_stations"]:
        out.append("Transfers: %d at %s" % (info["transfer_count"],
                                            ", ".join(info["transfer_stations"])))
    else:
        out.append("Transfers: 0")
    out.append("Lines: " + ", ".join(info["lines"]))
    out.append("Estimated time: %d minutes" % info["estimated_time_minutes"])
    out.append("Fare: %d yuan" % info["fare"])
    return "\n".join(out)


def format_json(info):
    return json.dumps(info, ensure_ascii=False, indent=2)


def render(info, fmt):
    return format_json(info) if fmt == "json" else format_text(info)
