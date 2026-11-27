"""Route summary, text and JSON report generation."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    if meters < 1000:
        return f"{int(meters)} m"
    return f"{meters / 1000:.2f} km ({int(meters)} m)"


def build_route(sp, target, number_to_station):
    nodes, edges = sp.path_with_edges(target)
    if not nodes:
        return None
    names = [number_to_station[n] for n in nodes]
    distance = sum(e.distance for e in edges)
    transfers = []
    lines = []
    for e in edges:
        if e.line not in lines:
            lines.append(e.line)
    for a, b in zip(edges, edges[1:]):
        if a.line != b.line:
            transfers.append({"station": number_to_station[a.dest],
                              "from_line": a.line, "to_line": b.line})
    segments = []
    for e in edges:
        if segments and segments[-1]["line"] == e.line:
            segments[-1]["stations"].append(number_to_station[e.dest])
        else:
            segments.append({"line": e.line,
                             "stations": [number_to_station[e.source], number_to_station[e.dest]]})
    fare = Sum_money(distance)
    return {
        "path": names,
        "distance": distance,
        "fare": fare,
        "transfer_count": len(transfers),
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
        "estimated_time": round(calculate_estimated_time(distance, len(transfers)), 1),
    }


def format_text(start, end, route, mode=None):
    out = [f"Route: {start} -> {end}" + (f" (mode: {mode})" if mode else "")]
    out.append("Stations: " + " -> ".join(route["path"]))
    out.append(f"Number of stations: {len(route['path'])}")
    out.append("Segments:")
    for seg in route["segments"]:
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"]))
    if route["transfers"]:
        out.append("Transfers:")
        for t in route["transfers"]:
            out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("Transfers: none")
    out.append(f"Lines involved: {', '.join(str(l) for l in route['lines'])}")
    out.append(f"Total distance: {format_distance(route['distance'])}")
    out.append(f"Transfer count: {route['transfer_count']}")
    out.append(f"Estimated time: {route['estimated_time']} minutes")
    out.append(f"Fare: {route['fare']} yuan")
    return "\n".join(out)


def build_json_dict(start, end, route, mode=None):
    return {
        "query": {"start": start, "end": end, "mode": mode},
        "path": route["path"],
        "distance": route["distance"],
        "distance_km": round(route["distance"] / 1000, 3),
        "fare": route["fare"],
        "estimated_time": route["estimated_time"],
        "transfer_count": route["transfer_count"],
        "transfers": route["transfers"],
        "lines": route["lines"],
    }


def format_json(start, end, route, mode=None):
    return json.dumps(build_json_dict(start, end, route, mode), ensure_ascii=False, indent=2)
