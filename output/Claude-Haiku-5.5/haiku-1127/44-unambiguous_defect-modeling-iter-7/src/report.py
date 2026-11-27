"""
Path visualisation and export.

Produces:
  * console text reports (station sequence, line segments, transfers, distance,
    fare and estimated time),
  * JSON reports for programmatic integration,
  * path summaries,
  * file output.
"""

import json
import os

from route_service import RouteResult


def summarize_route(result):
    """
    Extract the key figures of a route.

    Returns:
        dict with start, end, station_count, total_distance_m, total_distance_km,
        fare, transfer_count and estimated_time_min.
    """
    return {
        "start": result.start,
        "end": result.end,
        "station_count": len(result.stations),
        "total_distance_m": round(result.total_distance_m, 1),
        "total_distance_km": round(result.total_distance_km, 2),
        "fare": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_min": result.estimated_time_min,
    }


def format_text(result):
    """
    Build a human-readable console report.

    Args:
        result: RouteResult.

    Returns:
        str: The formatted report.
    """
    rule = "=" * 60
    out = [rule, "Beijing Subway Fare Query", rule]
    out.append(f"Start station   : {result.start}")
    out.append(f"End station     : {result.end}")
    out.append(f"Query mode      : {result.mode}")
    out.append("Max transfers   : " + ("unlimited" if result.max_transfers is None
                                       else str(result.max_transfers)))
    out.append(f"Line preference : {result.line_preference or 'none'}")
    out.append("")

    out.append(f"Station sequence ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, 1):
        out.append(f"  {index:>3}. {name}")
    out.append("")

    out.append("Line segments:")
    for segment in result.segments:
        out.append(f"  [{segment['line']}] " + " -> ".join(segment["stations"]))
    out.append("")

    out.append("Transfer stations:")
    if not result.transfers:
        out.append("  No transfer required")
    for transfer in result.transfers:
        out.append(f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}")
    out.append("")

    out.append(f"Total distance  : {result.total_distance_m:.0f} m "
               f"({result.total_distance_km:.2f} km)")
    out.append(f"Transfers       : {result.transfer_count}")
    out.append(f"Lines involved  : {', '.join(result.lines) if result.lines else 'none'}")
    out.append(f"Estimated time  : {result.estimated_time_min:.1f} minutes")
    out.append(f"Fare: {result.fare} yuan")
    out.append(rule)
    return "\n".join(out)


def format_json(result, indent=2):
    """
    Build a structured JSON report.

    Returns:
        str: JSON text with query, path, distance, fare, estimated time,
             transfer count and involved lines.
    """
    payload = {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.line_preference,
        },
        "path": list(result.stations),
        "distance_meters": round(result.total_distance_m, 1),
        "distance_km": round(result.total_distance_km, 3),
        "fare": result.fare,
        "estimated_time_minutes": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "lines": list(result.lines),
        "transfers": [dict(t) for t in result.transfers],
        "segments": [{"line": s["line"], "stations": list(s["stations"])}
                     for s in result.segments],
        "summary": summarize_route(result),
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def write_report(content, output_path, append=False):
    """
    Write report text to a file.

    Args:
        content: Text to write.
        output_path: Destination file path.
        append: Append to the file instead of overwriting it.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(output_path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as fh:
        fh.write(content)
        if not content.endswith("\n"):
            fh.write("\n")
    return output_path
