"""Query orchestration: input parsing, station resolution and route/fare computation."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from src.path_report import PathResult, build_result
from src.pathfinding import PathfindingConfig, ShortestPath
from src.subway_network import StationNotFoundError, SubwayNetwork

INPUT_FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"


class QueryError(Exception):
    """Base class for user-facing query errors."""


class InputFormatError(QueryError):
    """Raised when the query text does not contain exactly two station names."""


class PathNotFoundError(QueryError):
    """Raised when no route exists between the two stations."""


def parse_query(text: str) -> Tuple[str, str]:
    """Split a 'Starting Station; Ending Station' query into two names.

    Both ';' and ',' (including full-width variants) are accepted as separators.
    """
    if not isinstance(text, str):
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    normalized = text.strip().replace("\uff1b", ";").replace("\uff0c", ",")
    parts = [part.strip() for part in re.split(r"[;,]", normalized)]
    if len(parts) != 2 or not all(parts):
        raise InputFormatError(INPUT_FORMAT_MESSAGE)
    return parts[0], parts[1]


def _resolve(network: SubwayNetwork, name: str, role: str, notices: List[str]) -> str:
    """Resolve a user station name, recording a notice when it was approximated."""
    try:
        official, exact = network.resolve_station(name)
    except StationNotFoundError as exc:
        raise QueryError(
            f"{role} station '{name}' does not exist, please check the station name"
        ) from exc
    if not exact:
        notices.append(
            f"{role} station '{name}' is not an exact match; matched to nearest station '{official}'"
        )
    return official


def run_query(
    network: SubwayNetwork,
    text: str,
    config: Optional[PathfindingConfig] = None,
) -> PathResult:
    """Parse a query, compute the optimal route and fare.

    Raises:
        QueryError: for any user-facing problem (format, unknown station,
            identical stations, no route, calculation failure).
    """
    config = config if config is not None else PathfindingConfig()
    start_input, end_input = parse_query(text)

    notices: List[str] = []
    start_name = _resolve(network, start_input, "Starting", notices)
    end_name = _resolve(network, end_input, "Ending", notices)
    if start_name == end_name:
        raise QueryError("Starting station cannot be the same as the ending station")

    source = network.number_of(start_name)
    target = network.number_of(end_name)
    try:
        search = ShortestPath(network.graph, source, config)
    except (ValueError, KeyError) as exc:
        raise QueryError(f"Path calculation failed: {exc}") from exc

    if not search.has_path_to(target):
        raise PathNotFoundError(
            f"No route found from '{start_name}' to '{end_name}' with the given options"
        )

    stations, edges = search.path_with_edges(target)
    station_names = [network.name_of(number) for number in stations]
    transfer_count = search.get_transfer_count(target)

    try:
        return build_result(
            start_name,
            end_name,
            config,
            notices,
            station_names,
            edges,
            transfer_count,
        )
    except (ValueError, TypeError) as exc:
        raise QueryError(f"Fare calculation failed: {exc}") from exc
