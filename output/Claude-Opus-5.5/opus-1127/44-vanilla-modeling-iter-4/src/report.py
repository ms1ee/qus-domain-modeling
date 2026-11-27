"""
Route visualization and export (console text and JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Use meters for short distances and kilometers for long ones."""
    if meters < 1000:
        return f"{int(round(meters))} m"
    return f"{meters / 1000.0:.2f} km"


def build_route_result(network, sp, start_name, end_name, mode, max_transfers=None,
                       line_preference=None):
    """Build a structured result dict for a computed path.

    :raises ValueError: if no path exists
    """
    target = network.station_to_number[end_name]
    stations, edges = sp.path_with_edges(target)
    if not stations:
        raise ValueError(f"No route found from '{start_name}' to '{end_name}'")
    names = [network.number_to_station[s] for s in stations]
    distance = sp.dist_to[target]
    transfer_count = sp.get_transfer_count(target)

    segments = []
    for e in edges:
        src = network.number_to_station[e.source]
        dst = network.number_to_station[e.dest]
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(dst)
            segments[-1]["distance"] += e.distance
        else:
            segments.append({"line": e.line, "stations": [src, dst], "distance": e.distance})

    transfers = []
    for prev, cur in zip(segments, segments[1:]):
        transfers.append({"station": cur["stations"][0], "from_line": prev["line"],
                          "to_line": cur["line"]})

    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])

    fare = Sum_money(distance)
    est = calculate_estimated_time(distance, transfer_count)
    return {
        "query": {
            "start": start_name,
            "end": end_name,
            "mode": mode,
            "max_transfers": max_transfers,
            "line_preference": line_preference,
        },
        "path": names,
        "station_count": len(names),
        "segments": segments,
        "transfers": transfers,
        "distance": {"meters": distance, "kilometers": round(distance / 1000.0, 2)},
        "fare": fare,
        "estimated_time": round(est, 1),
        "transfer_count": transfer_count,
        "lines": lines,
    }


def format_text(result):
    """Console-formatted text report."""
    q = result["query"]
    meters = result["distance"]["meters"]
    out = []
    out.append("=" * 50)
    out.append(f"Route: {q['start']} -> {q['end']}  (mode: {q['mode']})")
    out.append("-" * 50)
    out.append("Stations: " + " -> ".join(result["path"]))
    out.append(f"Number of stations: {result['station_count']}")
    out.append("Line segments:")
    for seg in result["segments"]:
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"])
                   + f" ({format_distance(seg['distance'])})")
    if result["transfers"]:
        out.append("Transfers:")
        for t in result["transfers"]:
            out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("Transfers: none")
    out.append(f"Lines involved: {', '.join(str(l) for l in result['lines'])}")
    out.append(f"Total distance: {format_distance(meters)} ({meters} meters, "
               f"{meters / 1000.0:.2f} km)")
    out.append(f"Transfer count: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time']} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_result(result, fmt="text"):
    if fmt == "json":
        return format_json(result)
    return format_text(result)


def export_results(results, output_file, fmt="text"):
    """Write results (list of dicts) to file. JSON: object if one, array otherwise."""
    with open(output_file, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            fh.write(json.dumps(payload, ensure_ascii=False, indent=2))
            fh.write("\n")
        else:
            fh.write("\n\n".join(format_text(r) for r in results))
            fh.write("\n")
