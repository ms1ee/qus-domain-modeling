"""Route construction: turns a computed path into a descriptive Route object."""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from fare_calculator import Sum_money, calculate_estimated_time
from models import Edge, SubwayNetwork


@dataclass(frozen=True)
class Query:
    """A passenger query."""

    start_station: str
    end_station: str
    mode: str
    max_transfers: Optional[int]
    line_preference: Optional[str]


@dataclass(frozen=True)
class TransferInfo:
    """A place where the journey changes line."""

    station: str
    from_line: str
    to_line: str


@dataclass(frozen=True)
class RouteSegment:
    """A maximal run of consecutive stations on one line."""

    start_station: str
    end_station: str
    line: str
    distance_meters: float
    station_count: int


@dataclass(frozen=True)
class PathSummary:
    """Key figures extracted from a route."""

    total_distance_km: float
    total_fare_yuan: int
    transfer_count: int
    estimated_time_minutes: float


@dataclass
class Route:
    """Complete description of a computed journey."""

    query: Query
    stations: List[str]
    segments: List[RouteSegment]
    transfers: List[TransferInfo]
    involved_lines: List[str]
    total_distance_meters: float
    transfer_count: int
    estimated_time_minutes: float
    fare_yuan: int

    def summary(self) -> PathSummary:
        """Return a PathSummary derived from this route."""
        return PathSummary(
            total_distance_km=round(self.total_distance_meters / 1000.0, 2),
            total_fare_yuan=self.fare_yuan,
            transfer_count=self.transfer_count,
            estimated_time_minutes=self.estimated_time_minutes,
        )


def build_route(
    network: SubwayNetwork,
    query: Query,
    station_numbers: Sequence[int],
    edges: Sequence[Edge],
) -> Route:
    """Create a Route from station numbers and the edges connecting them.

    A transfer is counted each time consecutive edges belong to different lines.

    Raises:
        ValueError: if fare or time calculation fails on the given data.
    """
    names = [network.name_of(number) for number in station_numbers]

    involved_lines: List[str] = []
    for edge in edges:
        if edge.line not in involved_lines:
            involved_lines.append(edge.line)

    segments: List[RouteSegment] = []
    transfers: List[TransferInfo] = []
    if edges:
        segment_start = 0
        for i in range(1, len(edges) + 1):
            if i == len(edges) or edges[i].line != edges[segment_start].line:
                segment_edges = edges[segment_start:i]
                segments.append(
                    RouteSegment(
                        start_station=names[segment_start],
                        end_station=names[i],
                        line=edges[segment_start].line,
                        distance_meters=float(sum(e.distance for e in segment_edges)),
                        station_count=i - segment_start + 1,
                    )
                )
                if i < len(edges):
                    transfers.append(
                        TransferInfo(
                            station=names[i],
                            from_line=edges[i - 1].line,
                            to_line=edges[i].line,
                        )
                    )
                segment_start = i

    total_distance = float(sum(e.distance for e in edges))
    transfer_count = len(transfers)
    fare = Sum_money(total_distance)
    estimated_time = calculate_estimated_time(total_distance, transfer_count)

    return Route(
        query=query,
        stations=names,
        segments=segments,
        transfers=transfers,
        involved_lines=involved_lines,
        total_distance_meters=total_distance,
        transfer_count=transfer_count,
        estimated_time_minutes=estimated_time,
        fare_yuan=fare,
    )
