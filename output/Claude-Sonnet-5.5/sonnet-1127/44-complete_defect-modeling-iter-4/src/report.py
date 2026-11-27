"""Route building and report generation."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, stations, edges, total_distance, transfer_count,
                 involved_lines, estimated_time, transfer_stations, segments):
        self.stationSequence = stations
        self.edges = edges
        self.totalDistance = total_distance
        self.transferCount = transfer_count
        self.involvedLines = involved_lines
        self.estimatedTime = estimated_time
        self.transferStations = transfer_stations
        self.segments = segments  # list of (line, [stations])


def build_route(network, sp, target):
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise ValueError("no path")
    names = [network.number_to_station[n] for n in nodes]
    total = sum(e.distance for e in edges)
    lines, segments, transfers = [], [], []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if segments and segments[-1][0] == e.line:
            segments[-1][1].append(names[i + 1])
        else:
            if segments:
                transfers.append(names[i])
            segments.append((e.line, [names[i], names[i + 1]]))
    t = len(transfers)
    return Route(names, edges, total, t, lines,
                 calculate_estimated_time(total, t), transfers, segments)


def format_distance(meters):
    if meters < 1000:
        return "%d meters" % meters
    return "%.2f km" % (meters / 1000.0)


def text_report(route, fare, start, end):
    out = ["Route: %s -> %s" % (start, end),
           "Stations (%d): %s" % (len(route.stationSequence), " -> ".join(route.stationSequence)),
           "Total distance: %s (%.2f km)" % (format_distance(route.totalDistance), route.totalDistance / 1000.0)]
    for line, sts in route.segments:
        out.append("  [%s] %s -> %s (%d stops)" % (line, sts[0], sts[-1], len(sts) - 1))
    if route.transferStations:
        out.append("Transfers: %d at %s" % (route.transferCount, ", ".join(route.transferStations)))
    else:
        out.append("Transfers: 0")
    out.append("Lines: %s" % ", ".join(route.involvedLines))
    out.append("Estimated time: %.1f minutes" % route.estimatedTime)
    out.append("Fare: %d yuan" % fare)
    return "\n".join(out)


def json_report(route, fare, start, end, mode):
    return json.dumps({
        "query": {"start": start, "end": end, "mode": mode},
        "path": route.stationSequence,
        "distance_meters": route.totalDistance,
        "distance_km": round(route.totalDistance / 1000.0, 2),
        "fare": fare,
        "estimated_time": route.estimatedTime,
        "transfer_count": route.transferCount,
        "transfer_stations": route.transferStations,
        "lines": route.involvedLines,
    }, ensure_ascii=False, indent=2)


def make_report(route, fare, start, end, mode, fmt="text"):
    if fmt == "json":
        return json_report(route, fare, start, end, mode)
    return text_report(route, fare, start, end)
