"""Path visualization, trip summary generation and report export."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from .fare_calculator import Sum_money, calculate_estimated_time
from .models import Edge, Transfer

if TYPE_CHECKING:  # pragma: no cover
    from .network import SubwayNetwork


@dataclass
class Segment:
    """A contiguous part of the route served by a single line."""

    line: str
    stations: list[str]


@dataclass
class TripSummary:
    """Key information extracted from a computed route."""

    query: dict
    stations: list[str]
    edges: list[Edge]
    total_distance_m: float
    fare_yuan: int
    transfer_count: int
    transfers: list[Transfer]
    involved_lines: list[str]
    segments: list[Segment] = field(default_factory=list)
    estimated_time_min: float = 0.0

    @property
    def total_distance_km(self) -> float:
        """Total distance converted from meters to kilometers."""
        return self.total_distance_m / 1000.0


def build_summary(
    network: "SubwayNetwork", query: dict, station_numbers: list[int], edges: list[Edge]
) -> TripSummary:
    """Build a TripSummary from a route expressed as station numbers and edges."""
    names = [network.station_name(number) for number in station_numbers]
    total = sum(edge.weight for edge in edges)

    transfers: list[Transfer] = []
    segments: list[Segment] = []
    if edges:
        current_line = edges[0].line
        seg_stations = [names[0]]
        for index, edge in enumerate(edges):
            if index > 0 and edge.line != edges[index - 1].line:
                transfers.append(Transfer(names[index], edges[index - 1].line, edge.line))
                segments.append(Segment(current_line, seg_stations))
                current_line = edge.line
                seg_stations = [names[index]]
            seg_stations.append(names[index + 1])
        segments.append(Segment(current_line, seg_stations))

    involved = list(dict.fromkeys(edge.line for edge in edges))
    transfer_count = len(transfers)
    return TripSummary(
        query=query,
        stations=names,
        edges=list(edges),
        total_distance_m=total,
        fare_yuan=Sum_money(total),
        transfer_count=transfer_count,
        transfers=transfers,
        involved_lines=involved,
        segments=segments,
        estimated_time_min=calculate_estimated_time(total, transfer_count),
    )


def format_distance(meters: float) -> str:
    """Format a distance: meters for short trips, kilometers (plus meters) for long trips."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def render_text(summary: TripSummary) -> str:
    """Render a trip summary as console-formatted text."""
    query = summary.query
    preferred = query.get("line_preference") or []
    lines = [
        "=" * 60,
        f"Query: {query['start_station']} -> {query['end_station']}",
        f"Mode: {query['mode']}    Max transfers: {query['max_transfers']}",
        f"Line preference: {', '.join(preferred) if preferred else 'none'}",
        "-" * 60,
        f"Route ({len(summary.stations)} stations): " + " -> ".join(summary.stations),
        f"Total distance: {format_distance(summary.total_distance_m)}",
        f"Transfers: {summary.transfer_count}",
        f"Lines involved: {', '.join(summary.involved_lines) if summary.involved_lines else 'none'}",
        f"Estimated time: {summary.estimated_time_min:.1f} minutes",
        "Segments:",
    ]
    for index, segment in enumerate(summary.segments, start=1):
        lines.append(f"  {index}. [{segment.line}] " + " -> ".join(segment.stations))
    if summary.transfers:
        lines.append("Transfer stations:")
        for transfer in summary.transfers:
            lines.append(
                f"  - {transfer.station_name}: {transfer.from_line} -> {transfer.to_line}"
            )
    else:
        lines.append("Transfer stations: none")
    lines.append(f"Fare: {summary.fare_yuan} yuan")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_json(summary: TripSummary) -> str:
    """Render a trip summary as a JSON document for programmatic use."""
    payload = {
        "query": summary.query,
        "path": {"stations": summary.stations, "station_count": len(summary.stations)},
        "distance": {
            "meters": round(summary.total_distance_m, 1),
            "kilometers": round(summary.total_distance_km, 3),
        },
        "fare_yuan": summary.fare_yuan,
        "estimated_time_minutes": round(summary.estimated_time_min, 1),
        "transfer_count": summary.transfer_count,
        "transfers": [asdict(transfer) for transfer in summary.transfers],
        "involved_lines": summary.involved_lines,
        "segments": [{"line": seg.line, "stations": seg.stations} for seg in summary.segments],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_report(content: str, path: str, append: bool = False) -> str:
    """Write report content to a file.

    Args:
        content: rendered report text.
        path: destination file path (parent directories are created).
        append: append to the file instead of overwriting it.

    Returns:
        The path written to.

    Raises:
        OSError: if the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as handle:
        handle.write(content + "\n")
    return path
