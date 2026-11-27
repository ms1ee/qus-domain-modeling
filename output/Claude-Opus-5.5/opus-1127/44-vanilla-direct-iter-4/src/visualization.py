"""Path visualization and export (console text and JSON)."""

import json


def format_distance(meters):
    """Short distances in meters, long distances in kilometers (both shown)."""
    if meters < 1000:
        return f"{meters} meters ({meters / 1000.0:.2f} km)"
    return f"{meters / 1000.0:.2f} km ({meters} meters)"


def format_text(result):
    lines = []
    q = result["query"]
    lines.append("=" * 50)
    lines.append(f"Route: {q['start']} -> {q['end']}")
    lines.append(f"Mode: {q['mode']}")
    lines.append("-" * 50)
    lines.append(f"Station sequence ({len(result['path'])} stations):")
    lines.append("  " + " -> ".join(result["path"]))
    lines.append("Line segments:")
    transfers = result["transfer_stations"]
    for i, seg in enumerate(result["segments"]):
        lines.append(f"  [{seg['line']}] {' -> '.join(seg['stations'])} "
                     f"({format_distance(seg['distance'])})")
        if i < len(transfers):
            tr = transfers[i]
            lines.append(f"  >> Transfer at {tr['station']}: "
                         f"{tr['from_line']} -> {tr['to_line']}")
    lines.append("-" * 50)
    lines.append(f"Total distance: {format_distance(result['distance']['meters'])}")
    if transfers:
        at = ", ".join(t["station"] for t in transfers)
        lines.append(f"Transfers: {result['transfer_count']} (at {at})")
    else:
        lines.append(f"Transfers: {result['transfer_count']}")
    lines.append(f"Lines involved: {', '.join(str(l) for l in result['lines'])}")
    lines.append(f"Estimated time: {result['estimated_time']} minutes")
    lines.append(f"Fare: {result['fare']} yuan")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_result(result, fmt="text"):
    return format_json(result) if fmt == "json" else format_text(result)
