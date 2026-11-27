"""Route construction and report generation."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


class TransferInfo:
    def __init__(self, station_name, line_names):
        self.station_name = station_name
        self.line_names = line_names


class Route:
    def __init__(self, stations, total_distance, transfers, lines, segments, estimated_time):
        self.station_sequence = stations
        self.total_distance = total_distance
        self.transfers = transfers
        self.transfer_count = len(transfers)
        self.involved_lines = lines
        self.segments = segments  # list of (line, [stations])
        self.estimated_time = estimated_time


def build_route(graph, nodes, edges):
    names = [graph.number_to_station[n] for n in nodes]
    total = sum(e.distance for e in edges)
    transfers, lines, segments = [], [], []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if segments and segments[-1][0] == e.line:
            segments[-1][1].append(names[i + 1])
        else:
            segments.append((e.line, [names[i], names[i + 1]]))
        if i + 1 < len(edges) and edges[i + 1].line != e.line:
            transfers.append(TransferInfo(names[i + 1], [e.line, edges[i + 1].line]))
    return Route(names, total, transfers, lines, segments,
                 calculate_estimated_time(total, len(transfers)))


def format_distance(meters):
    if meters < 1000:
        return "%d m" % meters
    return "%.2f km (%d m)" % (meters / 1000.0, meters)


def text_report(start, end, route, fare):
    out = ["Route: %s -> %s" % (start, end),
           "Stations (%d): %s" % (len(route.station_sequence), " -> ".join(route.station_sequence)),
           "Total distance: %s" % format_distance(route.total_distance)]
    for line, sts in route.segments:
        out.append("  [%s] %s -> %s (%d stops)" % (line, sts[0], sts[-1], len(sts) - 1))
    if route.transfers:
        for t in route.transfers:
            out.append("Transfer at %s: %s" % (t.station_name, " -> ".join(t.line_names)))
    else:
        out.append("No transfers")
    out.append("Lines: %s" % ", ".join(route.involved_lines))
    out.append("Transfers: %d" % route.transfer_count)
    out.append("Estimated time: %.1f minutes" % route.estimated_time)
    out.append("Fare: %d yuan" % fare)
    return "\n".join(out)


def json_report(start, end, mode, route, fare):
    d = {
        "query": {"start": start, "end": end, "mode": mode},
        "path": route.station_sequence,
        "distance_m": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 2),
        "fare": fare,
        "estimated_time_min": route.estimated_time,
        "transfer_count": route.transfer_count,
        "transfers": [{"station": t.station_name, "lines": t.line_names} for t in route.transfers],
        "lines": route.involved_lines,
    }
    return json.dumps(d, ensure_ascii=False, indent=2)


def generate(start, end, mode, route, fmt):
    fare = Sum_money(route.total_distance)
    if fmt == "json":
        return json_report(start, end, mode, route, fare)
    return text_report(start, end, route, fare)
