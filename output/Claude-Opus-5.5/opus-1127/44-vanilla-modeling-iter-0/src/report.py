"""
Route building, path visualization and export (text / JSON).
"""

import json
from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time


@dataclass
class RouteSegment:
    order: int
    line: str
    stations: list
    distance: int

    @property
    def start(self):
        return self.stations[0]

    @property
    def end(self):
        return self.stations[-1]


@dataclass
class Route:
    stations: list
    segments: list = field(default_factory=list)
    total_distance: int = 0
    transfer_count: int = 0
    transfer_stations: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    fare: int = 0
    estimated_time: float = 0.0


def build_route(path, edges, number_to_station):
    """Build a Route from a station-number path and its edges."""
    names = [number_to_station.get(n, str(n)) for n in path]
    segments = []
    for i, e in enumerate(edges):
        to_name = names[i + 1]
        if segments and segments[-1].line == e.line:
            segments[-1].stations.append(to_name)
            segments[-1].distance += e.distance
        else:
            segments.append(RouteSegment(len(segments) + 1, e.line, [names[i], to_name], e.distance))
    total = sum(e.distance for e in edges)
    transfers = max(len(segments) - 1, 0)
    route = Route(
        stations=names,
        segments=segments,
        total_distance=total,
        transfer_count=transfers,
        transfer_stations=[s.start for s in segments[1:]],
        lines=list(dict.fromkeys(s.line for s in segments)),
    )
    route.fare = Sum_money(total)
    route.estimated_time = calculate_estimated_time(total, transfers)
    return route


def format_distance(meters):
    """Meters for short distances, kilometers for long ones (both shown)."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters:g} meters ({km:.2f} km)"
    return f"{km:.2f} km ({meters:g} meters)"


def format_text_report(route, start, end, mode=None):
    out = ["=" * 50, f"Route: {start} -> {end}"]
    if mode:
        out.append(f"Mode: {mode}")
    out.append("-" * 50)
    out.append(f"Station sequence ({len(route.stations)} stations):")
    out.append("  " + " -> ".join(route.stations))
    out.append("Line segments:")
    for i, seg in enumerate(route.segments):
        stops = len(seg.stations) - 1
        out.append(f"  {seg.order}. [{seg.line}] {seg.start} -> {seg.end} "
                   f"({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg.distance)})")
        out.append("       " + " -> ".join(seg.stations))
        if i + 1 < len(route.segments):
            out.append(f"     Transfer at {seg.end}: {seg.line} -> {route.segments[i + 1].line}")
    out.append(f"Transfer count: {route.transfer_count}")
    out.append("Transfer stations: " + (", ".join(route.transfer_stations) or "None"))
    out.append("Lines involved: " + ", ".join(route.lines))
    out.append(f"Total distance: {format_distance(route.total_distance)}")
    out.append(f"Estimated time: {route.estimated_time:.1f} minutes")
    out.append(f"Fare: {route.fare} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def build_json_report(route, start, end, mode=None, max_transfers=None, line_preference=None):
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": mode,
            "max_transfers": max_transfers,
            "line_preference": line_preference,
        },
        "path": list(route.stations),
        "segments": [
            {"order": s.order, "line": s.line, "stations": list(s.stations),
             "distance": s.distance} for s in route.segments
        ],
        "distance": {
            "meters": route.total_distance,
            "kilometers": round(route.total_distance / 1000.0, 3),
        },
        "fare": route.fare,
        "estimated_time": round(route.estimated_time, 1),
        "transfer_count": route.transfer_count,
        "transfer_stations": list(route.transfer_stations),
        "lines": list(route.lines),
    }


def format_json_report(*args, **kwargs):
    return json.dumps(build_json_report(*args, **kwargs), ensure_ascii=False, indent=2)
