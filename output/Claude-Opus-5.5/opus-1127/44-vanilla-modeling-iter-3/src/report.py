"""Path visualisation and report export (text and JSON)."""

import json


def format_distance(meters):
    """Human friendly distance: meters for short, kilometers for long."""
    if meters < 1000:
        return "{} meters ({:.2f} km)".format(meters, meters / 1000.0)
    return "{:.2f} km ({} meters)".format(meters / 1000.0, meters)


def build_summary(result):
    return {
        "total_distance_km": round(result["distance"]["meters"] / 1000.0, 2),
        "fare": result["fare"],
        "transfer_count": result["transfer_count"],
        "estimated_time": result["estimated_time"],
    }


def format_text(result):
    q = result["query"]
    lines = []
    lines.append("=" * 50)
    lines.append("Route: {} -> {}".format(q["start"], q["end"]))
    lines.append("Mode: {}".format(q["mode"]))
    if q.get("max_transfers") is not None:
        lines.append("Max transfers: {}".format(q["max_transfers"]))
    if q.get("line_preference"):
        lines.append("Line preference: {}".format(", ".join(q["line_preference"])))
    lines.append("-" * 50)
    lines.append("Stations ({}): {}".format(len(result["path"]), " -> ".join(result["path"])))
    lines.append("Segments:")
    for i, seg in enumerate(result["segments"]):
        if i > 0:
            prev = result["segments"][i - 1]
            lines.append("  >> Transfer at {}: {} -> {}".format(
                seg["from"], prev["line"], seg["line"]))
        lines.append("  [{}] {} -> {} ({} stops, {})".format(
            seg["line"], seg["from"], seg["to"], len(seg["stations"]) - 1,
            format_distance(seg["distance"])))
        lines.append("      " + " -> ".join(seg["stations"]))
    lines.append("-" * 50)
    lines.append("Total distance: {}".format(format_distance(result["distance"]["meters"])))
    if result["transfers"]:
        lines.append("Transfers: {} (at {})".format(
            result["transfer_count"], ", ".join(t["station"] for t in result["transfers"])))
    else:
        lines.append("Transfers: 0")
    lines.append("Lines involved: {}".format(", ".join(result["lines"])))
    lines.append("Estimated time: {} minutes".format(result["estimated_time"]))
    lines.append("Fare: {} yuan".format(result["fare"]))
    lines.append("=" * 50)
    return "\n".join(lines)


def format_json(result):
    data = dict(result)
    data["summary"] = build_summary(result)
    return json.dumps(data, ensure_ascii=False, indent=2)


def render(result, fmt="text"):
    if fmt == "json":
        return format_json(result)
    return format_text(result)


def export_results(results, path, fmt="text"):
    """Write all query results to a file in the chosen format."""
    with open(path, "w", encoding="utf-8") as fh:
        if fmt == "json":
            items = [dict(r, summary=build_summary(r)) for r in results]
            payload = items[0] if len(items) == 1 else items
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        else:
            fh.write("\n\n".join(format_text(r) for r in results))
            fh.write("\n")
