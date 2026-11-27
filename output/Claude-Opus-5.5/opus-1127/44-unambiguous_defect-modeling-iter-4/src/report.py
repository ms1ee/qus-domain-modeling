"""
Route summary, visualisation and export (text / JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time, get_fare_tier
from pathfinding import ShortestPath


def build_segments(station_names, edges):
    """Group consecutive edges on the same line into route segments."""
    segments = []
    for i, edge in enumerate(edges):
        if segments and segments[-1]["line"] == edge.line:
            seg = segments[-1]
            seg["to"] = station_names[i + 1]
            seg["stations"].append(station_names[i + 1])
            seg["distance"] += edge.weight
        else:
            segments.append({
                "sequence": len(segments) + 1,
                "line": edge.line,
                "from": station_names[i],
                "to": station_names[i + 1],
                "stations": [station_names[i], station_names[i + 1]],
                "distance": edge.weight,
            })
    for seg in segments:
        seg["stops"] = len(seg["stations"]) - 1
    return segments


def build_route_result(start, end, station_names, edges, mode="shortest_distance",
                       config=None):
    """Build the structured route summary dict."""
    distance = sum(e.weight for e in edges)
    if isinstance(distance, float) and distance.is_integer():
        distance = int(distance)
    segments = build_segments(station_names, edges)
    transfer_count = ShortestPath.count_transfers(edges)
    transfers = []
    for i in range(1, len(segments)):
        transfers.append({"station": segments[i]["from"],
                          "from_line": segments[i - 1]["line"],
                          "to_line": segments[i]["line"]})
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    fare = Sum_money(distance)
    return {
        "query": {
            "start": start,
            "end": end,
            "mode": mode,
            "max_transfers": getattr(config, "max_transfers", None),
            "line_preference": list(getattr(config, "preferred_lines", []) or []),
        },
        "path": list(station_names),
        "station_count": len(station_names),
        "segments": segments,
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "fare_tier": get_fare_tier(distance),
        "estimated_time": calculate_estimated_time(distance, transfer_count),
        "transfer_count": transfer_count,
        "transfer_stations": [t["station"] for t in transfers],
        "transfers": transfers,
        "lines": lines,
    }


def format_distance(meters):
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters} meters ({km:.2f} km)"
    return f"{km:.2f} km ({meters} meters)"


def format_text(result):
    """Console-formatted route report."""
    q = result["query"]
    out = ["=" * 50,
           f"Route: {q['start']} -> {q['end']}  (mode: {q['mode']})",
           "-" * 50,
           f"Stations ({result['station_count']}): " + " -> ".join(result["path"]),
           "Segments:"]
    for i, seg in enumerate(result["segments"]):
        out.append(f"  {seg['sequence']}. [{seg['line']}] {seg['from']} -> {seg['to']} "
                   f"({seg['stops']} stop(s), {seg['distance'] / 1000.0:.2f} km)")
        out.append("       " + " -> ".join(seg["stations"]))
        if i < len(result["transfers"]):
            t = result["transfers"][i]
            out.append(f"     * Transfer at {t['station']}: "
                       f"{t['from_line']} -> {t['to_line']}")
    d = result["distance"]
    out.append(f"Total distance: {d['meters']} meters ({d['kilometers']:.2f} km)")
    if result["transfer_count"]:
        out.append(f"Transfers: {result['transfer_count']} "
                   f"(at {', '.join(result['transfer_stations'])})")
    else:
        out.append("Transfers: 0 (direct)")
    out.append("Lines involved: " + ", ".join(str(x) for x in result["lines"]))
    out.append(f"Estimated time: {result['estimated_time']} minutes")
    out.append(f"Fare tier: {result['fare_tier']}")
    out.append(f"Fare: {result['fare']} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_result(result, fmt="text"):
    return format_json(result) if fmt == "json" else format_text(result)
