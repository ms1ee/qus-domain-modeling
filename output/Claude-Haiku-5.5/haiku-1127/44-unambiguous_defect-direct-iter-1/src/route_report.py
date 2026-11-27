"""Route planning, path summary generation and report formatting (text / JSON)."""

import json

from fare_calculator import Sum_money, calculate_estimated_time
from pathfinding import NoPathError, PathfindingConfig, ShortestPath


class RouteResult:
    """Computed route with all derived information needed for reporting.

    Attributes:
        start / end: canonical station names.
        config: PathfindingConfig used for the query.
        station_names: ordered list of station names from start to end.
        edges: list of Edge objects along the path.
        transfers: list of dicts describing each transfer station.
        segments: list of dicts describing consecutive same-line segments.
        lines: unique line names involved, in travel order.
        distance_m: total distance in meters.
        fare: fare in yuan.
        estimated_minutes: estimated travel time in minutes.
    """

    def __init__(self, start, end, config, station_names, edges, transfers, segments,
                 lines, distance_m, fare, estimated_minutes):
        self.start = start
        self.end = end
        self.config = config
        self.station_names = station_names
        self.edges = edges
        self.transfers = transfers
        self.segments = segments
        self.lines = lines
        self.distance_m = distance_m
        self.fare = fare
        self.estimated_minutes = estimated_minutes

    @property
    def transfer_count(self):
        """Number of transfers on the route."""
        return len(self.transfers)

    @property
    def distance_km(self):
        """Total distance in kilometers (2 decimals)."""
        return round(self.distance_m / 1000.0, 2)

    def summary(self):
        """Key figures of the route as a dictionary."""
        return {
            "total_distance_m": self.distance_m,
            "total_distance_km": self.distance_km,
            "total_fare_yuan": self.fare,
            "transfer_count": self.transfer_count,
            "estimated_time_min": self.estimated_minutes,
        }

    def to_dict(self):
        """Structured representation suitable for JSON export."""
        return {
            "query": {
                "start": self.start,
                "end": self.end,
                "mode": self.config.mode,
                "max_transfers": self.config.max_transfers,
                "line_preference": list(self.config.preferred_lines),
            },
            "path": list(self.station_names),
            "distance": {"meters": self.distance_m, "kilometers": self.distance_km},
            "fare": self.fare,
            "estimated_time_min": self.estimated_minutes,
            "transfer_count": self.transfer_count,
            "transfers": self.transfers,
            "lines": list(self.lines),
            "segments": self.segments,
        }


def plan_route(network, start_name, end_name, config=None):
    """Compute the route between two stations and derive all report information.

    Raises:
        ValueError: for unknown stations.
        NoPathError: if no route satisfies the constraints.
    """
    config = config or PathfindingConfig()
    src = network.get_station_number(start_name)
    dst = network.get_station_number(end_name)

    sp = ShortestPath(network.graph, src, config)
    if not sp.has_path(dst):
        if config.max_transfers is not None:
            raise NoPathError(f"No route from '{start_name}' to '{end_name}' within "
                              f"{config.max_transfers} transfer(s)")
        raise NoPathError(f"No route found from '{start_name}' to '{end_name}'")

    numbers, edges = sp.path_with_edges(dst)
    names = [network.station_name(n) for n in numbers]
    distance_m = sum(edge.weight for edge in edges)
    transfers = _find_transfers(network, names, edges)
    segments = _build_segments(names, edges)
    lines = list(dict.fromkeys(edge.line for edge in edges))
    fare = Sum_money(distance_m)
    minutes = calculate_estimated_time(distance_m, len(transfers))

    return RouteResult(
        start=start_name, end=end_name, config=config, station_names=names, edges=edges,
        transfers=transfers, segments=segments, lines=lines, distance_m=distance_m,
        fare=fare, estimated_minutes=minutes,
    )


def _find_transfers(network, names, edges):
    """Identify transfer stations where the travelling line changes."""
    transfers = []
    for i in range(len(edges) - 1):
        if edges[i].line != edges[i + 1].line:
            station = names[i + 1]
            transfers.append({
                "station": station,
                "from_line": edges[i].line,
                "to_line": edges[i + 1].line,
                "station_lines": network.graph.get_station_lines(station),
            })
    return transfers


def _build_segments(names, edges):
    """Group consecutive edges served by the same line into segments."""
    segments = []
    start = 0
    for i, edge in enumerate(edges):
        is_last = i == len(edges) - 1
        if is_last or edges[i + 1].line != edge.line:
            group = edges[start:i + 1]
            segments.append({
                "line": edge.line,
                "from_station": names[start],
                "to_station": names[i + 1],
                "stop_count": len(group) + 1,
                "distance_m": sum(e.weight for e in group),
            })
            start = i + 1
    return segments


def format_text(result):
    """Render a RouteResult as human-readable console text."""
    out = []
    add = out.append
    add("=" * 60)
    add("Beijing Subway Route Report")
    add("=" * 60)
    add(f"Query          : {result.start} -> {result.end}")
    add(f"Mode           : {result.config.mode}")
    if result.config.max_transfers is not None:
        add(f"Max transfers  : {result.config.max_transfers}")
    if result.config.preferred_lines:
        add(f"Preferred lines: {', '.join(result.config.preferred_lines)}")
    add("")
    add("Summary")
    add(f"  Total distance : {result.distance_m} m ({result.distance_km:.2f} km)")
    add(f"  Transfers      : {result.transfer_count}")
    add(f"  Lines involved : {', '.join(result.lines) if result.lines else 'none'}")
    add(f"  Est. time      : {result.estimated_minutes:.1f} min")
    add(f"Fare: {result.fare} yuan")
    add("")
    add("Line segments")
    if not result.segments:
        add("  (no travel required)")
    for i, seg in enumerate(result.segments, 1):
        add(f"  {i}. [{seg['line']}] {seg['from_station']} -> {seg['to_station']} "
            f"({seg['stop_count']} stations, {seg['distance_m']} m)")
    add("")
    add("Transfer stations")
    if not result.transfers:
        add("  (none)")
    for transfer in result.transfers:
        lines_at = ", ".join(transfer["station_lines"]) or "n/a"
        add(f"  - {transfer['station']}: {transfer['from_line']} -> {transfer['to_line']} "
            f"(lines at station: {lines_at})")
    add("")
    add(f"Station sequence ({len(result.station_names)} stations)")
    for i, name in enumerate(result.station_names, 1):
        add(f"  {i:>3}. {name}")
    return "\n".join(out)


def format_json(result, indent=2):
    """Render a RouteResult as JSON text."""
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=indent)


def format_result(result, fmt, indent=2):
    """Render a RouteResult in the requested format ('text' or 'json')."""
    if fmt == "json":
        return format_json(result, indent=indent)
    return format_text(result)
