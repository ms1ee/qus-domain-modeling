"""Route computation, summary, and reports."""
import json
from pathfinding import ShortestPath, PathfindingConfig
from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, stations, distance, transfer_count, lines, segments, transfer_stations):
        self.station_sequence = stations
        self.total_distance = distance
        self.transfer_count = transfer_count
        self.lines_involved = lines
        self.segments = segments
        self.transfer_stations = transfer_stations


class RouteQuery:
    def __init__(self, start, end, mode="shortest_distance", max_transfers=None, line_preference=None):
        self.start_station = start
        self.end_station = end
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference


def find_route(network, query):
    pref = [query.line_preference] if query.line_preference else []
    cfg = PathfindingConfig(query.mode, query.max_transfers, pref)
    src = network.station_to_number[query.start_station]
    dst = network.station_to_number[query.end_station]
    sp = ShortestPath(network.graph, src, cfg)
    nodes, edges = sp.path_with_edges(dst)
    if not nodes:
        return None
    names = [network.number_to_station[n] for n in nodes]
    segments = []
    transfers = []
    lines = []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["end"] = names[i + 1]
            segments[-1]["distance"] += e.distance
        else:
            if segments:
                transfers.append(names[i])
            segments.append({"line": e.line, "start": names[i], "end": names[i + 1],
                             "distance": e.distance})
    total = sum(e.distance for e in edges)
    return Route(names, total, len(transfers), lines, segments, transfers)


def format_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km" % (d / 1000.0)


def summarize(route):
    return {"total_distance": route.total_distance,
            "fare": Sum_money(route.total_distance),
            "transfer_count": route.transfer_count,
            "estimated_time": calculate_estimated_time(route.total_distance, route.transfer_count)}


def report_text(query, route):
    s = summarize(route)
    out = ["Route: %s -> %s (mode: %s)" % (query.start_station, query.end_station, query.mode),
           "Stations (%d): %s" % (len(route.station_sequence), " -> ".join(route.station_sequence)),
           "Distance: %s" % format_distance(route.total_distance)]
    for seg in route.segments:
        out.append("  [%s] %s -> %s (%s)" % (seg["line"], seg["start"], seg["end"],
                                             format_distance(seg["distance"])))
    out.append("Transfers: %d%s" % (route.transfer_count,
               " (at " + ", ".join(route.transfer_stations) + ")" if route.transfer_stations else ""))
    out.append("Lines: " + ", ".join(route.lines_involved))
    out.append("Estimated time: %.1f minutes" % s["estimated_time"])
    out.append("Fare: %d yuan" % s["fare"])
    return "\n".join(out)


def report_json(query, route):
    s = summarize(route)
    return json.dumps({
        "query": {"start": query.start_station, "end": query.end_station, "mode": query.mode,
                  "max_transfers": query.max_transfers, "line_preference": query.line_preference},
        "path": route.station_sequence,
        "distance": s["total_distance"],
        "fare": s["fare"],
        "estimated_time": s["estimated_time"],
        "transfer_count": s["transfer_count"],
        "transfer_stations": route.transfer_stations,
        "lines": route.lines_involved,
    }, ensure_ascii=False, indent=2)


class ReportExporter:
    def __init__(self, fmt="text", output_file=None):
        self.format = fmt
        self.output_file = output_file

    def render(self, query, route):
        return report_json(query, route) if self.format == "json" else report_text(query, route)

    def export(self, query, route):
        text = self.render(query, route)
        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        return text
