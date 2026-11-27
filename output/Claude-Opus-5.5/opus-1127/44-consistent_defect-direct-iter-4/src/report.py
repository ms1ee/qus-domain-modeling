"""Path visualization and export."""
import json


def format_distance(meters):
    if meters < 1000:
        return f"{meters} meters ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} meters)"


def format_text(info):
    lines = []
    q = info["query"]
    lines.append("=" * 50)
    lines.append(f"Route: {q['start']} -> {q['end']}  (mode: {q['mode']})")
    lines.append("-" * 50)
    lines.append("Station sequence (from end to start):")
    lines.append("  " + " <- ".join(reversed(info["path"])))
    lines.append("Line segments:")
    for seg in info["segments"]:
        lines.append(f"  [{seg['line']}] {seg['from']} -> {seg['to']} "
                     f"({len(seg['stations']) - 1} stops, {format_distance(seg['distance'])})")
    if info["transfer_stations"]:
        lines.append("Transfer stations: " + ", ".join(info["transfer_stations"]))
    else:
        lines.append("Transfer stations: none")
    lines.append("Lines involved: " + ", ".join(str(l) for l in info["lines"]))
    lines.append(f"Total distance: {format_distance(info['distance'])}")
    lines.append(f"Transfers: {info['transfer_count']}")
    lines.append(f"Estimated time: {info['estimated_time']} minutes")
    lines.append(f"Fare: {info['fare']} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def to_json_dict(info):
    return {
        "query": info["query"],
        "path": info["path"],
        "segments": info["segments"],
        "distance": info["distance"],
        "fare": info["fare"],
        "estimated_time": info["estimated_time"],
        "transfer_count": info["transfer_count"],
        "transfer_stations": info["transfer_stations"],
        "lines": info["lines"],
    }


def format_json(info):
    return json.dumps(to_json_dict(info), ensure_ascii=False, indent=2)


def summary(info):
    return {"distance": info["distance"], "fare": info["fare"],
            "transfer_count": info["transfer_count"], "estimated_time": info["estimated_time"]}
