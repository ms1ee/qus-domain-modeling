"""Path visualisation and export: console text, JSON, summaries, and file output."""

import json
import os


def format_distance(meters):
    """Format a distance: meters for short trips, kilometers for long trips.

    Short (< 1 km) example: "850 m (0.85 km)"; long example: "3.20 km (3200 m)".
    """
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def build_summary(route):
    """Extract the key figures of a route as a dictionary."""
    return {
        "total_distance_km": round(route.total_distance_m / 1000.0, 3),
        "total_fare": route.fare,
        "transfer_count": route.transfer_count,
        "estimated_time_minutes": round(route.estimated_time_minutes, 1),
    }


def format_text(route):
    """Render a route as a human-readable console report."""
    summary = build_summary(route)
    max_transfers = route.max_transfers if route.max_transfers is not None else "unlimited"
    output = [
        "=" * 56,
        "Beijing Subway Fare Query Result",
        "=" * 56,
        f"Starting station : {route.start_name}",
        f"Ending station   : {route.end_name}",
        f"Query mode       : {route.mode}",
        f"Max transfers    : {max_transfers}",
        f"Line preference  : {route.line_preference or 'none'}",
        "",
        f"Station sequence ({len(route.stations)} stations):",
        "  " + " -> ".join(route.stations),
        "",
        "Line segments:",
    ]
    for index, segment in enumerate(route.segments, 1):
        output.append(f"  {index}. {segment['line']}: {' -> '.join(segment['stations'])}")

    output.append("")
    if route.transfers:
        output.append(f"Transfer details ({len(route.transfers)}):")
        for transfer in route.transfers:
            output.append(f"  - {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}")
    else:
        output.append("Transfer details: no transfers required")
    output.append("Lines involved: " + ", ".join(route.lines))

    output.extend([
        "",
        "Summary",
        f"  Total distance : {format_distance(route.total_distance_m)}",
        f"  Transfers      : {summary['transfer_count']}",
        f"  Estimated time : {summary['estimated_time_minutes']:.1f} min",
        f"Fare: {route.fare} yuan",
        "=" * 56,
    ])
    return "\n".join(output)


def route_to_dict(route):
    """Convert a route to a JSON-serialisable dictionary."""
    return {
        "query": {
            "start_station": route.start_name,
            "end_station": route.end_name,
            "mode": route.mode,
            "max_transfers": route.max_transfers,
            "line_preference": route.line_preference,
        },
        "path": list(route.stations),
        "segments": [{"line": seg["line"], "stations": list(seg["stations"])}
                     for seg in route.segments],
        "distance": {
            "meters": round(route.total_distance_m, 2),
            "kilometers": round(route.total_distance_m / 1000.0, 3),
        },
        "fare": route.fare,
        "estimated_time_minutes": round(route.estimated_time_minutes, 1),
        "transfer_count": route.transfer_count,
        "transfers": [transfer.to_dict() for transfer in route.transfers],
        "lines": list(route.lines),
    }


def format_json(route, indent=2):
    """Render a route as a JSON string (indent=None gives a single line)."""
    return json.dumps(route_to_dict(route), ensure_ascii=False, indent=indent)


def write_report(route, output_format, output_file):
    """Append the route report to a file.

    Text reports are appended as blocks separated by blank lines; JSON reports
    are appended as one compact JSON object per line (JSON Lines).

    Returns:
        The absolute path of the output file.
    """
    if output_format == "json":
        content = format_json(route, indent=None) + "\n"
    else:
        content = format_text(route) + "\n\n"
    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(content)
    return os.path.abspath(output_file)
