"""
Route summary generation, path visualization and export (text / JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Short distances in meters, long distances in kilometers."""
    if meters < 1000:
        return f"{int(round(meters))} m"
    return f"{meters / 1000.0:.2f} km"


def build_route_result(network, sp, target, config=None):
    """Build a structured result dict for the path from sp.source to target.
    Returns None if no path exists."""
    stations, edges = sp.path_with_edges(target)
    if not stations or (not edges and sp.source != target):
        return None
    names = [network.station_name(n) for n in stations]
    total = sum(e.weight for e in edges)

    segments, transfers = [], []
    for i, e in enumerate(edges):
        from_name = network.station_name(e.source)
        to_name = network.station_name(e.dest)
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["to"] = to_name
            seg["stations"].append(to_name)
            seg["distance_meters"] += e.weight
        else:
            if segments:
                transfers.append({"station": from_name,
                                  "from_line": segments[-1]["line"], "to_line": e.line})
            segments.append({"line": e.line, "from": from_name, "to": to_name,
                             "stations": [from_name, to_name], "distance_meters": e.weight})
    for seg in segments:
        seg["stops"] = len(seg["stations"]) - 1

    transfer_count = len(transfers)
    fare = Sum_money(total)
    est = calculate_estimated_time(total, transfer_count)
    lines = list(dict.fromkeys(s["line"] for s in segments))

    query = {"start": names[0], "end": names[-1]}
    if config is not None:
        query.update({"mode": config.mode, "max_transfers": config.max_transfers,
                      "line_preference": list(config.preferred_lines)})
    return {
        "query": query,
        "path": names,
        "station_count": len(names),
        "segments": segments,
        "transfers": transfers,
        "distance": {"meters": total, "kilometers": round(total / 1000.0, 2)},
        "fare": fare,
        "estimated_time_minutes": est,
        "transfer_count": transfer_count,
        "lines": lines,
    }


def format_text(result):
    """Console-formatted text report."""
    sep = "=" * 60
    out = [sep, f"Route: {result['query']['start']} -> {result['query']['end']}"]
    if "mode" in result["query"]:
        out.append(f"Mode: {result['query']['mode']}")
    out.append("-" * 60)
    out.append(f"Station sequence ({result['station_count']} stations):")
    out.append("  " + " -> ".join(result["path"]))
    out.append("Line segments:")
    transfers = result["transfers"]
    for i, seg in enumerate(result["segments"]):
        out.append(f"  {i + 1}. [{seg['line']}] {seg['from']} -> {seg['to']} "
                   f"({seg['stops']} stop(s), {format_distance(seg['distance_meters'])})")
        if i < len(transfers):
            t = transfers[i]
            out.append(f"     >> Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    if transfers:
        out.append("Transfer stations: " + ", ".join(
            f"{t['station']} ({t['from_line']} -> {t['to_line']})" for t in transfers))
    else:
        out.append("Transfer stations: none (direct route)")
    out.append("Lines involved: " + ", ".join(str(l) for l in result["lines"]))
    m = result["distance"]["meters"]
    out.append(f"Total distance: {format_distance(m)} ({m} meters / {result['distance']['kilometers']:.2f} km)")
    out.append(f"Transfers: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time_minutes']} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append(sep)
    return "\n".join(out)


def format_json(result):
    """JSON report for programmatic integration."""
    return json.dumps(result, ensure_ascii=False, indent=2)
