"""
Path visualization and export: console text and JSON reports, summaries.
"""

import json


def format_distance(meters):
    """Show both meters and kilometers; primary unit depends on length."""
    if meters < 1000:
        return f"{meters} meters ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} meters)"


def format_fare(fare):
    return f"Fare: {fare} yuan"


def generate_summary(route):
    return {
        "total_distance": route["distance"],
        "total_fare": route["fare"],
        "transfer_count": route["transfer_count"],
        "estimated_time": round(route["estimated_time"], 1),
    }


def format_text(route):
    lines = []
    lines.append("=" * 50)
    lines.append(f"Route: {route['start']} -> {route['end']}  (mode: {route['mode']})")
    lines.append("-" * 50)
    lines.append("Stations: " + " -> ".join(route["path"]))
    lines.append(f"Number of stations: {len(route['path'])}")
    lines.append("")
    lines.append("Line segments:")
    for i, seg in enumerate(route["segments"], 1):
        lines.append(f"  {i}. [{seg['line']}] " + " -> ".join(seg["stations"])
                     + f"  ({format_distance(seg['distance'])})")
    if route["transfers"]:
        lines.append("")
        lines.append("Transfers:")
        for t in route["transfers"]:
            lines.append(f"  At {t['station']}: {t['from_line']} -> {t['to_line']}")
    lines.append("")
    lines.append("Lines involved: " + ", ".join(str(l) for l in route["lines"]))
    lines.append(f"Total distance: {format_distance(route['distance'])}")
    lines.append(f"Transfer count: {route['transfer_count']}")
    lines.append(f"Estimated time: {route['estimated_time']:.1f} minutes")
    lines.append(format_fare(route["fare"]))
    lines.append("=" * 50)
    return "\n".join(lines)


def build_json_dict(route):
    return {
        "query": {"start": route["start"], "end": route["end"], "mode": route["mode"]},
        "path": route["path"],
        "segments": route["segments"],
        "transfers": route["transfers"],
        "distance": route["distance"],
        "distance_km": round(route["distance"] / 1000, 3),
        "fare": route["fare"],
        "estimated_time": round(route["estimated_time"], 1),
        "transfer_count": route["transfer_count"],
        "lines": route["lines"],
        "summary": generate_summary(route),
    }


def format_json(route):
    return json.dumps(build_json_dict(route), ensure_ascii=False, indent=2)


def format_report(route, fmt="text"):
    return format_json(route) if fmt == "json" else format_text(route)
