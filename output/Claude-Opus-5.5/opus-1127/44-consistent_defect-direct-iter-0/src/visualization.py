"""Route summary, text and JSON report generation."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return f"{meters} m"
    return f"{meters / 1000:.2f} km ({meters} m)"


def build_route_result(start, end, nodes, edges, number_to_station, transfer_count=None, mode=None):
    stations = [number_to_station[n] for n in nodes]
    distance = sum(e.weight for e in edges)
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(number_to_station[e.dest])
            segments[-1]["distance"] += e.weight
        else:
            segments.append({"line": e.line,
                             "stations": [number_to_station[e.source], number_to_station[e.dest]],
                             "distance": e.weight})
    transfer_stations = [seg["stations"][0] for seg in segments[1:]]
    if transfer_count is None:
        transfer_count = len(transfer_stations)
    lines = []
    for seg in segments:
        if seg["line"] not in lines:
            lines.append(seg["line"])
    fare = Sum_money(distance)
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": stations,
        "segments": segments,
        "distance": distance,
        "fare": fare,
        "estimated_time": calculate_estimated_time(distance, transfer_count),
        "transfer_count": transfer_count,
        "transfer_stations": transfer_stations,
        "lines": lines,
    }


def build_summary(result):
    return {
        "distance": result["distance"],
        "fare": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time": result["estimated_time"],
    }


def format_text_report(result):
    out = []
    q = result["query"]
    out.append("=" * 50)
    out.append(f"Route: {q['start']} -> {q['end']}")
    out.append("Station sequence (end to start): " + " <- ".join(reversed(result["path"])))
    out.append("Segments:")
    for seg in result["segments"]:
        out.append(f"  [{seg['line']}] {' -> '.join(seg['stations'])} ({format_distance(seg['distance'])})")
    if result["transfer_stations"]:
        out.append("Transfer stations: " + ", ".join(result["transfer_stations"]))
    else:
        out.append("Transfer stations: none")
    out.append("Lines involved: " + ", ".join(result["lines"]))
    out.append(f"Total distance: {format_distance(result['distance'])}")
    out.append(f"Transfers: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time']} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append("=" * 50)
    return "\n".join(out)


def format_json_report(result):
    data = {
        "query": result["query"],
        "path": result["path"],
        "distance": result["distance"],
        "fare": result["fare"],
        "estimated_time": result["estimated_time"],
        "transfer_count": result["transfer_count"],
        "transfer_stations": result["transfer_stations"],
        "lines": result["lines"],
        "segments": result["segments"],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
