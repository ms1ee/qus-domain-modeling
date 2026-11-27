"""Route result building, path visualization and export (text / JSON)."""

import json
from datetime import datetime

from fare_calculator import FareCalculationError, Sum_money, calculate_estimated_time, format_fare
from pathfinding import RouteNotFoundError, ShortestPath


class RouteResult:
    """All information about a computed route."""

    def __init__(self, start, end, mode, stations, segments, distance, fare,
                 transfer_count, transfer_stations, lines, estimated_time,
                 max_transfers=None, line_preference=None):
        self.start = start
        self.end = end
        self.mode = mode
        self.stations = stations
        self.segments = segments
        self.distance = distance
        self.fare = fare
        self.transfer_count = transfer_count
        self.transfer_stations = transfer_stations
        self.lines = lines
        self.estimated_time = estimated_time
        self.max_transfers = max_transfers
        self.line_preference = line_preference or []


def build_route_result(network, start, end, config):
    """Compute a route between two canonical station names."""
    s = network.station_to_number[start]
    t = network.station_to_number[end]
    sp = ShortestPath(network.graph, s, config)
    if not sp.has_path_to(t):
        msg = "No route found from '%s' to '%s'" % (start, end)
        if config.max_transfers is not None:
            msg += " within %d transfer(s)" % config.max_transfers
        raise RouteNotFoundError(msg)
    nums, edges = sp.path_with_edges(t)
    names = [network.number_to_station[n] for n in nums]
    distance = sp.dist_to[t]
    try:
        fare = Sum_money(distance)
        transfers = sp.get_transfer_count(t)
        est = calculate_estimated_time(distance, transfers)
    except (ValueError, TypeError) as exc:
        raise FareCalculationError(str(exc)) from exc

    segments, transfer_stations, lines = [], [], []
    for i, edge in enumerate(edges):
        if not segments or segments[-1]["line"] != edge.line:
            if segments:
                transfer_stations.append(names[i])
            segments.append({"line": edge.line, "from": names[i], "to": names[i + 1],
                             "stations": [names[i], names[i + 1]], "distance": edge.distance})
        else:
            seg = segments[-1]
            seg["to"] = names[i + 1]
            seg["stations"].append(names[i + 1])
            seg["distance"] += edge.distance
        if edge.line not in lines:
            lines.append(edge.line)

    return RouteResult(start, end, config.mode, names, segments, distance, fare, transfers,
                       transfer_stations, lines, est, config.max_transfers, config.preferred_lines)


def _km(meters):
    return round(meters / 1000.0, 2)


def summarize(result):
    """Key information summary of a route."""
    return {"distance_km": _km(result.distance), "fare": result.fare,
            "transfer_count": result.transfer_count,
            "estimated_time_minutes": result.estimated_time}


def format_text(result):
    """Console-formatted text report."""
    out = ["=" * 50,
           "Route: %s -> %s  (mode: %s)" % (result.start, result.end, result.mode),
           "-" * 50,
           "Stations (%d): %s" % (len(result.stations), " -> ".join(result.stations)),
           "Total distance: %d m (%.2f km)" % (round(result.distance), result.distance / 1000.0),
           "Lines involved: %s" % (", ".join(result.lines) if result.lines else "-")]
    if result.transfer_stations:
        out.append("Transfers: %d (at %s)" % (result.transfer_count, ", ".join(result.transfer_stations)))
    else:
        out.append("Transfers: %d" % result.transfer_count)
    out.append("Segments:")
    for i, seg in enumerate(result.segments, 1):
        out.append("  %d. [%s] %s -> %s (%d stops, %.2f km)" % (
            i, seg["line"], seg["from"], seg["to"], len(seg["stations"]) - 1, seg["distance"] / 1000.0))
        out.append("     " + " - ".join(seg["stations"]))
        if i < len(result.segments):
            out.append("     >> Transfer at %s to %s" % (seg["to"], result.segments[i]["line"]))
    out.append("Estimated time: %.1f minutes" % result.estimated_time)
    out.append(format_fare(result.fare))
    out.append("=" * 50)
    return "\n".join(out)


def to_dict(result):
    """Structured (JSON-serialisable) report."""
    return {
        "query": {"start": result.start, "end": result.end, "mode": result.mode,
                  "max_transfers": result.max_transfers,
                  "line_preference": list(result.line_preference),
                  "timestamp": datetime.now().isoformat(timespec="seconds")},
        "path": list(result.stations),
        "station_count": len(result.stations),
        "distance": result.distance,
        "distance_meters": result.distance,
        "distance_km": _km(result.distance),
        "fare": result.fare,
        "fare_text": format_fare(result.fare),
        "estimated_time": result.estimated_time,
        "estimated_time_minutes": result.estimated_time,
        "transfer_count": result.transfer_count,
        "transfers": result.transfer_count,
        "transfer_stations": list(result.transfer_stations),
        "lines": list(result.lines),
        "segments": [dict(s, stations=list(s["stations"])) for s in result.segments],
        "summary": summarize(result),
    }


def format_json(result):
    return json.dumps(to_dict(result), ensure_ascii=False, indent=2)
