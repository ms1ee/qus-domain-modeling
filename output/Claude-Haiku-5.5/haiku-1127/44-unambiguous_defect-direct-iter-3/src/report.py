"""Path result construction, summary generation and report rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from errors import PathNotFoundError, QueryError
from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge
from network import SubwayNetwork
from pathfinding import (
    MODE_COMPREHENSIVE,
    MODE_LEAST_TRANSFER,
    MODE_SHORTEST_DISTANCE,
    PathfindingConfig,
    ShortestPath,
)

MODE_LABELS: Dict[str, str] = {
    MODE_SHORTEST_DISTANCE: "Shortest distance",
    MODE_LEAST_TRANSFER: "Minimum transfers",
    MODE_COMPREHENSIVE: "Comprehensive optimal",
}


@dataclass
class PathSegment:
    """A continuous ride on a single line."""

    line: str
    stations: List[str]
    distance_m: int

    @property
    def stop_count(self) -> int:
        return len(self.stations) - 1


@dataclass
class TransferInfo:
    """A station where the passenger changes from one line to another."""

    station: str
    from_line: str
    to_line: str
    lines: List[str]


@dataclass
class PathResult:
    """Complete result of a route query."""

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]
    segments: List[PathSegment]
    transfers: List[TransferInfo]
    lines_used: List[str]
    total_distance_m: int
    fare: int
    transfer_count: int
    estimated_minutes: float

    @property
    def total_distance_km(self) -> float:
        return round(self.total_distance_m / 1000.0, 2)


def _unique(items: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(items))


def _build_segments(names: List[str], edges: List[Edge]) -> List[PathSegment]:
    segments: List[PathSegment] = []
    if not edges:
        return segments
    start = 0
    for i in range(1, len(edges) + 1):
        if i == len(edges) or edges[i].line != edges[start].line:
            distance = sum(e.distance for e in edges[start:i])
            segments.append(
                PathSegment(
                    line=edges[start].line,
                    stations=names[start : i + 1],
                    distance_m=distance,
                )
            )
            start = i
    return segments


def build_path_result(
    network: SubwayNetwork,
    start_name: str,
    end_name: str,
    config: Optional[PathfindingConfig] = None,
) -> PathResult:
    """Compute the route between two official station names and summarise it."""
    config = config if config is not None else PathfindingConfig()
    config.validate()
    if start_name == end_name:
        raise QueryError("Starting station cannot be the same as the ending station")

    source = network.number_of(start_name)
    target = network.number_of(end_name)
    shortest = ShortestPath(network.graph, source, config)
    if not shortest.has_path_to(target):
        raise PathNotFoundError(
            f"No route found from '{start_name}' to '{end_name}' with the current settings"
        )

    numbers, edges = shortest.path_with_edges(target)
    names = [network.name_of(n) for n in numbers]
    total = sum(e.distance for e in edges)

    transfers: List[TransferInfo] = []
    for k in range(1, len(edges)):
        if edges[k - 1].line != edges[k].line:
            station = names[k]
            transfers.append(
                TransferInfo(
                    station=station,
                    from_line=edges[k - 1].line,
                    to_line=edges[k].line,
                    lines=network.lines_of(station),
                )
            )

    transfer_count = len(transfers)
    return PathResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        segments=_build_segments(names, edges),
        transfers=transfers,
        lines_used=_unique([e.line for e in edges]),
        total_distance_m=total,
        fare=Sum_money(total),
        transfer_count=transfer_count,
        estimated_minutes=calculate_estimated_time(total, transfer_count),
    )


def build_summary(result: PathResult) -> Dict[str, Any]:
    """Key figures of a path: distance, fare, transfers and estimated time."""
    return {
        "total_distance_km": result.total_distance_km,
        "total_fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": result.estimated_minutes,
    }


def render_text(result: PathResult) -> str:
    """Human-readable console report."""
    out: List[str] = []
    out.append("=" * 60)
    out.append(f"Route: {result.start} -> {result.end}")
    out.append(f"Query mode: {MODE_LABELS.get(result.mode, result.mode)}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Preferred lines: {', '.join(result.preferred_lines)}")
    out.append("-" * 60)
    out.append(f"Station sequence ({len(result.stations)} stations):")
    out.append("  " + " -> ".join(result.stations))
    out.append(
        f"Total distance: {result.total_distance_m} m "
        f"({result.total_distance_km:.2f} km)"
    )
    out.append(f"Transfers: {result.transfer_count}")
    out.append(f"Estimated travel time: {result.estimated_minutes:.1f} min")
    out.append("Line segments:")
    for index, segment in enumerate(result.segments, start=1):
        out.append(
            f"  {index}. {segment.line}: {segment.stations[0]} -> "
            f"{segment.stations[-1]} ({segment.stop_count} stops, "
            f"{segment.distance_m} m)"
        )
    out.append("Transfer stations:")
    if not result.transfers:
        out.append("  None (no transfer needed)")
    for transfer in result.transfers:
        out.append(
            f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line} "
            f"(lines at station: {', '.join(transfer.lines)})"
        )
    out.append(f"Lines involved: {', '.join(result.lines_used)}")
    out.append("-" * 60)
    out.append(f"Fare: {result.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def render_json(result: PathResult) -> str:
    """Structured JSON report for programmatic integration."""
    payload = {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "preferred_lines": result.preferred_lines,
        },
        "path": {
            "stations": result.stations,
            "station_count": len(result.stations),
        },
        "distance": {
            "meters": result.total_distance_m,
            "kilometers": result.total_distance_km,
        },
        "fare": result.fare,
        "estimated_time_minutes": result.estimated_minutes,
        "transfer_count": result.transfer_count,
        "lines": result.lines_used,
        "transfers": [
            {
                "station": t.station,
                "from_line": t.from_line,
                "to_line": t.to_line,
                "lines": t.lines,
            }
            for t in result.transfers
        ],
        "segments": [
            {
                "line": s.line,
                "start": s.stations[0],
                "end": s.stations[-1],
                "stations": s.stations,
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
        "summary": build_summary(result),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
