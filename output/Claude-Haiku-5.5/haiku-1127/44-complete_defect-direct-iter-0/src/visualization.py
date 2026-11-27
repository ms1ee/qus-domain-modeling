"""Path visualization and export.

Renders a route summary (see path_summary.compute_route_summary) as
console-formatted text or as JSON, and writes results to files.
"""

import json
from typing import Any, Dict

SHORT_DISTANCE_LIMIT_M = 1000


def format_distance(distance_m: float) -> str:
    """Format a distance using meters for short trips and kilometers for long trips.

    Examples:
        850  -> "850 m (0.85 km)"
        12500 -> "12.50 km (12500 m)"
    """
    if distance_m < SHORT_DISTANCE_LIMIT_M:
        return f"{distance_m:.0f} m ({distance_m / 1000.0:.2f} km)"
    return f"{distance_m / 1000.0:.2f} km ({distance_m:.0f} m)"


def format_text(summary: Dict[str, Any]) -> str:
    """Render a route summary as console-formatted text."""
    query = summary["query"]
    max_transfers = query["max_transfers"] if query["max_transfers"] is not None else "unlimited"
    preference = ", ".join(query["line_preference"]) if query["line_preference"] else "none"
    segments = summary["segments"]
    transfers = summary["transfers"]

    out = []
    out.append("=" * 60)
    out.append("Beijing Subway Route Query")
    out.append("=" * 60)
    out.append(f"Start station   : {query['start']}")
    out.append(f"End station     : {query['end']}")
    out.append(f"Query mode      : {query['mode']}")
    out.append(f"Max transfers   : {max_transfers}")
    out.append(f"Line preference : {preference}")
    out.append("")
    out.append(f"Station sequence ({summary['stations_count']} stations):")
    out.append("  " + " -> ".join(summary["path"]))
    out.append("")
    out.append("Line segments:")
    if not segments:
        out.append("  (no travel required)")
    for index, segment in enumerate(segments, start=1):
        stops = len(segment["stations"]) - 1
        out.append(
            f"  {index}. [{segment['line']}] {segment['from']} -> {segment['to']} "
            f"({stops} stop(s), {format_distance(segment['distance_m'])})"
        )
    out.append("")
    out.append("Transfers:")
    if not transfers:
        out.append("  No transfer required")
    for transfer in transfers:
        out.append(f"  At {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}")
    out.append(f"Number of transfers: {summary['transfer_count']}")
    out.append(f"Lines involved     : {', '.join(summary['lines']) if summary['lines'] else 'none'}")
    out.append("")
    out.append(f"Total distance        : {format_distance(summary['distance_m'])}")
    out.append(f"Estimated travel time : {summary['estimated_time_min']:.1f} min")
    out.append(f"Fare: {summary['fare']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(summary: Dict[str, Any]) -> str:
    """Render a route summary as a JSON document."""
    payload = {
        "query": summary["query"],
        "path": summary["path"],
        "stations_count": summary["stations_count"],
        "distance_m": summary["distance_m"],
        "distance_km": summary["distance_km"],
        "fare": summary["fare"],
        "estimated_time_min": summary["estimated_time_min"],
        "transfer_count": summary["transfer_count"],
        "lines": summary["lines"],
        "segments": summary["segments"],
        "transfers": summary["transfers"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_summary(summary: Dict[str, Any], fmt: str = "text") -> str:
    """Render a summary in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(summary)
    return format_text(summary)


def export_to_file(content: str, path: str) -> None:
    """Write rendered output to a file (UTF-8), overwriting existing content.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")
