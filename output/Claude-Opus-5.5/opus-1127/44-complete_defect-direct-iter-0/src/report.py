"""
Route result construction, visualization and export (text / JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Human friendly distance: meters for short, kilometers for long."""
    km = meters / 1000.0
    if meters < 1000:
        return f"{int(round(meters))} meters ({km:.2f} km)"
    return f"{km:.2f} km ({int(round(meters))} meters)"


def build_route_result(network, sp, start_name, end_name, config):
    """Build a structured result dict for a computed path.

    Returns None if no path exists.
    """
    target = network.station_to_number[end_name]
    nums, edges = sp.path_with_edges(target)
    if not nums:
        return None
    names = [network.number_to_station[n] for n in nums]
    distance = sum(e.weight for e in edges)

    segments = []
    transfers = []
    for e in edges:
        src = network.number_to_station[e.source]
        dst = network.number_to_station[e.dest]
        if not segments or segments[-1]["line"] != e.line:
            if segments:
                transfers.append({"station": src, "from_line": segments[-1]["line"], "to_line": e.line})
            segments.append({"line": e.line, "stations": [src], "distance": 0})
        segments[-1]["stations"].append(dst)
        segments[-1]["distance"] += e.weight

    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    transfer_count = len(transfers)
    fare = Sum_money(distance)
    est = calculate_estimated_time(distance, transfer_count)

    return {
        "query": {
            "start": start_name,
            "end": end_name,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": names,
        "station_count": len(names),
        "segments": segments,
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": est,
        "transfer_count": transfer_count,
        "transfers": transfers,
        "transfer_stations": [t["station"] for t in transfers],
        "lines": lines,
    }


def summarize(result):
    """Extract key summary information from a route result."""
    return {
        "total_distance_km": result["distance"]["kilometers"],
        "fare": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time_minutes": result["estimated_time"],
    }


def format_text(result):
    """Console-formatted text report."""
    sep = "=" * 60
    sub = "-" * 60
    out = [sep, f"Route: {result['query']['start']} -> {result['query']['end']}",
           f"Mode: {result['query']['mode']}", sub,
           f"Station sequence ({result['station_count']} stations):",
           "  " + " -> ".join(result["path"]), "", "Route details:"]
    for i, seg in enumerate(result["segments"]):
        if i > 0:
            t = result["transfers"][i - 1]
            out.append(f"  ** Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
        out.append(f"  [{seg['line']}] {seg['stations'][0]} -> {seg['stations'][-1]} "
                   f"({len(seg['stations']) - 1} stops, {format_distance(seg['distance'])})")
        out.append("      " + " -> ".join(seg["stations"]))
    out.append(sub)
    out.append(f"Total distance: {format_distance(result['distance']['meters'])}")
    if result["transfer_count"]:
        out.append(f"Transfers: {result['transfer_count']} (at {', '.join(result['transfer_stations'])})")
    else:
        out.append("Transfers: 0 (direct)")
    out.append(f"Lines involved: {', '.join(str(l) for l in result['lines'])}")
    out.append(f"Estimated time: {result['estimated_time']:.1f} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append(sep)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)
