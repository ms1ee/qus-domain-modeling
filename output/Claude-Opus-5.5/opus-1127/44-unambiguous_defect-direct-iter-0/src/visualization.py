"""Route result construction and text / JSON report formatting."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


class FareCalculationError(Exception):
    pass


def build_segments(network, path, edges):
    """Group consecutive edges on the same line into ride segments."""
    segments = []
    for edge in edges:
        src = network.station_name(edge.source)
        dst = network.station_name(edge.dest)
        if segments and segments[-1]["line"] == edge.line:
            seg = segments[-1]
            seg["stations"].append(dst)
            seg["distance"] += edge.weight
        else:
            segments.append({"line": edge.line, "stations": [src, dst], "distance": edge.weight})
    for seg in segments:
        seg["stops"] = len(seg["stations"]) - 1
    return segments


def format_distance(meters):
    if meters >= 1000:
        return "%d meters (%.2f km)" % (round(meters), meters / 1000.0)
    return "%d meters (%.3f km)" % (round(meters), meters / 1000.0)


def build_route_result(network, sp, start, end, config):
    """Build the full route summary dict for a computed ShortestPath."""
    target = network.station_number(end)
    path, edges = sp.path_with_edges(target)
    if not path:
        return None
    names = [network.station_name(v) for v in path]
    distance = sum(e.weight for e in edges)
    segments = build_segments(network, path, edges)
    transfers = []
    for prev, cur in zip(segments, segments[1:]):
        transfers.append({"station": prev["stations"][-1], "from_line": prev["line"], "to_line": cur["line"]})
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, len(transfers))
    except (TypeError, ValueError) as exc:
        raise FareCalculationError(str(exc))
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": names,
        "station_count": len(names),
        "segments": segments,
        "distance": distance,
        "distance_meters": distance,
        "distance_km": round(distance / 1000.0, 2),
        "fare": fare,
        "estimated_time": est,
        "estimated_time_minutes": est,
        "transfer_count": len(transfers),
        "transfers": transfers,
        "transfer_stations": [t["station"] for t in transfers],
        "lines": lines,
    }


def format_text(result):
    q = result["query"]
    out = []
    out.append("=" * 50)
    out.append("Route: %s -> %s" % (q["start"], q["end"]))
    out.append("Mode: %s" % q["mode"])
    out.append("-" * 50)
    out.append("Stations (%d): %s" % (result["station_count"], " -> ".join(result["path"])))
    out.append("Line segments:")
    for i, seg in enumerate(result["segments"]):
        out.append("  [%s] %s -> %s (%d stops, %s)" % (
            seg["line"], seg["stations"][0], seg["stations"][-1], seg["stops"], format_distance(seg["distance"])))
        out.append("      " + " -> ".join(seg["stations"]))
        if i < len(result["transfers"]):
            t = result["transfers"][i]
            out.append("  Transfer at %s: %s -> %s" % (t["station"], t["from_line"], t["to_line"]))
    out.append("-" * 50)
    out.append("Total distance: %s" % format_distance(result["distance"]))
    out.append("Transfers: %d" % result["transfer_count"])
    if result["transfer_stations"]:
        out.append("Transfer stations: %s" % ", ".join(result["transfer_stations"]))
    out.append("Lines involved: %s" % ", ".join(str(l) for l in result["lines"]))
    out.append("Estimated time: %.1f minutes" % result["estimated_time"])
    out.append("Fare: %d yuan" % result["fare"])
    out.append("=" * 50)
    return "\n".join(out)


def format_json(results):
    return json.dumps(results, ensure_ascii=False, indent=2)
