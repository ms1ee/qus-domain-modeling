"""Path summary, visualization, and export (console text, JSON, file output)."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fare_calculator import FareCalculationError, Sum_money, calculate_estimated_time
from models import Edge
from pathfinding import NoPathError, PathCalculationError, PathfindingConfig, ShortestPath


@dataclass
class TransferInfo:
    """A transfer point where the passenger changes from one line to another."""

    station: str
    from_line: str
    to_line: str


@dataclass
class SegmentInfo:
    """A continuous ride on a single line."""

    line: str
    start: str
    end: str
    stops: int
    distance_m: int


@dataclass
class PathResult:
    """Structured result of a single route query."""

    start: str
    end: str
    mode: str
    max_transfers: Optional[int]
    preferred_lines: List[str]
    stations: List[str]
    segments: List[SegmentInfo]
    transfers: List[TransferInfo]
    lines_involved: List[str]
    distance_m: int
    fare: int
    transfer_count: int
    estimated_time_min: float

    @property
    def distance_km(self) -> float:
        return self.distance_m / 1000.0


def count_transfers(edges: List[Edge]) -> int:
    """Count line changes between consecutive edges of a path."""
    return sum(1 for i in range(1, len(edges)) if edges[i - 1].line != edges[i].line)


def _transfer_details(stations: List[str], edges: List[Edge]) -> List[TransferInfo]:
    transfers = []
    for i in range(1, len(edges)):
        if edges[i - 1].line != edges[i].line:
            transfers.append(TransferInfo(stations[i], edges[i - 1].line, edges[i].line))
    return transfers


def _segments(stations: List[str], edges: List[Edge]) -> List[SegmentInfo]:
    segments: List[SegmentInfo] = []
    index = 0
    while index < len(edges):
        line = edges[index].line
        begin = index
        distance = 0
        while index < len(edges) and edges[index].line == line:
            distance += edges[index].distance
            index += 1
        segments.append(SegmentInfo(
            line=line,
            start=stations[begin],
            end=stations[index],
            stops=index - begin,
            distance_m=distance,
        ))
    return segments


def build_path_result(network, start_name: str, end_name: str,
                      config: PathfindingConfig) -> PathResult:
    """Compute the route between two stations and build a summary.

    Raises:
        NoPathError: if no route satisfies the constraints.
        PathCalculationError: on unexpected failures during path search.
        FareCalculationError: if the fare cannot be computed.
    """
    source = network.number_of(start_name)
    target = network.number_of(end_name)

    try:
        finder = ShortestPath(network.graph, source, config)
        if not finder.has_path_to(target):
            raise NoPathError(
                f"No route found between '{start_name}' and '{end_name}' "
                f"under the current settings"
            )
        numbers, edges = finder.path_with_edges(target)
    except NoPathError:
        raise
    except Exception as exc:  # defensive: report unexpected algorithm failures
        raise PathCalculationError(f"Path calculation failed: {exc}") from exc

    stations = [network.name_of(n) for n in numbers]
    total_distance = sum(edge.distance for edge in edges)
    transfer_count = count_transfers(edges)

    try:
        fare = Sum_money(total_distance)
        estimated = calculate_estimated_time(total_distance, transfer_count)
    except Exception as exc:
        raise FareCalculationError(f"Fare calculation failed: {exc}") from exc

    lines_involved: List[str] = []
    for edge in edges:
        if edge.line not in lines_involved:
            lines_involved.append(edge.line)

    return PathResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=stations,
        segments=_segments(stations, edges),
        transfers=_transfer_details(stations, edges),
        lines_involved=lines_involved,
        distance_m=total_distance,
        fare=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated,
    )


def format_distance(meters: float) -> str:
    """Show distance in meters for short trips and kilometers for long trips,
    always including both units."""
    if meters < 1000:
        return f"{meters:.0f} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters:.0f} m)"


def format_text(result: PathResult) -> str:
    """Render a result as console-friendly text."""
    rule = "=" * 60
    out: List[str] = [
        rule,
        "Beijing Subway Fare Query",
        rule,
        f"Starting station: {result.start}",
        f"Ending station:   {result.end}",
        f"Mode: {result.mode}",
    ]
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Preferred lines: {', '.join(result.preferred_lines)}")

    out.append("")
    out.append(f"Station sequence ({len(result.stations)} stations):")
    for index, station in enumerate(result.stations, 1):
        out.append(f"  {index:>3}. {station}")

    out.append("")
    out.append(f"Total distance: {format_distance(result.distance_m)}")

    out.append("")
    out.append("Line segments:")
    if not result.segments:
        out.append("  (no travel required)")
    for index, seg in enumerate(result.segments, 1):
        out.append(
            f"  {index}. {seg.line}: {seg.start} -> {seg.end} "
            f"({seg.stops} stops, {format_distance(seg.distance_m)})"
        )

    out.append("")
    out.append(f"Transfers: {result.transfer_count}")
    if result.transfers:
        out.append("Transfer stations:")
        for transfer in result.transfers:
            out.append(f"  - {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("Transfer stations: none")
    out.append(f"Lines involved: {', '.join(result.lines_involved) or 'none'}")
    out.append(f"Estimated time: {result.estimated_time_min:.1f} min")
    out.append("")
    out.append(f"Fare: {result.fare} yuan")
    out.append(rule)
    return "\n".join(out)


def to_dict(result: PathResult) -> Dict[str, Any]:
    """Convert a result into a JSON-serializable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": result.stations,
        "distance_m": result.distance_m,
        "distance_km": round(result.distance_km, 3),
        "fare": result.fare,
        "estimated_time_min": result.estimated_time_min,
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": result.lines_involved,
        "segments": [
            {
                "line": s.line,
                "start": s.start,
                "end": s.end,
                "stops": s.stops,
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
    }


def format_json(result: PathResult, indent: Optional[int] = 2) -> str:
    """Render a result as a JSON string."""
    return json.dumps(to_dict(result), ensure_ascii=False, indent=indent)


def render(result: PathResult, fmt: str) -> str:
    """Render a result in the requested format (``text`` or ``json``)."""
    if fmt == "json":
        return format_json(result)
    return format_text(result)


def export_result(result: PathResult, fmt: str, file_path: str) -> None:
    """Append a query result to ``file_path``.

    Text results are appended as blocks separated by blank lines; JSON results
    are appended as one compact JSON object per line (JSON Lines).

    Raises:
        OSError: if the file cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)
    if fmt == "json":
        content = json.dumps(to_dict(result), ensure_ascii=False) + "\n"
    else:
        content = format_text(result) + "\n\n"
    with open(file_path, "a", encoding="utf-8") as handle:
        handle.write(content)
