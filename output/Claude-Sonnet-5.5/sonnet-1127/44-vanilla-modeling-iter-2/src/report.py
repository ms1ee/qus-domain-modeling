"""Route building, summary and report generation."""
import json

from fare_calculator import Sum_money, calculate_estimated_time


class Route:
    def __init__(self, stations, edges, graph):
        self.stations = stations
        self.edges = edges
        self.total_distance = sum(e.distance for e in edges)
        self.segments = []  # (line, [stations])
        self.transfer_stations = []
        for i, e in enumerate(edges):
            if self.segments and self.segments[-1][0] == e.line:
                self.segments[-1][1].append(stations[i + 1])
            else:
                if self.segments:
                    self.transfer_stations.append(stations[i])
                self.segments.append((e.line, [stations[i], stations[i + 1]]))
        self.transfer_count = len(self.transfer_stations)
        self.lines_involved = []
        for line, _ in self.segments:
            if line not in self.lines_involved:
                self.lines_involved.append(line)


def format_distance(meters):
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km"


def summarize(route):
    return {
        "total_distance_km": round(route.total_distance / 1000.0, 2),
        "fare": Sum_money(route.total_distance),
        "transfer_count": route.transfer_count,
        "estimated_time": round(calculate_estimated_time(route.total_distance, route.transfer_count), 1),
    }


def text_report(start, end, route, summary):
    out = [f"Route: {start} -> {end}",
           f"Stations ({len(route.stations)}): " + " -> ".join(route.stations),
           f"Total distance: {format_distance(route.total_distance)} ({route.total_distance} m / "
           f"{summary['total_distance_km']} km)"]
    for line, sts in route.segments:
        out.append(f"  [{line}] {sts[0]} -> {sts[-1]} ({len(sts) - 1} stops)")
    if route.transfer_stations:
        out.append("Transfers at: " + ", ".join(route.transfer_stations))
    out.append(f"Transfer count: {summary['transfer_count']}")
    out.append("Lines: " + ", ".join(route.lines_involved))
    out.append(f"Estimated time: {summary['estimated_time']} minutes")
    out.append(f"Fare: {summary['fare']} yuan")
    return "\n".join(out)


def json_report(start, end, mode, route, summary):
    return json.dumps({
        "query": {"start": start, "end": end, "mode": mode},
        "path": route.stations,
        "distance_m": route.total_distance,
        "distance_km": summary["total_distance_km"],
        "fare": summary["fare"],
        "estimated_time": summary["estimated_time"],
        "transfer_count": summary["transfer_count"],
        "transfer_stations": route.transfer_stations,
        "lines": route.lines_involved,
    }, ensure_ascii=False, indent=2)
