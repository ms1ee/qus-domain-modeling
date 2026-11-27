"""Route construction, summaries and report formatting."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, stations, edges, total_distance, transfer_count):
        self.stations = stations
        self.edges = edges
        self.total_distance = total_distance
        self.transfer_count = transfer_count
        self.involved_lines = []
        for e in edges:
            if e.line not in self.involved_lines:
                self.involved_lines.append(e.line)

    def segments(self):
        """List of (line, [station names]) grouped by consecutive line."""
        segs = []
        for i, e in enumerate(self.edges):
            if not segs or segs[-1][0] != e.line:
                segs.append([e.line, [self.stations[i]]])
            segs[-1][1].append(self.stations[i + 1])
        return segs

    def transfer_stations(self):
        segs = self.segments()
        return [(segs[i][1][-1], segs[i][0], segs[i + 1][0]) for i in range(len(segs) - 1)]


def format_distance(meters):
    if meters < 1000:
        return "%d m" % meters
    return "%.2f km" % (meters / 1000.0)


def summary(route):
    return {
        "total_distance_km": round(route.total_distance / 1000.0, 2),
        "total_fare": Sum_money(route.total_distance),
        "transfer_count": route.transfer_count,
        "estimated_time": round(calculate_estimated_time(route.total_distance, route.transfer_count), 1),
    }


def to_text(route, start, end):
    s = summary(route)
    out = ["Route: %s -> %s" % (start, end),
           "Stations: " + " -> ".join(route.stations)]
    for line, sts in route.segments():
        out.append("  [%s] %s -> %s (%d stops)" % (line, sts[0], sts[-1], len(sts) - 1))
    out.append("Total distance: %s (%d m / %.2f km)" % (
        format_distance(route.total_distance), route.total_distance, s["total_distance_km"]))
    ts = route.transfer_stations()
    if ts:
        out.append("Transfers (%d):" % len(ts))
        for st, a, b in ts:
            out.append("  %s: %s -> %s" % (st, a, b))
    else:
        out.append("Transfers: none")
    out.append("Lines: " + ", ".join(str(l) for l in route.involved_lines))
    out.append("Estimated time: %.1f minutes" % s["estimated_time"])
    out.append("Fare: %d yuan" % s["total_fare"])
    return "\n".join(out)


def to_json(route, start, end, mode=None, max_transfers=None, line_preference=None):
    s = summary(route)
    d = {
        "query": {"start": start, "end": end, "mode": mode,
                  "max_transfers": max_transfers, "line_preference": line_preference},
        "path": route.stations,
        "distance": route.total_distance,
        "distance_km": s["total_distance_km"],
        "fare": s["total_fare"],
        "estimated_time": s["estimated_time"],
        "transfer_count": route.transfer_count,
        "transfer_stations": [{"station": a, "from_line": b, "to_line": c}
                              for a, b, c in route.transfer_stations()],
        "lines": route.involved_lines,
    }
    return json.dumps(d, ensure_ascii=False, indent=2)
