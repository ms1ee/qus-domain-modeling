"""Report generation (text and JSON)."""
import json


def format_distance(d):
    return "%d m" % d if d < 1000 else "%.2f km" % (d / 1000.0)


class Report:
    def __init__(self, query, route, summary, fmt="text", output_file=None):
        self.query = query
        self.route = route
        self.summary = summary
        self.format = fmt
        self.output_file = output_file
        self.content = self.render()

    def render(self):
        return self.to_json() if self.format == "json" else self.to_text()

    def to_text(self):
        r, s = self.route, self.summary
        out = ["Route: %s -> %s" % (self.query.start_station, self.query.end_station),
               "Stations (%d): %s" % (len(r.stations), " -> ".join(r.stations))]
        for line, sts in r.segments:
            out.append("  [%s] %s -> %s (%d stops)" % (line, sts[0], sts[-1], len(sts) - 1))
        out.append("Distance: %d m (%.2f km) [%s]" % (r.total_distance, r.total_distance / 1000.0,
                                                    format_distance(r.total_distance)))
        out.append("Transfers: %d%s" % (r.transfer_count,
                   " (at " + ", ".join(r.transfer_stations) + ")" if r.transfer_stations else ""))
        out.append("Lines: %s" % ", ".join(r.lines_involved))
        out.append("Estimated time: %.1f minutes" % s.estimated_time)
        out.append("Fare: %d yuan" % s.fare)
        return "\n".join(out)

    def to_json(self):
        r, s = self.route, self.summary
        return json.dumps({
            "query": {"start": self.query.start_station, "end": self.query.end_station,
                      "mode": self.query.mode, "max_transfers": self.query.max_transfers,
                      "line_preference": self.query.line_preference},
            "path": r.stations,
            "distance": r.total_distance,
            "fare": s.fare,
            "estimated_time": s.estimated_time,
            "transfer_count": r.transfer_count,
            "transfer_stations": r.transfer_stations,
            "lines": r.lines_involved,
        }, ensure_ascii=False, indent=2)

    def save(self):
        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(self.content + "\n")
