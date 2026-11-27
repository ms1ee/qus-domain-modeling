"""Path visualization and export (text and JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters):
    """Meters for short distances, kilometres for long ones."""
    if meters < 1000:
        return f"{int(round(meters))} m"
    return f"{meters / 1000.0:.2f} km"


def build_route_info(manager, sp, start_name, end_name, config):
    """Collect all route information into a dict. Raises RuntimeError if no path."""
    target = manager.station_to_number[end_name]
    path, edges = sp.path_with_edges(target)
    if not path:
        raise RuntimeError(f"No route found from '{start_name}' to '{end_name}'"
                           + (" within the transfer limit" if config.max_transfers is not None else ""))
    names = [manager.number_to_station[n] for n in path]
    distance = sum(e.weight for e in edges)

    segments = []
    for e in edges:
        frm = manager.number_to_station[e.source]
        to = manager.number_to_station[e.dest]
        if segments and segments[-1]["line"] == e.line:
            seg = segments[-1]
            seg["stations"].append(to)
            seg["to"] = to
            seg["distance"] += e.weight
        else:
            segments.append({"line": e.line, "from": frm, "to": to,
                             "stations": [frm, to], "distance": e.weight})
    transfers = []
    for i in range(1, len(segments)):
        transfers.append({"station": segments[i]["from"],
                          "from_line": segments[i - 1]["line"],
                          "to_line": segments[i]["line"]})
    lines = []
    for s in segments:
        if s["line"] not in lines:
            lines.append(s["line"])
    transfer_count = len(transfers)
    try:
        fare = Sum_money(distance)
    except Exception as exc:  # fare calculation exception handling
        raise RuntimeError(f"Fare calculation failed: {exc}") from exc
    est = calculate_estimated_time(distance, transfer_count)
    return {
        "start": start_name, "end": end_name,
        "mode": config.mode, "max_transfers": config.max_transfers,
        "line_preference": list(config.preferred_lines),
        "path": names, "segments": segments, "transfers": transfers,
        "lines": lines, "distance": distance, "transfer_count": transfer_count,
        "fare": fare, "estimated_time": est,
    }


def generate_summary(info):
    return {
        "total_distance_km": round(info["distance"] / 1000.0, 2),
        "total_fare": info["fare"],
        "transfer_count": info["transfer_count"],
        "estimated_time_minutes": info["estimated_time"],
    }


def format_text_report(info):
    lines = []
    lines.append("=" * 50)
    lines.append(f"Route: {info['start']} -> {info['end']}  (mode: {info['mode']})")
    lines.append("=" * 50)
    lines.append(f"Stations ({len(info['path'])}): " + " -> ".join(info["path"]))
    lines.append("Line segments:")
    for i, seg in enumerate(info["segments"]):
        lines.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} "
                     f"({len(seg['stations']) - 1} stops, {format_distance(seg['distance'])})")
        if i < len(info["transfers"]):
            t = info["transfers"][i]
            lines.append(f"  >> Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
    d = info["distance"]
    lines.append(f"Total distance: {format_distance(d)} ({int(d)} m / {d / 1000.0:.2f} km)")
    lines.append(f"Transfers: {info['transfer_count']}"
                 + (" (" + ", ".join(t["station"] for t in info["transfers"]) + ")"
                    if info["transfers"] else ""))
    lines.append("Lines involved: " + ", ".join(info["lines"]))
    lines.append(f"Estimated time: {info['estimated_time']} minutes")
    lines.append(f"Fare: {info['fare']} yuan")
    return "\n".join(lines)


def to_json_dict(info):
    return {
        "query": {
            "start": info["start"], "end": info["end"], "mode": info["mode"],
            "max_transfers": info["max_transfers"], "line_preference": info["line_preference"],
        },
        "path": info["path"],
        "segments": [{"line": s["line"], "from": s["from"], "to": s["to"],
                      "stations": s["stations"], "distance": s["distance"]}
                     for s in info["segments"]],
        "transfer_stations": info["transfers"],
        "distance": {"meters": info["distance"],
                     "kilometers": round(info["distance"] / 1000.0, 2),
                     "display": format_distance(info["distance"])},
        "fare": info["fare"],
        "fare_text": f"Fare: {info['fare']} yuan",
        "estimated_time": info["estimated_time"],
        "transfer_count": info["transfer_count"],
        "lines": info["lines"],
        "summary": generate_summary(info),
    }


def format_json_report(info):
    return json.dumps(to_json_dict(info), ensure_ascii=False, indent=2)
