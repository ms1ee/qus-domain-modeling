"""Route summary, text and JSON report generation."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return f"{meters} meters ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} meters)"


def build_summary(network, sp, start_name, end_name, mode):
    target = network.station_to_number[end_name]
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        raise RuntimeError(f"No path found from '{start_name}' to '{end_name}'")
    distance = sum(e.distance for e in edges)
    transfers = sp.get_transfer_count(target)
    try:
        fare = Sum_money(distance)
    except Exception as exc:
        raise RuntimeError(f"Fare calculation failed: {exc}") from exc
    stations = [network.number_to_station[n] for n in nodes]
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    transfer_stations = []
    for a, b in zip(edges, edges[1:]):
        if a.line != b.line:
            transfer_stations.append({"station": network.number_to_station[a.dest],
                                      "from_line": a.line, "to_line": b.line})
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(network.number_to_station[e.dest])
        else:
            segments.append({"line": e.line,
                             "stations": [network.number_to_station[e.source],
                                          network.number_to_station[e.dest]]})
    return {
        "query": {"start": start_name, "end": end_name, "mode": mode},
        "path": stations,
        "distance": distance,
        "fare": fare,
        "estimated_time": round(calculate_estimated_time(distance, transfers), 1),
        "transfer_count": transfers,
        "lines": lines,
        "transfer_stations": transfer_stations,
        "segments": segments,
    }


def format_text(summary):
    out = []
    q = summary["query"]
    out.append("=" * 50)
    out.append(f"Route: {q['start']} -> {q['end']} (mode: {q['mode']})")
    out.append("-" * 50)
    out.append("Stations: " + " -> ".join(summary["path"]))
    out.append(f"Number of stations: {len(summary['path'])}")
    out.append("Segments:")
    for seg in summary["segments"]:
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"]))
    if summary["transfer_stations"]:
        out.append("Transfers:")
        for t in summary["transfer_stations"]:
            out.append(f"  At {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append(f"Transfer count: {summary['transfer_count']}")
    out.append("Lines involved: " + ", ".join(summary["lines"]))
    out.append(f"Total distance: {format_distance(summary['distance'])}")
    out.append(f"Estimated time: {summary['estimated_time']} minutes")
    out.append(f"Fare: {summary['fare']} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json(summary):
    data = {k: summary[k] for k in ("query", "path", "distance", "fare", "estimated_time",
                                    "transfer_count", "lines", "transfer_stations")}
    return json.dumps(data, ensure_ascii=False, indent=2)
