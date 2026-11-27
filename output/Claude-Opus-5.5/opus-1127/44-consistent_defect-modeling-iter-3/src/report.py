"""Path visualization, summary generation and export."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def build_route_info(start_name, end_name, mode, stations, edges,
                     number_to_station, transfer_count):
    """Build a dict describing a route (used for text and JSON output)."""
    names = [number_to_station[s] for s in stations]
    total = sum(e.distance for e in edges)
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["stations"].append(number_to_station[e.dest])
            seg["distance"] += e.distance
        else:
            segments.append({"line": e.line,
                             "stations": [number_to_station[e.source],
                                          number_to_station[e.dest]],
                             "distance": e.distance})
    transfers = []
    for a, b in zip(segments, segments[1:]):
        transfers.append({"station": b["stations"][0],
                          "from_line": a["line"], "to_line": b["line"]})
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    fare = Sum_money(total)
    est = calculate_estimated_time(total, transfer_count)
    return {
        "query": {"start": start_name, "end": end_name, "mode": mode},
        "path": names,
        "distance": total,
        "distance_km": round(total / 1000.0, 2),
        "fare": fare,
        "estimated_time": round(est, 1),
        "transfer_count": transfer_count,
        "lines": lines,
        "segments": segments,
        "transfers": transfers,
    }


def generate_summary(info):
    """Key information summary (distance in meters)."""
    return {"total_distance": info["distance"],
            "total_fare": info["fare"],
            "transfer_count": info["transfer_count"],
            "estimated_time": info["estimated_time"]}


def format_distance(meters):
    return f"{meters} meters ({meters / 1000.0:.2f} km)"


def format_text(info):
    out = []
    q = info["query"]
    out.append("=" * 50)
    out.append(f"Route: {q['start']} -> {q['end']} (mode: {q['mode']})")
    out.append("-" * 50)
    out.append("Stations: " + " -> ".join(info["path"]))
    out.append(f"Number of stations: {len(info['path'])}")
    out.append("Segments:")
    for seg in info["segments"]:
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"])
                   + f" ({format_distance(seg['distance'])})")
    if info["transfers"]:
        out.append("Transfers:")
        for t in info["transfers"]:
            out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("Transfers: none")
    out.append("Lines involved: " + ", ".join(str(l) for l in info["lines"]))
    out.append(f"Total distance: {format_distance(info['distance'])}")
    out.append(f"Transfer count: {info['transfer_count']}")
    out.append(f"Estimated time: {info['estimated_time']} minutes")
    out.append(f"Fare: {info['fare']} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json(info):
    return json.dumps(info, ensure_ascii=False, indent=2)


def export_results(results, path, fmt):
    """Write accumulated results to a file."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            payload = results[0] if len(results) == 1 else results
            fh.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            fh.write("\n\n".join(format_text(r) for r in results))
        fh.write("\n")
