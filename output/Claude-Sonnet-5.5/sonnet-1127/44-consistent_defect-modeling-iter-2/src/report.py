"""Route, RouteReport, Query."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


class Query:
    def __init__(self, start_station, end_station, mode="shortest_distance",
                 max_transfers=None, line_preference=None):
        self.start_station = start_station
        self.end_station = end_station
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference


class Route:
    def __init__(self, stations, total_distance, transfer_count, involved_lines,
                 transfer_stations=None, segments=None):
        self.stations = stations
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.involved_lines = involved_lines
        self.transfer_stations = transfer_stations or []
        self.segments = segments or []  # (line, first, last)


def build_route(graph, nodes, edges):
    names = [graph.number_to_station[n] for n in nodes]
    lines, tstations, segs = [], [], []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if i > 0 and edges[i - 1].line != e.line:
            tstations.append(names[i])
        if not segs or segs[-1][0] != e.line or (i > 0 and edges[i - 1].line != e.line):
            segs.append([e.line, names[i], names[i + 1]])
        else:
            segs[-1][2] = names[i + 1]
    return Route(names, sum(e.distance for e in edges), len(tstations), lines, tstations,
                 [tuple(s) for s in segs])


def format_distance(d):
    if d < 1000:
        return "%d m" % d
    return "%.2f km (%d m)" % (d / 1000, d)


class RouteReport:
    def __init__(self, route, query=None, fmt="text", output_file=None):
        self.route = route
        self.query = query
        self.format = fmt
        self.output_file = output_file
        self.fare = Sum_money(route.total_distance)
        self.estimated_time = calculate_estimated_time(route.total_distance, route.transfer_count)

    def summary(self):
        return {"distance": self.route.total_distance, "fare": self.fare,
                "transfer_count": self.route.transfer_count,
                "estimated_time": self.estimated_time}

    def to_text(self):
        r = self.route
        out = []
        if self.query:
            out.append("Route: %s -> %s (mode: %s)" % (self.query.start_station,
                                                       self.query.end_station, self.query.mode))
        out.append("Stations (%d): %s" % (len(r.stations), " -> ".join(r.stations)))
        for line, a, b in r.segments:
            out.append("  [%s] %s -> %s" % (line, a, b))
        out.append("Total distance: %s" % format_distance(r.total_distance))
        if r.transfer_stations:
            out.append("Transfers (%d): %s" % (r.transfer_count, ", ".join(r.transfer_stations)))
        else:
            out.append("Transfers: 0")
        out.append("Lines: %s" % ", ".join(r.involved_lines))
        out.append("Estimated time: %.1f minutes" % self.estimated_time)
        out.append("Fare: %d yuan" % self.fare)
        return "\n".join(out)

    def to_json(self):
        r = self.route
        q = self.query
        return json.dumps({
            "query": {"start": q.start_station, "end": q.end_station, "mode": q.mode,
                      "max_transfers": q.max_transfers,
                      "line_preference": q.line_preference} if q else None,
            "path": r.stations,
            "distance": r.total_distance,
            "fare": self.fare,
            "estimated_time": self.estimated_time,
            "transfer_count": r.transfer_count,
            "transfer_stations": r.transfer_stations,
            "lines": r.involved_lines,
        }, ensure_ascii=False, indent=2)

    def render(self):
        return self.to_json() if self.format == "json" else self.to_text()

    def save(self):
        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(self.render() + "\n")
