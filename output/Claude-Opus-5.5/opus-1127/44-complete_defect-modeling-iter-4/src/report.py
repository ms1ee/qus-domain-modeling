"""
Route construction, path visualization and export (text / JSON).
"""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from models import Route, Transfer


def build_route(network, sp, target):
    """Build a Route from a ShortestPath result. Returns None if unreachable."""
    path, edges = sp.path_with_edges(target)
    if not path:
        return None
    names = [network.station_name(n) for n in path]
    segments, transfers, involved = [], [], []
    for i, e in enumerate(edges):
        if not segments or segments[-1]["line"] != e.line:
            if segments:
                transfers.append(Transfer(names[i], segments[-1]["line"], e.line))
            segments.append({"line": e.line, "stations": [names[i]], "distance": 0})
        segments[-1]["stations"].append(names[i + 1])
        segments[-1]["distance"] += e.distance
        if e.line not in involved:
            involved.append(e.line)
    total = sum(e.distance for e in edges)
    tcount = len(transfers)
    return Route(
        station_sequence=names,
        total_distance=total,
        transfer_count=tcount,
        estimated_time=calculate_estimated_time(total, tcount),
        involved_lines=involved,
        segments=segments,
        transfers=transfers,
    )


def generate_summary(route):
    """Key information: distance (km), fare, transfers, estimated time."""
    return {
        "total_distance_m": route.total_distance,
        "total_distance_km": round(route.total_distance / 1000.0, 2),
        "fare": Sum_money(route.total_distance),
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": route.estimated_time,
    }


def format_distance(meters):
    km = meters / 1000.0
    if meters < 1000:
        return f"{meters} m ({km:.2f} km)"
    return f"{km:.2f} km ({meters} m)"


def build_result(route, query_info, fare=None):
    """Structured result dictionary (used for JSON and text output)."""
    if fare is None:
        fare = Sum_money(route.total_distance)
    return {
        "query": dict(query_info),
        "path": list(route.station_sequence),
        "station_count": len(route.station_sequence),
        "segments": [
            {"line": s["line"], "from": s["stations"][0], "to": s["stations"][-1],
             "stations": list(s["stations"]), "distance": s["distance"]}
            for s in route.segments
        ],
        "distance": {
            "meters": route.total_distance,
            "kilometers": round(route.total_distance / 1000.0, 2),
        },
        "fare": fare,
        "fare_text": f"Fare: {fare} yuan",
        "estimated_time": route.estimated_time,
        "estimated_time_unit": "minutes",
        "transfer_count": route.transfer_count,
        "transfers": [
            {"station": t.station_name, "from_line": t.from_line, "to_line": t.to_line}
            for t in route.transfers
        ],
        "lines": list(route.involved_lines),
    }


def format_text(result):
    q = result["query"]
    out = [
        "=" * 50,
        f"Route: {q.get('start')} -> {q.get('end')}",
        f"Mode: {q.get('mode', 'shortest_distance')}",
        "-" * 50,
        f"Stations ({result['station_count']}): " + " -> ".join(result["path"]),
        "Segments:",
    ]
    transfers = result["transfers"]
    for i, seg in enumerate(result["segments"]):
        stops = len(seg["stations"]) - 1
        out.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"])
                   + f" ({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg['distance'])})")
        if i < len(transfers):
            t = transfers[i]
            out.append(f"  ** Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    out.append(f"Total distance: {format_distance(result['distance']['meters'])}")
    if transfers:
        out.append(f"Transfers: {result['transfer_count']} (at "
                   + ", ".join(t["station"] for t in transfers) + ")")
    else:
        out.append("Transfers: 0")
    out.append("Lines involved: " + ", ".join(str(l) for l in result["lines"]))
    out.append(f"Estimated time: {result['estimated_time']} min")
    out.append(result["fare_text"])
    out.append("=" * 50)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def render(result, fmt="text"):
    return format_json(result) if fmt == "json" else format_text(result)
