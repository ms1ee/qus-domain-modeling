"""Route computation, path summary and report rendering (console text and JSON)."""

import json
from dataclasses import dataclass, field

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import PathfindingConfig, ShortestPath


class RouteError(Exception):
    """Base class for route query errors."""


class RouteNotFoundError(RouteError):
    """Raised when no path exists under the given configuration."""


@dataclass
class RouteSegment:
    """A continuous ride on a single line."""

    line: str
    start: str
    end: str
    stations: list = field(default_factory=list)
    distance_m: int = 0

    @property
    def stop_count(self):
        """Number of inter-station hops within the segment."""
        return len(self.stations) - 1


@dataclass
class TransferInfo:
    """A line change at a transfer station."""

    station: str
    from_line: str
    to_line: str


@dataclass
class RouteResult:
    """Complete result of a route query."""

    start: str
    end: str
    mode: str
    max_transfers: object
    preferred_lines: list
    stations: list
    segments: list
    transfers: list
    distance_m: int
    fare: int
    transfer_count: int
    estimated_time_min: float

    @property
    def lines(self):
        """Ordered list of unique lines used by the route."""
        result = []
        for segment in self.segments:
            if segment.line not in result:
                result.append(segment.line)
        return result

    @property
    def distance_km(self):
        """Total distance in kilometers."""
        return self.distance_m / 1000.0


def _build_segments(names, edges):
    """Group consecutive edges on the same line into segments."""
    segments = []
    for index, edge in enumerate(edges):
        start = names[index]
        end = names[index + 1]
        if segments and segments[-1].line == edge.line:
            segment = segments[-1]
            segment.end = end
            segment.stations.append(end)
            segment.distance_m += edge.distance
        else:
            segments.append(RouteSegment(
                line=edge.line, start=start, end=end,
                stations=[start, end], distance_m=edge.distance,
            ))
    return segments


def _build_transfers(segments):
    """Derive transfer details from consecutive segments."""
    transfers = []
    for previous, current in zip(segments, segments[1:]):
        transfers.append(TransferInfo(
            station=current.start, from_line=previous.line, to_line=current.line,
        ))
    return transfers


def compute_route(network, start_name, end_name, config=None):
    """Compute the route, fare and summary between two official station names."""
    config = config or PathfindingConfig()
    try:
        source = network.number_of(start_name)
        target = network.number_of(end_name)
    except KeyError as exc:
        raise RouteError(f"Unknown station: {exc}") from exc

    try:
        sp = ShortestPath(network.graph, source, config)
    except (ValueError, KeyError) as exc:
        raise RouteError(f"Path calculation failed: {exc}") from exc

    stations, edges = sp.path_with_edges(target)
    if not stations or stations[-1] != target:
        raise RouteNotFoundError(
            f"No route found from '{start_name}' to '{end_name}' with the given options"
        )

    names = [network.name_of(number) for number in stations]
    segments = _build_segments(names, edges)
    transfers = _build_transfers(segments)
    distance_m = sum(edge.distance for edge in edges)
    transfer_count = sp.get_transfer_count(target)

    try:
        fare = Sum_money(distance_m)
        estimated_time = calculate_estimated_time(distance_m, transfer_count)
    except (TypeError, ValueError) as exc:
        raise RouteError(f"Fare calculation failed: {exc}") from exc

    return RouteResult(
        start=start_name,
        end=end_name,
        mode=config.mode,
        max_transfers=config.max_transfers,
        preferred_lines=list(config.preferred_lines),
        stations=names,
        segments=segments,
        transfers=transfers,
        distance_m=distance_m,
        fare=fare,
        transfer_count=transfer_count,
        estimated_time_min=estimated_time,
    )


def format_distance(meters):
    """Show distance in meters for short trips and kilometers for long trips, with both units."""
    if meters < 1000:
        return f"{meters} m ({meters / 1000:.2f} km)"
    return f"{meters / 1000:.2f} km ({meters} m)"


def build_summary(result):
    """Return the key figures of a route as a dictionary."""
    return {
        "total_distance_km": round(result.distance_km, 3),
        "total_fare_yuan": result.fare,
        "transfer_count": result.transfer_count,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
    }


def to_dict(result):
    """Convert a RouteResult into a JSON-serializable dictionary."""
    return {
        "query": {
            "start": result.start,
            "end": result.end,
            "mode": result.mode,
            "max_transfers": result.max_transfers,
            "line_preference": result.preferred_lines,
        },
        "path": list(result.stations),
        "distance": {
            "meters": result.distance_m,
            "kilometers": round(result.distance_km, 3),
        },
        "fare": result.fare,
        "estimated_time_minutes": round(result.estimated_time_min, 1),
        "transfer_count": result.transfer_count,
        "transfers": [
            {"station": t.station, "from_line": t.from_line, "to_line": t.to_line}
            for t in result.transfers
        ],
        "lines": result.lines,
        "segments": [
            {
                "line": s.line,
                "start": s.start,
                "end": s.end,
                "stations": list(s.stations),
                "distance_m": s.distance_m,
            }
            for s in result.segments
        ],
        "summary": build_summary(result),
    }


def format_text(result):
    """Render the route as console-friendly text."""
    out = []
    out.append("=" * 60)
    out.append(f"Route: {result.start} -> {result.end}")
    out.append(f"Mode: {result.mode}")
    if result.max_transfers is not None:
        out.append(f"Max transfers: {result.max_transfers}")
    if result.preferred_lines:
        out.append(f"Line preference: {', '.join(result.preferred_lines)}")
    out.append("-" * 60)
    out.append(f"Station sequence ({len(result.stations)} stations):")
    for index, name in enumerate(result.stations, 1):
        out.append(f"  {index:>3}. {name}")
    out.append("-" * 60)
    out.append("Line segments:")
    for segment in result.segments:
        out.append(
            f"  [{segment.line}] {segment.start} -> {segment.end} "
            f"({segment.stop_count} stops, {format_distance(segment.distance_m)})"
        )
    out.append("Transfer details:")
    if result.transfers:
        for transfer in result.transfers:
            out.append(f"  Transfer at {transfer.station}: {transfer.from_line} -> {transfer.to_line}")
    else:
        out.append("  No transfers required")
    out.append(f"Lines involved: {', '.join(result.lines)}")
    out.append("-" * 60)
    out.append(f"Total distance: {format_distance(result.distance_m)}")
    out.append(f"Transfers: {result.transfer_count}")
    out.append(f"Estimated time: {result.estimated_time_min:.1f} minutes")
    out.append(f"Fare: {result.fare} yuan")
    out.append("=" * 60)
    return "\n".join(out)


def render_result(result, fmt, compact=False):
    """Render a route in the requested format ('text' or 'json').

    With ``compact=True`` JSON is written on a single line (JSON Lines style),
    which is used when appending results to an output file.
    """
    if fmt == "json":
        return json.dumps(to_dict(result), ensure_ascii=False, indent=None if compact else 2)
    if fmt == "text":
        return format_text(result)
    raise ValueError(f"Unsupported output format: {fmt}")


def append_to_file(path, content):
    """Append rendered content to a file (UTF-8)."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content.rstrip("\n") + "\n\n")
