"""
Path visualization and export.

Produces console-formatted text reports and structured JSON reports from
QueryResult objects, and exports collections of results to files.
"""

import json
import os


def format_distance(meters):
    """
    Format a distance: meters for short distances, kilometers for long ones.

    Examples:
        850   -> "850 m"
        12350 -> "12.35 km (12350 m)"
    """
    value = int(round(meters))
    if value < 1000:
        return f"{value} m"
    return f"{value / 1000:.2f} km ({value} m)"


def format_text(result):
    """Return a console-formatted text report for a QueryResult."""
    lines = []
    lines.append("=" * 60)
    lines.append("Beijing Subway Fare Query Result")
    lines.append("=" * 60)
    lines.append(f"Starting station : {result.start}")
    lines.append(f"Ending station   : {result.end}")
    lines.append(f"Query mode       : {result.mode}")
    if result.max_transfers is not None:
        lines.append(f"Max transfers    : {result.max_transfers}")
    if result.preferred_lines:
        lines.append(f"Preferred lines  : {', '.join(result.preferred_lines)}")
    lines.append("")

    lines.append("Route details (line segments):")
    for index, (line, stations) in enumerate(result.segments, 1):
        lines.append(f"  {index}. [{line}] {' -> '.join(stations)}")
    lines.append("")

    lines.append(f"Station sequence ({len(result.stations)} stations):")
    lines.append("  " + " -> ".join(result.stations))
    lines.append("")

    if result.transfers:
        lines.append(f"Transfer stations ({len(result.transfers)}):")
        for item in result.transfers:
            lines.append(f"  - {item['station']}: {item['from_line']} -> {item['to_line']}")
    else:
        lines.append("Transfer stations: none")
    lines.append(f"Lines involved: {', '.join(result.lines) if result.lines else 'none'}")
    lines.append("")

    lines.append("Summary:")
    lines.append(f"  Total distance : {format_distance(result.distance_m)}")
    lines.append(f"  Transfers      : {result.transfer_count}")
    lines.append(f"  Estimated time : {result.estimated_time:.1f} minutes")
    lines.append(f"  Fare: {result.fare} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(result):
    """Return a JSON report for a QueryResult."""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def format_result(result, output_format="text"):
    """Format a result as 'text' or 'json'."""
    if output_format == "json":
        return format_json(result)
    return format_text(result)


def export_results(results, output_file, output_format="text"):
    """
    Write all query results of a session to a file (overwriting it).

    Text format writes the text reports separated by blank lines.
    JSON format writes a JSON array with one object per query.

    Raises:
        OSError: If the file cannot be written.
    """
    if output_format == "json":
        content = json.dumps(
            [result.to_dict() for result in results], ensure_ascii=False, indent=2
        )
    else:
        content = "\n\n".join(format_text(result) for result in results)
    content += "\n"

    directory = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(directory, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as handle:
        handle.write(content)
