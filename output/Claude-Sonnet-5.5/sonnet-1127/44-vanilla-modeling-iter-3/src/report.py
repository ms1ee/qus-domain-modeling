"""Route analysis, report generation and export."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return "%d m" % meters
    return "%.2f km" % (meters / 1000.0)


def build_summary(dm, start, end, nodes, edges):
    names = [dm.number_to_station[n] for n in nodes]
    total = sum(e.distance for e in edges)
    segments = []
    transfers = []
    for i, e in enumerate(edges):
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["to"] = dm.number_to_station[e.dest]
            segments[-1]["stations"] += 1
        else:
            if segments:
                transfers.append(dm.number_to_station[e.source])
            segments.append({"line": e.line, "from": dm.number_to_station[e.source],
                             "to": dm.number_to_station[e.dest], "stations": 1})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    tc = len(transfers)
    return {
        "query": {"start": start, "end": end},
        "path": names,
        "distance_m": total,
        "distance_km": round(total / 1000.0, 2),
        "fare": Sum_money(total),
        "estimated_time_min": round(calculate_estimated_time(total, tc), 1),
        "transfer_count": tc,
        "transfer_stations": transfers,
        "lines": lines,
        "segments": segments,
    }


def render(summary, fmt="text"):
    if fmt == "json":
        return json.dumps(summary, ensure_ascii=False, indent=2)
    q = summary["query"]
    out = ["Route: %s -> %s" % (q["start"], q["end"]),
           "Stations (%d): %s" % (len(summary["path"]), " -> ".join(summary["path"])),
           "Total distance: %s" % format_distance(summary["distance_m"]),
           "Lines: %s" % ", ".join(summary["lines"]),
           "Transfers: %d" % summary["transfer_count"]]
    for s in summary["segments"]:
        out.append("  [%s] %s -> %s (%d stops)" % (s["line"], s["from"], s["to"], s["stations"]))
    for t in summary["transfer_stations"]:
        out.append("  Transfer at: %s" % t)
    out.append("Estimated time: %.1f minutes" % summary["estimated_time_min"])
    out.append("Fare: %d yuan" % summary["fare"])
    return "\n".join(out)


class ReportExporter:
    def __init__(self, fmt="text", output_file=None):
        self.format = fmt
        self.output_file = output_file

    def export(self, summary):
        text = render(summary, self.format)
        if self.output_file:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(text + "\n\n")
        return text
