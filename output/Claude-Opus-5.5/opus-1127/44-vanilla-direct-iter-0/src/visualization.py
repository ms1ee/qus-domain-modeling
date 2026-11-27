"""
Path visualization and export module.

Builds route information dictionaries and renders them as console text or
JSON.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from fare_calculator import Sum_money, calculate_estimated_time


def format_distance(meters: float) -> str:
    """Show distance in meters for short trips and kilometers for long ones."""
    if meters < 1000:
        return f"{meters:g} meters ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters:g} meters)"


def format_fare(fare: int) -> str:
    return f"Fare: {fare} yuan"


def build_route_info(path_names: List[str], edges, query: Optional[Dict] = None) -> Dict:
    """Build a route information dict from station names and edges."""
    distance = sum(e.distance for e in edges)
    segments: List[Dict] = []
    transfers: List[Dict] = []
    lines: List[str] = []
    for i, e in enumerate(edges):
        if not segments or segments[-1]["line"] != e.line:
            if segments:
                transfers.append({"station": path_names[i],
                                  "from_line": segments[-1]["line"], "to_line": e.line})
            segments.append({"line": e.line, "stations": [path_names[i]], "distance": 0})
        segments[-1]["stations"].append(path_names[i + 1])
        segments[-1]["distance"] += e.distance
        if e.line not in lines:
            lines.append(e.line)
    transfer_count = len(transfers)
    fare = Sum_money(distance)
    est = calculate_estimated_time(distance, transfer_count)
    return {
        "query": query or {},
        "path": list(path_names),
        "station_count": len(path_names),
        "distance": distance,
        "distance_km": round(distance / 1000.0, 3),
        "distance_display": format_distance(distance),
        "fare": fare,
        "fare_text": format_fare(fare),
        "estimated_time": round(est, 1),
        "transfer_count": transfer_count,
        "transfers": transfers,
        "lines": lines,
        "segments": segments,
    }


def build_summary(info: Dict) -> Dict:
    """Extract key information from route info."""
    return {
        "total_distance_km": info["distance_km"],
        "total_fare": info["fare"],
        "transfer_count": info["transfer_count"],
        "estimated_time_minutes": info["estimated_time"],
    }


def format_text_report(info: Dict) -> str:
    q = info.get("query", {})
    sep = "=" * 60
    lines = [sep]
    lines.append(f"Route: {q.get('start', info['path'][0] if info['path'] else '')} -> "
                 f"{q.get('end', info['path'][-1] if info['path'] else '')}")
    if q.get("mode"):
        lines.append(f"Mode: {q['mode']}")
    lines.append("-" * 60)
    lines.append(f"Stations ({info['station_count']}): " + " -> ".join(info["path"]))
    lines.append("Segments:")
    for i, seg in enumerate(info["segments"]):
        if i > 0:
            t = info["transfers"][i - 1]
            lines.append(f"  >> Transfer at {t['station']}: {t['from_line']} -> {t['to_line']}")
        stops = len(seg["stations"]) - 1
        lines.append(f"  [{seg['line']}] " + " -> ".join(seg["stations"]) +
                     f"  ({stops} stop{'s' if stops != 1 else ''}, {format_distance(seg['distance'])})")
    lines.append(f"Total distance: {info['distance_display']}")
    if info["transfers"]:
        at = ", ".join(t["station"] for t in info["transfers"])
        lines.append(f"Transfers: {info['transfer_count']} (at {at})")
    else:
        lines.append("Transfers: 0")
    lines.append("Lines involved: " + ", ".join(str(l) for l in info["lines"]))
    lines.append(f"Estimated time: {info['estimated_time']:.1f} minutes")
    lines.append(info["fare_text"])
    lines.append(sep)
    return "\n".join(lines)


def to_json_dict(info: Dict) -> Dict:
    return {
        "query": info.get("query", {}),
        "path": info["path"],
        "distance": {"meters": info["distance"], "kilometers": info["distance_km"]},
        "fare": info["fare"],
        "estimated_time": info["estimated_time"],
        "transfer_count": info["transfer_count"],
        "transfers": info["transfers"],
        "lines": info["lines"],
        "segments": info["segments"],
    }


def format_json_report(info: Dict) -> str:
    return json.dumps(to_json_dict(info), ensure_ascii=False, indent=2)
