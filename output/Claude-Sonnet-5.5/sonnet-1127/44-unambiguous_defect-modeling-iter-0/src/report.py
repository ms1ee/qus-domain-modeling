"""Route report generation (text / json) and summaries."""
import json
from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(m):
    return "%d meters (%.2f km)" % (round(m), m / 1000.0)


def summarize(route):
    return {
        "distance_m": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 2),
        "fare": Sum_money(route.total_distance),
        "transfer_count": route.transfer_count,
        "estimated_time": round(calculate_estimated_time(route.total_distance, route.transfer_count), 1),
    }


def segments(route):
    segs = []
    for e, name in zip(route.edges, route.stations[1:]):
        if segs and segs[-1]["line"] == e.line:
            segs[-1]["to"] = name
            segs[-1]["stations"] += 1
        else:
            segs.append({"line": e.line, "from": route.stations[len(route.stations) - 1 - 0] if False else None,
                         "to": name, "stations": 1})
    # fill 'from'
    idx = 0
    for s in segs:
        s["from"] = route.stations[idx]
        idx += s["stations"]
    return segs


class RouteReport:
    def __init__(self, query, route, fmt="text", output_file=None):
        self.query = query
        self.route = route
        self.format = fmt
        self.output_file = output_file
        self.summary = summarize(route)

    def to_text(self):
        r, s = self.route, self.summary
        out = ["Route: %s -> %s" % (self.query.start, self.query.end),
               "Stations (%d): %s" % (len(r.stations), " -> ".join(r.stations)),
               "Distance: " + format_distance(r.total_distance)]
        for seg in segments(r):
            out.append("  [%s] %s -> %s (%d stops)" % (seg["line"], seg["from"], seg["to"], seg["stations"]))
        if r.transfer_stations:
            out.append("Transfers (%d): %s" % (r.transfer_count, "; ".join(
                "%s (%s -> %s)" % t for t in r.transfer_stations)))
        else:
            out.append("Transfers: 0")
        out.append("Lines: " + ", ".join(r.lines))
        out.append("Estimated time: %.0f minutes" % s["estimated_time"])
        out.append("Fare: %d yuan" % s["fare"])
        return "\n".join(out)

    def to_json(self):
        r, s = self.route, self.summary
        return json.dumps({
            "query": {"start": self.query.start, "end": self.query.end, "mode": self.query.mode,
                      "max_transfers": self.query.max_transfers,
                      "line_preference": self.query.line_preference},
            "path": r.stations,
            "distance_m": s["distance_m"],
            "distance_km": s["distance_km"],
            "fare": s["fare"],
            "estimated_time": s["estimated_time"],
            "transfer_count": s["transfer_count"],
            "transfer_stations": [t[0] for t in r.transfer_stations],
            "lines": r.lines,
            "segments": segments(r),
        }, ensure_ascii=False, indent=2)

    def render(self):
        return self.to_json() if self.format == "json" else self.to_text()
