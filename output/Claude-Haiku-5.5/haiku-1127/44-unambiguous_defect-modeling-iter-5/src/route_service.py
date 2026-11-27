"""Route planning service: resolves stations, runs the path search, and
assembles fare, time, transfer and segment information into a RouteResult."""

import difflib
from dataclasses import dataclass, field
from typing import List, Optional

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import (
    MODE_SHORTEST_DISTANCE,
    VALID_MODES,
    PathfindingConfig,
    ShortestPath,
)


class QueryError(Exception):
    """Base class for invalid user queries."""


class StationNotFoundError(QueryError):
    """Raised when a station name does not exist in the network."""


class SameStationError(QueryError):
    """Raised when the starting and ending stations are identical."""


@dataclass
class TransferInfo:
    """A line change at a station."""
    station: str
    from_line: str
    to_line: str


@dataclass
class SegmentInfo:
    """A contiguous ride on a single line."""
    line: str
    start_station: str
    end_station: str
    station_count: int
    distance_m: float


@dataclass
class RouteResult:
    """Complete result of a route query."""
    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]
    station_names: List[str]
    edges: list
    distance_m: float
    transfer_count: int
    transfers: List[TransferInfo] = field(default_factory=list)
    segments: List[SegmentInfo] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    fare_yuan: int = 0
    estimated_time_minutes: float = 0.0


def resolve_station(dm, raw_name, role):
    """Map user input to an official station name or raise StationNotFoundError.

    Args:
        dm: DataManager instance.
        raw_name: The name typed by the user.
        role: "Starting" or "Ending", used in the error message.
    """
    std = dm.standardize_station_name(raw_name)
    if std is None:
        display = str(raw_name).strip()
        message = f"{role} station '{display}' does not exist, please check the station name"
        suggestions = difflib.get_close_matches(display, dm.station_names(), n=3, cutoff=0.5)
        if suggestions:
            message += f". Did you mean: {', '.join(suggestions)}?"
        raise StationNotFoundError(message)
    return std


def _extract_segments(names, edges):
    """Group consecutive edges by line into SegmentInfo records."""
    segments = []
    i = 0
    while i < len(edges):
        line = edges[i].line
        j = i
        distance = 0.0
        while j < len(edges) and edges[j].line == line:
            distance += edges[j].distance
            j += 1
        segments.append(SegmentInfo(
            line=line,
            start_station=names[i],
            end_station=names[j],
            station_count=j - i + 1,
            distance_m=float(distance),
        ))
        i = j
    return segments


def _extract_transfers(names, edges):
    """Return the transfer records (line changes) along the path."""
    transfers = []
    for i in range(len(edges) - 1):
        if edges[i].line != edges[i + 1].line:
            transfers.append(TransferInfo(
                station=names[i + 1],
                from_line=edges[i].line,
                to_line=edges[i + 1].line,
            ))
    return transfers


def plan_route(dm, start, end, mode=MODE_SHORTEST_DISTANCE, max_transfers=None, line_preference=None):
    """Compute the route between two stations and assemble the full result.

    Args:
        dm: DataManager providing the graph and station names.
        start: Starting station name (user input).
        end: Ending station name (user input).
        mode: One of pathfinding.VALID_MODES.
        max_transfers: Optional maximum number of transfers.
        line_preference: Optional official line name to prefer.

    Returns:
        RouteResult

    Raises:
        StationNotFoundError, SameStationError, QueryError,
        pathfinding.PathNotFoundError
    """
    start_name = resolve_station(dm, start, "Starting")
    end_name = resolve_station(dm, end, "Ending")
    if start_name == end_name:
        raise SameStationError("Starting station cannot be the same as the ending station")
    if mode not in VALID_MODES:
        raise QueryError(f"Unknown mode '{mode}'")

    preferred = [line_preference] if line_preference else []
    try:
        config = PathfindingConfig(mode=mode, max_transfers=max_transfers, preferred_lines=preferred)
    except ValueError as exc:
        raise QueryError(str(exc)) from exc

    search = ShortestPath(dm.graph, dm.get_station_number(start_name), config)
    node_ids, edges = search.path_with_edges(dm.get_station_number(end_name))

    names = [dm.get_station_name(n) for n in node_ids]
    distance = float(sum(e.distance for e in edges))
    transfers = _extract_transfers(names, edges)
    transfer_count = len(transfers)
    segments = _extract_segments(names, edges)

    lines = []
    for seg in segments:
        if seg.line not in lines:
            lines.append(seg.line)

    fare = Sum_money(distance)
    time_minutes = calculate_estimated_time(distance, transfer_count)

    return RouteResult(
        start_station=start_name,
        end_station=end_name,
        mode=mode,
        max_transfers=max_transfers,
        line_preference=line_preference,
        station_names=names,
        edges=edges,
        distance_m=distance,
        transfer_count=transfer_count,
        transfers=transfers,
        segments=segments,
        lines=lines,
        fare_yuan=fare,
        estimated_time_minutes=time_minutes,
    )
