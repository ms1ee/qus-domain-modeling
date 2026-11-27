"""Path visualization, summary generation and report export."""

import json
import os
from dataclasses import dataclass

from fare_calculator import Sum_money, calculate_estimated_time


@dataclass
class Segment:
    """A continuous run of stations served by one line."""

    line: str
    stations: list
    distance_m: int


@dataclass
class TransferInfo:
    """A transfer station where the passenger changes lines."""

    station: str
    from_line: str
    to_line: str


@dataclass
class PathSummary:
    """Key information extracted from a computed route."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    stations: list
    segments: list
    transfers: list
    lines: list
    distance_m: int
    fare_yuan: int
    transfer_count: int
    estimated_time_min: float


def format_distance(meters):
    """Format a distance using meters for short distances and kilometers for long ones.

    Examples: 850 -> "850 m (0.85 km)"; 12350 -> "12.35 km (12350 m)".
    """
    kilometers = meters / 1000.0
    if meters < 1000:
        return f"{meters} m ({kilometers:.2f} km)"
    return f"{kilometers:.2f} km ({meters} m)"


def _split_segments(names, edges):
    """Split a route into line segments and transfer stations.

    Args:
        names: Station names along the path (length = len(edges) + 1).
        edges: Edge objects along the path.

    Returns:
        tuple: (list of Segment, list of TransferInfo).
    """
    segments = []
    transfers = []
    if not edges:
        return segments, transfers
    current_line = edges[0].line
    segment_start = 0
    segment_distance = 0
    for index, edge in enumerate(edges):
        if edge.line != current_line:
            segments.append(Segment(current_line, names[segment_start:index + 1], segment_distance))
            transfers.append(TransferInfo(names[index], current_line, edge.line))
            current_line = edge.line
            segment_start = index
            segment_distance = 0
        segment_distance += edge.distance
    segments.append(Segment(current_line, names[segment_start:], segment_distance))
    return segments, transfers


def build_summary(network, start, end, station_numbers, edges, transfer_count,
                  mode, max_transfers=None, preferred_lines=None):
    """Build a PathSummary from a computed route.

    Args:
        network: The SubwayNetwork used for name lookups.
        start: Start station name.
        end: End station name.
        station_numbers: Station numbers along the path.
        edges: Edge objects along the path.
        transfer_count: Number of transfers on the path.
        mode: Query mode name.
        max_transfers: Transfer limit used for the query (or None).
        preferred_lines: Preferred lines used for the query (or None).

    Returns:
        PathSummary: The summary including total distance, fare and time.
    """
    names = [network.name_of(number) for number in station_numbers]
    distance = int(sum(edge.distance for edge in edges))
    segments, transfers = _split_segments(names, edges)
    lines = []
    for segment in segments:
        if segment.line not in lines:
            lines.append(segment.line)
    fare = Sum_money(distance)
    estimated_time = calculate_estimated_time(distance, transfer_count)
    return PathSummary(
        start=start,
        end=end,
        mode=mode,
        max_transfers=max_transfers,
        preferred_lines=list(preferred_lines or []),
        stations=names,
        segments=segments,
        transfers=transfers,
        lines=lines,
        distance_m=distance,
        fare_yuan=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated_time,
    )


def format_text(summary):
    """Render a PathSummary as console-formatted text."""
    divider = "=" * 60
    out = [divider]
    out.append(f"Route: {summary.start} -> {summary.end}")
    constraints = f"mode={summary.mode}"
    if summary.max_transfers is not None:
        constraints += f", max transfers={summary.max_transfers}"
    if summary.preferred_lines:
        constraints += f", preferred lines={', '.join(summary.preferred_lines)}"
    out.append(f"Query settings: {constraints}")
    out.append(f"Station sequence ({len(summary.stations)} stations):")
    out.append("  " + " -> ".join(summary.stations))
    out.append(f"Total distance: {format_distance(summary.distance_m)}")
    out.append(f"Number of transfers: {summary.transfer_count}")
    out.append("Lines involved: " + (", ".join(summary.lines) if summary.lines else "(none)"))
    out.append("Route segments:")
    for index, segment in enumerate(summary.segments, 1):
        sections = max(len(segment.stations) - 1, 0)
        out.append(
            f"  {index}. [{segment.line}] {segment.stations[0]} -> {segment.stations[-1]} "
            f"({sections} sections, {format_distance(segment.distance_m)})"
        )
    out.append("Transfer stations:")
    if summary.transfers:
        for transfer in summary.transfers:
            out.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("  (none)")
    out.append(f"Estimated travel time: {summary.estimated_time_min:.1f} min")
    out.append(f"Fare: {summary.fare_yuan} yuan")
    out.append(divider)
    return "\n".join(out)


def summary_to_dict(summary):
    """Convert a PathSummary into a JSON-serialisable dictionary."""
    return {
        "query": {
            "start": summary.start,
            "end": summary.end,
            "mode": summary.mode,
            "max_transfers": summary.max_transfers,
            "preferred_lines": summary.preferred_lines,
        },
        "path": list(summary.stations),
        "distance_m": summary.distance_m,
        "distance_km": round(summary.distance_m / 1000.0, 2),
        "fare_yuan": summary.fare_yuan,
        "estimated_time_min": round(summary.estimated_time_min, 2),
        "transfer_count": summary.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in summary.transfers
        ],
        "lines": list(summary.lines),
        "segments": [
            {
                "line": seg.line,
                "from": seg.stations[0],
                "to": seg.stations[-1],
                "stations": list(seg.stations),
                "distance_m": seg.distance_m,
            }
            for seg in summary.segments
        ],
    }


def format_json(summary):
    """Render a PathSummary as a JSON document string."""
    return json.dumps(summary_to_dict(summary), ensure_ascii=False, indent=2)


def render(summary, fmt):
    """Render a summary in the requested format ('text' or 'json').

    Raises:
        ValueError: If the format is unknown.
    """
    if fmt == "text":
        return format_text(summary)
    if fmt == "json":
        return format_json(summary)
    raise ValueError(f"unsupported output format '{fmt}'")


def write_output_file(path, content, append=False):
    """Write text content to a file, creating parent directories when needed.

    Args:
        path: Destination file path.
        content: Text to write.
        append: Append to the file instead of overwriting it.

    Raises:
        OSError: If the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as fh:
        fh.write(content)
