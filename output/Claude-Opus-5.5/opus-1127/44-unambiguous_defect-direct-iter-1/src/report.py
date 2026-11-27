"""Route result building and formatting (text / JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time, FareCalculationError
from pathfinding import ShortestPath, count_transfers


class RouteError(Exception):
    """Raised when a route cannot be computed."""


class FareError(Exception):
    """Raised when a fare cannot be computed."""


def format_distance(meters):
    if meters >= 1000:
        return f"{meters / 1000:.2f} km"
    return f"{meters} m"


def build_route_result(network, start, end, config):
    """Compute the route between two official station names and summarise it."""
    try:
        s = network.station_to_number[start]
        t = network.station_to_number[end]
    except KeyError as exc:
        raise RouteError(f"Unknown station: {exc}") from exc
    try:
        sp = ShortestPath(network.graph, s, config)
        nodes, edges = sp.path_with_edges(t)
    except Exception as exc:  # pragma: no cover - defensive
        raise RouteError(f"Path calculation failed: {exc}") from exc
    if not nodes:
        extra = ""
        if config.max_transfers is not None:
            extra = f" within {config.max_transfers} transfer(s)"
        raise RouteError(f"No route found from '{start}' to '{end}'{extra}")

    names = [network.number_to_station[n] for n in nodes]
    distance = sum(e.distance for e in edges)
    transfers_n = count_transfers(edges)
    try:
        fare = Sum_money(distance)
        est = calculate_estimated_time(distance, transfers_n)
    except FareCalculationError as exc:
        raise FareError(f"Fare calculation failed: {exc}") from exc

    segments = []
    transfers = []
    lines = []
    for i, e in enumerate(edges):
        if e.line not in lines:
            lines.append(e.line)
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["to"] = names[i + 1]
            seg["stations"].append(names[i + 1])
            seg["stops"] += 1
            seg["distance"] += e.distance
        else:
            if segments:
                transfers.append({"station": names[i], "from_line": segments[-1]["line"],
                                  "to_line": e.line})
            segments.append({"line": e.line, "from": names[i], "to": names[i + 1],
                             "stations": [names[i], names[i + 1]], "stops": 1,
                             "distance": e.distance})

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
        "distance": distance,
        "distance_m": distance,
        "distance_km": round(distance / 1000, 2),
        "fare": fare,
        "estimated_time": est,
        "estimated_time_min": est,
        "transfer_count": transfers_n,
        "transfers": transfers,
        "transfer_stations": [t["station"] for t in transfers],
        "lines": lines,
        "segments": segments,
    }


def format_text(result):
    q = result["query"]
    bar = "=" * 60
    out = [bar, f"Route: {q['start']} -> {q['end']}  (Mode: {q['mode']})", bar]
    out.append(f"Stations ({result['station_count']}): " + " -> ".join(result["path"]))
    out.append("Segments:")
    for i, seg in enumerate(result["segments"], 1):
        out.append(f"  {i}. [{seg['line']}] {seg['from']} -> {seg['to']} "
                   f"({seg['stops']} stop(s), {format_distance(seg['distance'])})")
    if result["transfers"]:
        out.append(f"Transfers ({result['transfer_count']}):")
        for t in result["transfers"]:
            out.append(f"  Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    else:
        out.append("Transfers (0): none")
    out.append("Lines involved: " + ", ".join(str(l) for l in result["lines"]))
    out.append(f"Total distance: {result['distance']} meters ({result['distance_km']:.2f} km)")
    out.append(f"Estimated time: {result['estimated_time']} minutes")
    out.append(f"Fare: {result['fare']} yuan")
    out.append(bar)
    return "\n".join(out)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_result(result, fmt):
    return format_json(result) if fmt == "json" else format_text(result)
