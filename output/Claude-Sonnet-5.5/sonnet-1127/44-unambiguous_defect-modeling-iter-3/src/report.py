"""Route, Query and PathReport."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


class Query:
    def __init__(self, start, end, mode="shortest_distance", max_transfers=None, line_preference=None):
        self.start = start
        self.end = end
        self.mode = mode
        self.max_transfers = max_transfers
        self.line_preference = line_preference


class Route:
    def __init__(self, stations, total_distance, edges):
        self.stations = stations
        self.total_distance = total_distance
        self.edges = edges
        self.transfers = []  # (station, from_line, to_line)
        for i in range(1, len(edges)):
            if edges[i].line != edges[i - 1].line:
                self.transfers.append((stations[i], edges[i - 1].line, edges[i].line))
        self.transfer_count = len(self.transfers)
        self.involved_lines = []
        for e in edges:
            if e.line not in self.involved_lines:
                self.involved_lines.append(e.line)

    def segments(self):
        segs = []
        for i, e in enumerate(self.edges):
            if segs and segs[-1]["line"] == e.line:
                segs[-1]["to"] = self.stations[i + 1]
                segs[-1]["count"] += 1
            else:
                segs.append({"line": e.line, "from": self.stations[i],
                             "to": self.stations[i + 1], "count": 1})
        return segs


class PathReport:
    def __init__(self, query, route, fmt="text"):
        self.query = query
        self.route = route
        self.format = fmt
        d = route.total_distance
        self.distance_km = round(d / 1000.0, 2)
        self.fare = Sum_money(d)
        self.estimated_time = calculate_estimated_time(d, route.transfer_count)

    def distance_text(self):
        d = self.route.total_distance
        return "%d m (%.2f km)" % (d, d / 1000.0)

    def to_dict(self):
        r = self.route
        return {
            "query": {"start": self.query.start, "end": self.query.end,
                      "mode": self.query.mode, "max_transfers": self.query.max_transfers,
                      "line_preference": self.query.line_preference},
            "path": r.stations,
            "distance_meters": r.total_distance,
            "distance_km": self.distance_km,
            "fare": self.fare,
            "estimated_time_minutes": self.estimated_time,
            "transfer_count": r.transfer_count,
            "transfers": [{"station": s, "from_line": a, "to_line": b} for s, a, b in r.transfers],
            "lines": r.involved_lines,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_text(self):
        r = self.route
        out = ["Route: %s -> %s (mode: %s)" % (self.query.start, self.query.end, self.query.mode),
               "Stations (%d): %s" % (len(r.stations), " -> ".join(r.stations)),
               "Segments:"]
        for s in r.segments():
            out.append("  %s: %s -> %s (%d stops)" % (s["line"], s["from"], s["to"], s["count"]))
        out.append("Total distance: %s" % self.distance_text())
        out.append("Transfers: %d" % r.transfer_count)
        for s, a, b in r.transfers:
            out.append("  Transfer at %s: %s -> %s" % (s, a, b))
        out.append("Lines: %s" % ", ".join(r.involved_lines))
        out.append("Estimated time: %.0f minutes" % self.estimated_time)
        out.append("Fare: %d yuan" % self.fare)
        return "\n".join(out)

    def render(self):
        return self.to_json() if self.format == "json" else self.to_text()
