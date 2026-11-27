"""Path visualization, summary generation and report export."""

import json
import os

from fare_calculator import Sum_money, calculate_estimated_time, get_fare_tier_name
from pathfinding import PathfindingConfig, PathNotFoundError, ShortestPath


def compute_route(graph, start_name, end_name, config=None):
    """Compute the route between two stations and build the result record.

    Raises:
        ValueError: For invalid station names or identical endpoints.
        PathNotFoundError: If no route satisfies the constraints.
    """
    config = config if config is not None else PathfindingConfig()
    if start_name == end_name:
        raise ValueError("Starting station cannot be the same as the ending station")
    for name in (start_name, end_name):
        if not graph.has_station(name):
            raise ValueError(f"station '{name}' does not exist")

    source = graph.get_number(start_name)
    target = graph.get_number(end_name)
    sp = ShortestPath(graph, source, config)
    if not sp.has_path_to(target):
        if config.max_transfers is not None:
            raise PathNotFoundError(
                f"no route from '{start_name}' to '{end_name}' within "
                f"{config.max_transfers} transfer(s)"
            )
        raise PathNotFoundError(f"no route from '{start_name}' to '{end_name}'")

    nodes, edges = sp.path_with_edges(target)
    return build_route_result(graph, nodes, edges, start_name, end_name, config)


def build_route_result(graph, nodes, edges, start_name, end_name, config):
    """Build a JSON-serialisable dictionary describing a route."""
    names = [graph.get_name(number) for number in nodes]
    total_m = float(sum(edge.distance for edge in edges))

    transfers = []
    segments = []
    segment_start = 0
    for index in range(1, len(edges)):
        if edges[index - 1].line != edges[index].line:
            segments.append(_make_segment(names, edges, segment_start, index, edges[index - 1].line))
            transfers.append(
                {
                    "station": names[index],
                    "from_line": edges[index - 1].line,
                    "to_line": edges[index].line,
                }
            )
            segment_start = index
    if edges:
        segments.append(
            _make_segment(names, edges, segment_start, len(names) - 1, edges[-1].line)
        )

    lines_involved = []
    for segment in segments:
        if segment["line"] not in lines_involved:
            lines_involved.append(segment["line"])

    transfer_count = len(transfers)
    fare = Sum_money(total_m)
    tier = get_fare_tier_name(total_m)
    estimated = calculate_estimated_time(total_m, transfer_count)
    total_km = round(total_m / 1000.0, 3)

    return {
        "query": {
            "start": start_name,
            "end": end_name,
            "mode": config.mode,
            "max_transfers": config.max_transfers,
            "line_preference": list(config.preferred_lines),
        },
        "path": names,
        "segments": segments,
        "transfers": transfers,
        "lines": lines_involved,
        "distance": {"meters": round(total_m, 1), "kilometers": total_km},
        "fare": {"yuan": fare, "tier": tier},
        "transfer_count": transfer_count,
        "estimated_time_minutes": round(estimated, 1),
        "summary": {
            "total_distance_km": total_km,
            "total_fare_yuan": fare,
            "transfer_count": transfer_count,
            "estimated_time_minutes": round(estimated, 1),
        },
    }


def _make_segment(names, edges, start, end, line):
    """Create a description of a run of stations served by one line."""
    distance = sum(edges[k].distance for k in range(start, end))
    return {
        "line": line,
        "start": names[start],
        "end": names[end],
        "stations": names[start:end + 1],
        "stop_count": end - start,
        "distance_m": float(distance),
    }


def format_text(result):
    """Render a route result as console-formatted text."""
    query = result["query"]
    out = []
    out.append("=" * 60)
    out.append(f"Route: {query['start']} -> {query['end']}")
    out.append(f"Mode: {query['mode']}")
    if query["max_transfers"] is not None:
        out.append(f"Max transfers: {query['max_transfers']}")
    if query["line_preference"]:
        out.append(f"Preferred lines: {', '.join(query['line_preference'])}")
    out.append("-" * 60)

    out.append(f"Station sequence ({len(result['path'])} stations):")
    for index, name in enumerate(result["path"], start=1):
        out.append(f"  {index:>3}. {name}")

    out.append("Line segments:")
    for segment in result["segments"]:
        out.append(
            f"  [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({segment['stop_count']} stops, {segment['distance_m']:.0f} m)"
        )

    out.append("Transfers:")
    if not result["transfers"]:
        out.append("  None (direct trip)")
    for transfer in result["transfers"]:
        out.append(
            f"  - at {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
        )
    out.append(f"Lines involved: {', '.join(result['lines'])}")

    out.append("-" * 60)
    distance = result["distance"]
    out.append(f"Total distance: {distance['meters']:.0f} m ({distance['kilometers']:.2f} km)")
    out.append(f"Number of transfers: {result['transfer_count']}")
    out.append(f"Estimated time: {result['estimated_time_minutes']:.1f} minutes")
    out.append(f"Fare: {result['fare']['yuan']} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def format_json(result):
    """Render a route result as a JSON document."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def render_report(result, fmt="text"):
    """Render a route result in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(result)
    if fmt == "text":
        return format_text(result)
    raise ValueError(f"unsupported output format '{fmt}'")


def export_results(results, fmt, output_file):
    """Write all query results of a session to a file.

    JSON output is a single JSON array; text output concatenates the reports.
    """
    if fmt == "json":
        content = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        content = "\n\n".join(format_text(result) for result in results)
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write(content + "\n")
    return output_file
