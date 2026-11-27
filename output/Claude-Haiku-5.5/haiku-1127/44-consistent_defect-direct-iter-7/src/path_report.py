"""Path visualization, summary generation and report export (text and JSON)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from src.fare_calculator import Sum_money, calculate_estimated_time
from src.models import Edge


def format_distance(meters: float) -> str:
    """Format a distance: meters for short trips, kilometers (with meters) for long ones."""
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


@dataclass
class PathResult:
    """Complete result of a fare/path query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    notices: List[str]
    stations: List[str]                 # display order: end -> start
    lines: List[str]                    # all lines involved, in journey order
    segments: List[Dict[str, Any]]      # continuous same-line runs, in journey order
    transfers: List[Dict[str, str]]     # transfer stations with from/to lines
    distance_m: float
    fare: int
    transfer_count: int
    estimated_time: float               # minutes
    extra: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        """Key figures of the route: distance (meters), fare, transfers and time."""
        return {
            "distance_m": round(self.distance_m, 2),
            "fare": self.fare,
            "transfer_count": self.transfer_count,
            "estimated_time_minutes": round(self.estimated_time, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Structured representation suitable for JSON export."""
        return {
            "query": {
                "start_station": self.start_station,
                "end_station": self.end_station,
                "mode": self.mode,
                "max_transfers": self.max_transfers,
                "line_preference": self.preferred_lines,
                "notices": self.notices,
            },
            "path": {
                "stations": self.stations,
                "segments": self.segments,
                "transfers": self.transfers,
            },
            "distance_m": round(self.distance_m, 2),
            "fare": self.fare,
            "estimated_time_minutes": round(self.estimated_time, 2),
            "transfer_count": self.transfer_count,
            "lines": self.lines,
        }


def build_result(
    start_station: str,
    end_station: str,
    config: Any,
    notices: Sequence[str],
    stations_end_to_start: Sequence[str],
    edges_end_to_start: Sequence[Edge],
    transfer_count: int,
) -> PathResult:
    """Assemble a PathResult from the raw path returned by ShortestPath.

    Args:
        config: PathfindingConfig used for the query.
        stations_end_to_start: station names in the order returned by path_with_edges.
        edges_end_to_start: edges in the order returned by path_with_edges.
        transfer_count: transfers counted by the path search.
    """
    journey_names = list(reversed(stations_end_to_start))
    journey_edges = list(reversed(edges_end_to_start))

    segments: List[Dict[str, Any]] = []
    lines: List[str] = []
    distance = 0.0
    for index, edge in enumerate(journey_edges):
        distance += edge.weight
        if edge.line not in lines:
            lines.append(edge.line)
        if segments and segments[-1]["line"] == edge.line:
            segment = segments[-1]
            segment["end"] = journey_names[index + 1]
            segment["distance_m"] += edge.weight
            segment["stops"] += 1
        else:
            segments.append(
                {
                    "line": edge.line,
                    "start": journey_names[index],
                    "end": journey_names[index + 1],
                    "distance_m": edge.weight,
                    "stops": 1,
                }
            )

    transfers: List[Dict[str, str]] = []
    for index in range(1, len(journey_edges)):
        previous, current = journey_edges[index - 1], journey_edges[index]
        if previous.line != current.line:
            transfers.append(
                {
                    "station": journey_names[index],
                    "from_line": previous.line,
                    "to_line": current.line,
                }
            )

    fare = Sum_money(distance)
    estimated = calculate_estimated_time(distance, transfer_count)

    return PathResult(
        start_station=start_station,
        end_station=end_station,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        notices=list(notices),
        stations=list(stations_end_to_start),
        lines=lines,
        segments=segments,
        transfers=transfers,
        distance_m=distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_time=estimated,
    )


def render_text(result: PathResult) -> str:
    """Render a human-readable console report."""
    out: List[str] = []
    out.append("=" * 60)
    out.append("Beijing Subway Fare Query")
    out.append("=" * 60)
    out.append(f"Start: {result.start_station}    End: {result.end_station}")
    out.append(f"Mode: {result.mode}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Line preference: {', '.join(result.preferred_lines)}")
    for notice in result.notices:
        out.append(f"Note: {notice}")

    out.append("")
    out.append(f"Station sequence (end -> start, {len(result.stations)} stations):")
    out.append("  " + " -> ".join(result.stations))

    out.append("")
    out.append("Route segments:")
    for number, segment in enumerate(result.segments, start=1):
        out.append(
            f"  {number}. [{segment['line']}] {segment['start']} -> {segment['end']} "
            f"({segment['stops']} stop(s), {format_distance(segment['distance_m'])})"
        )

    out.append("")
    out.append("Transfer stations:")
    if result.transfers:
        for transfer in result.transfers:
            out.append(
                f"  {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']}"
            )
    else:
        out.append("  None (no transfer required)")

    out.append("")
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append(f"Total distance: {format_distance(result.distance_m)}")
    out.append(f"Number of transfers: {result.transfer_count}")
    out.append(f"Estimated travel time: {result.estimated_time:.1f} minutes")
    out.append("")
    out.append(f"Fare: {result.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def render_json(result: PathResult) -> str:
    """Render the result as a JSON document."""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
