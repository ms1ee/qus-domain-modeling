"""Path summary and report export."""
import json
from dataclasses import dataclass

from fare_calculator import calculate_estimated_time


@dataclass
class PathSummary:
    total_distance_km: float
    fare: int
    transfer_count: int
    estimated_time: float


def format_distance(meters):
    if meters < 1000:
        return "%d m (%.2f km)" % (meters, meters / 1000.0)
    return "%.2f km (%d m)" % (meters / 1000.0, meters)


def make_summary(route, fare):
    return PathSummary(route.total_distance / 1000.0, fare, route.transfer_count,
                       calculate_estimated_time(route.total_distance, route.transfer_count))


class ReportExporter:
    def __init__(self, format="text", output_file=None):
        self.format = getattr(format, "value", format)
        self.output_file = output_file
        self._written = False

    def render(self, query, route, fare):
        summary = make_summary(route, fare)
        if self.format == "json":
            return json.dumps({
                "query": {"start": query.start_station, "end": query.end_station,
                          "mode": getattr(query.mode, "value", query.mode)},
                "path": route.station_sequence,
                "distance_m": route.total_distance,
                "distance_km": round(summary.total_distance_km, 3),
                "fare": fare,
                "estimated_time": round(summary.estimated_time, 1),
                "transfer_count": route.transfer_count,
                "lines": route.involved_lines,
                "transfers": [{"station": s, "from": a, "to": b} for s, a, b in route.transfers],
            }, ensure_ascii=False, indent=2)
        out = ["Route: %s -> %s" % (query.start_station, query.end_station),
               "Stations (%d): %s" % (len(route.station_sequence), " -> ".join(route.station_sequence)),
               "Total distance: " + format_distance(route.total_distance),
               "Lines: " + ", ".join(route.involved_lines)]
        for line, stations in route.segments:
            out.append("  [%s] %s" % (line, " -> ".join(stations)))
        if route.transfers:
            for s, a, b in route.transfers:
                out.append("Transfer at %s: %s -> %s" % (s, a, b))
        else:
            out.append("No transfers")
        out.append("Transfers: %d" % route.transfer_count)
        out.append("Estimated time: %.1f minutes" % summary.estimated_time)
        out.append("Fare: %d yuan" % fare)
        return "\n".join(out)

    def export(self, text):
        if not self.output_file:
            return
        with open(self.output_file, "a" if self._written else "w", encoding="utf-8") as f:
            f.write(text + "\n")
        self._written = True
