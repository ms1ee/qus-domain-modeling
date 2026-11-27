"""Path visualization, summary and report export.

Builds a structured result dictionary for a route, then renders it either as
console text or as JSON, and can append results to an output file.
"""

import json
from typing import Any, Dict, List, Optional, Sequence

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge
from network import SubwayNetwork
from pathfinding import PathfindingConfig


def format_distance(distance_m: int) -> str:
    """Format a distance: meters for short distances, kilometers for long ones."""
    if distance_m < 1000:
        return f"{distance_m} m"
    return f"{distance_m / 1000:.2f} km ({distance_m} m)"


def build_segments(network: SubwayNetwork, edges: Sequence[Edge]) -> List[Dict[str, Any]]:
    """Group consecutive edges operated by the same line into segments."""
    segments: List[Dict[str, Any]] = []
    for edge in edges:
        src_name = network.name_of(edge.source)
        dst_name = network.name_of(edge.dest)
        if segments and segments[-1]["line"] == edge.line:
            segment = segments[-1]
            segment["stations"].append(dst_name)
            segment["distance_m"] += edge.distance
        else:
            segments.append(
                {"line": edge.line, "stations": [src_name, dst_name], "distance_m": edge.distance}
            )
    for segment in segments:
        segment["start"] = segment["stations"][0]
        segment["end"] = segment["stations"][-1]
        segment["stop_count"] = len(segment["stations"]) - 1
    return segments


def build_result(
    network: SubwayNetwork,
    start: str,
    end: str,
    config: PathfindingConfig,
    nodes: Sequence[int],
    edges: Sequence[Edge],
    transfer_count: int,
) -> Dict[str, Any]:
    """Assemble the complete, JSON-serializable result of a route query."""
    path_names = [network.name_of(number) for number in nodes]
    distance_m = sum(edge.distance for edge in edges)
    segments = build_segments(network, edges)

    lines_involved: List[str] = []
    for segment in segments:
        if segment["line"] not in lines_involved:
            lines_involved.append(segment["line"])

    transfers: List[Dict[str, str]] = []
    for index in range(1, len(segments)):
        transfers.append(
            {
                "station": segments[index]["start"],
                "from_line": segments[index - 1]["line"],
                "to_line": segments[index]["line"],
            }
        )

    fare = Sum_money(distance_m)
    estimated_time = calculate_estimated_time(distance_m, transfer_count)

    return {
        "query": {
            "start": start,
            "end": end,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": path_names,
        "station_count": len(path_names),
        "distance_m": distance_m,
        "distance_km": round(distance_m / 1000.0, 3),
        "fare": fare,
        "estimated_time_min": estimated_time,
        "transfer_count": transfer_count,
        "lines": lines_involved,
        "segments": segments,
        "transfers": transfers,
        "summary": {
            "total_distance_km": round(distance_m / 1000.0, 3),
            "total_fare_yuan": fare,
            "transfer_count": transfer_count,
            "estimated_time_min": estimated_time,
        },
    }


def render_text(result: Dict[str, Any]) -> str:
    """Render a route result as human-readable console text."""
    query = result["query"]
    out: List[str] = []
    out.append(f"Route: {query['start']} -> {query['end']}")
    out.append(f"Mode: {query['mode']}")
    if query["max_transfers"] is not None:
        out.append(f"Max transfers: {query['max_transfers']}")
    if query["line_preference"]:
        out.append(f"Line preference: {', '.join(query['line_preference'])}")

    out.append(f"Station sequence ({result['station_count']} stations):")
    for index, name in enumerate(result["path"], start=1):
        out.append(f"  {index:>3}. {name}")

    out.append("Line segments:")
    for segment in result["segments"]:
        out.append(
            f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({segment['stop_count']} stops, {format_distance(segment['distance_m'])})"
        )

    out.append("Transfers:")
    if result["transfers"]:
        for transfer in result["transfers"]:
            out.append(
                f"  At {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        out.append("  No transfer required")

    out.append(f"Lines involved: {', '.join(result['lines'])}")
    out.append(f"Total distance: {format_distance(result['distance_m'])}")
    out.append(f"Transfer count: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time_min']:.1f} min")
    out.append(f"Fare: {result['fare']} yuan")
    return "\n".join(out)


def render_json(result: Dict[str, Any], indent: Optional[int] = 2) -> str:
    """Render a route result as JSON (indent=None gives a single line)."""
    return json.dumps(result, ensure_ascii=False, indent=indent)


def append_result_to_file(path: str, result: Dict[str, Any], output_format: str) -> None:
    """Append one query result to a file.

    JSON results are written as one JSON object per line (JSON Lines);
    text results are written as blocks separated by a divider line.

    Raises:
        OSError: if the file cannot be written.
    """
    if output_format == "json":
        block = render_json(result, indent=None) + "\n"
    else:
        block = render_text(result) + "\n" + "-" * 60 + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(block)
