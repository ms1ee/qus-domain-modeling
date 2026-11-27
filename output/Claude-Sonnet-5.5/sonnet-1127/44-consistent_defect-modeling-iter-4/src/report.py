"""Route, RouteSummary and ReportExporter."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, stations, edges, transfer_stations=None):
        self.stations = stations
        self.edges = edges
        self.totalDistance = sum(e.distance for e in edges)
        self.transfer_stations = transfer_stations or []
        self.transferCount = len(self.transfer_stations)
        lines = []
        for e in edges:
            if e.line not in lines:
                lines.append(e.line)
        self.involvedLines = lines

    def segments(self):
        """List of (line, first station, last station)."""
        segs = []
        for i, e in enumerate(self.edges):
            if segs and segs[-1][0] == e.line:
                segs[-1][2] = self.stations[i + 1]
            else:
                segs.append([e.line, self.stations[i], self.stations[i + 1]])
        return segs


class RouteSummary:
    def __init__(self, route):
        self.route = route
        self.totalDistance = route.totalDistance
        self.transferCount = route.transferCount
        self.fare = Sum_money(route.totalDistance)
        self.estimatedTime = calculate_estimated_time(route.totalDistance, route.transferCount)


def format_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km" % (d / 1000.0)


class ReportExporter:
    def __init__(self, fmt="text", output_file=None):
        self.format = fmt
        self.outputFile = output_file

    def render(self, start, end, mode, summary):
        return self.render_json(start, end, mode, summary) if self.format == "json" \
            else self.render_text(start, end, mode, summary)

    def render_text(self, start, end, mode, summary):
        r = summary.route
        out = ["Route: %s -> %s (mode: %s)" % (start, end, mode),
               "Stations (%d): %s" % (len(r.stations), " -> ".join(r.stations)),
               "Segments:"]
        for line, a, b in r.segments():
            out.append("  [%s] %s -> %s" % (line, a, b))
        out.append("Distance: %d m (%s)" % (r.totalDistance, format_distance(r.totalDistance)))
        if r.transfer_stations:
            out.append("Transfers (%d): %s" % (r.transferCount, ", ".join(r.transfer_stations)))
        else:
            out.append("Transfers: 0")
        out.append("Lines: %s" % ", ".join(r.involvedLines))
        out.append("Estimated time: %.1f minutes" % summary.estimatedTime)
        out.append("Fare: %d yuan" % summary.fare)
        return "\n".join(out)

    def render_json(self, start, end, mode, summary):
        r = summary.route
        return json.dumps({
            "query": {"start": start, "end": end, "mode": mode},
            "path": r.stations,
            "distance": r.totalDistance,
            "fare": summary.fare,
            "estimated_time": round(summary.estimatedTime, 1),
            "transfer_count": r.transferCount,
            "transfer_stations": r.transfer_stations,
            "lines": r.involvedLines,
        }, ensure_ascii=False, indent=2)

    def export(self, content):
        if self.outputFile:
            with open(self.outputFile, "a", encoding="utf-8") as f:
                f.write(content + "\n")
