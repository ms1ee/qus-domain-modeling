"""Route building, summaries and report formatting (text / JSON)."""

import json

try:
    from fare_calculator import Sum_money, calculate_estimated_time
    from models import Route, TransferPoint, Segment, PathSummary
except ImportError:  # pragma: no cover
    from .fare_calculator import Sum_money, calculate_estimated_time
    from .models import Route, TransferPoint, Segment, PathSummary


def build_route(network, sp, start_name, end_name, mode="shortest_distance"):
    """Build a Route from a computed ShortestPath; None if unreachable."""
    target = network.station_to_number[end_name]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        return None
    names = [network.number_to_station[n] for n in nodes]
    total = sum(e.weight for e in edges)
    if isinstance(total, float) and total.is_integer():
        total = int(total)
    segments, transfers, lines = [], [], []
    for e in edges:
        src = network.number_to_station[e.source]
        dst = network.number_to_station[e.dest]
        if segments and segments[-1].line == e.line:
            segments[-1].stations.append(dst)
            segments[-1].distance += e.weight
        else:
            if segments:
                transfers.append(TransferPoint(src, segments[-1].line, e.line))
            segments.append(Segment(e.line, [src, dst], e.weight))
        if e.line not in lines:
            lines.append(e.line)
    fare = Sum_money(total)
    est = calculate_estimated_time(total, len(transfers))
    return Route(start=start_name, end=end_name, mode=mode,
                 station_sequence=names, total_distance=total,
                 transfer_count=len(transfers), estimated_time=est,
                 involved_lines=lines, fare=fare, transfers=transfers,
                 segments=segments)


def summarize(route):
    """Extract key information from a route."""
    return PathSummary(total_distance=route.total_distance,
                       total_fare=route.fare,
                       transfer_count=route.transfer_count,
                       estimated_time=route.estimated_time)


def format_distance(meters):
    """Show distance in both units; primary unit depends on magnitude."""
    km = meters / 1000.0
    if meters < 1000:
        return "%d meters (%.2f km)" % (meters, km)
    return "%.2f km (%d meters)" % (km, meters)


def format_fare(fare):
    return "Fare: %d yuan" % fare


def route_to_text(route):
    lines = []
    lines.append("=" * 50)
    lines.append("Route: %s -> %s (mode: %s)" % (route.start, route.end, route.mode))
    lines.append("Station sequence (end to start): " +
                 " <- ".join(reversed(route.station_sequence)))
    lines.append("Segments:")
    for i, seg in enumerate(route.segments):
        lines.append("  [%s] %s (%d stops, %s)" % (
            seg.line, " -> ".join(seg.stations), len(seg.stations) - 1,
            format_distance(seg.distance)))
        if i < len(route.transfers):
            t = route.transfers[i]
            lines.append("  ** Transfer at %s: %s -> %s" %
                         (t.station_name, t.from_line, t.to_line))
    lines.append("Total distance: " + format_distance(route.total_distance))
    if route.transfers:
        lines.append("Transfers: %d (at %s)" % (
            route.transfer_count,
            ", ".join(t.station_name for t in route.transfers)))
    else:
        lines.append("Transfers: 0")
    lines.append("Lines involved: " + ", ".join(str(l) for l in route.involved_lines))
    lines.append("Estimated time: %.1f minutes" % route.estimated_time)
    lines.append(format_fare(route.fare))
    lines.append("=" * 50)
    return "\n".join(lines)


def route_to_dict(route):
    return {
        "query": {"start": route.start, "end": route.end, "mode": route.mode},
        "path": list(route.station_sequence),
        "distance": route.total_distance,
        "distance_km": round(route.total_distance / 1000.0, 3),
        "fare": route.fare,
        "estimated_time": round(route.estimated_time, 2),
        "transfer_count": route.transfer_count,
        "transfers": [{"station": t.station_name, "from_line": t.from_line,
                       "to_line": t.to_line} for t in route.transfers],
        "lines": list(route.involved_lines),
    }


def route_to_json(route):
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=2)
