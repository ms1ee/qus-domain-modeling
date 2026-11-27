"""Route reports: text and JSON."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, station_sequence, total_distance, transfer_count, involved_lines, edges):
        self.station_sequence = station_sequence
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.involved_lines = involved_lines
        self.edges = edges


class PathSummary:
    def __init__(self, route):
        self.route = route
        self.total_distance = route.total_distance
        self.fare = Sum_money(route.total_distance)
        self.transfer_count = route.transfer_count
        self.estimated_time = calculate_estimated_time(route.total_distance, route.transfer_count)


def make_route(names, edges, total):
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    tc = sum(1 for a, b in zip(edges, edges[1:]) if a.line != b.line)
    return Route(names, total, tc, lines, edges)


def _dist_text(m):
    return "%d m" % m if m < 1000 else "%.2f km (%d m)" % (m / 1000.0, m)


class ReportExporter:
    def __init__(self, fmt="text", output_file=None):
        self.format = fmt
        self.output_file = output_file
        self._started = False

    def render(self, start, end, summary, names=None):
        if self.format == "json":
            return self.to_json(start, end, summary)
        return self.to_text(start, end, summary)

    def to_text(self, start, end, summary):
        r = summary.route
        out = ["Route: %s -> %s" % (start, end),
               "Stations (%d): %s" % (len(r.station_sequence), " -> ".join(r.station_sequence))]
        # line segments and transfers
        segs = []
        for i, e in enumerate(r.edges):
            if segs and segs[-1][0] == e.line:
                segs[-1][2] = r.station_sequence[i + 1]
            else:
                segs.append([e.line, r.station_sequence[i], r.station_sequence[i + 1]])
        for line, a, b in segs:
            out.append("  [%s] %s -> %s" % (line, a, b))
        if len(segs) > 1:
            out.append("Transfer stations: " + ", ".join(s[1] for s in segs[1:]))
        out.append("Lines: " + ", ".join(r.involved_lines))
        out.append("Total distance: " + _dist_text(r.total_distance))
        out.append("Transfers: %d" % summary.transfer_count)
        out.append("Estimated time: %.1f minutes" % summary.estimated_time)
        out.append("Fare: %d yuan" % summary.fare)
        return "\n".join(out)

    def to_json(self, start, end, summary):
        r = summary.route
        return json.dumps({
            "query": {"start": start, "end": end},
            "path": r.station_sequence,
            "distance": summary.total_distance,
            "fare": summary.fare,
            "estimated_time": round(summary.estimated_time, 2),
            "transfer_count": summary.transfer_count,
            "lines": r.involved_lines,
        }, ensure_ascii=False, indent=2)

    def export(self, text):
        if not self.output_file:
            return
        mode = "a" if self._started else "w"
        with open(self.output_file, mode, encoding="utf-8") as f:
            f.write(text + "\n")
        self._started = True
