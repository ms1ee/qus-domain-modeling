"""Loading of the Beijing Subway dataset and construction of the network model."""

import json
import os
from typing import Any, Dict, Optional

from models import Edge, Graph, Station, SubwayNetwork

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def validate_subway_data(data: Any) -> None:
    """Check the top-level structure of the dataset.

    Raises:
        DataLoadError: if the structure does not match the expected schema.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"Subway data field '{key}' must be a list")


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load and return the JSON content of the subway dataset file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise DataLoadError(f"Subway data file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from None
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from None
    validate_subway_data(data)
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write the dataset back to disk atomically."""
    validate_subway_data(data)
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {exc}") from None


def parse_distance(value: Any) -> Optional[float]:
    """Return a positive distance in meters, or None if the value is invalid."""
    if isinstance(value, bool):
        return None
    try:
        distance = float(value)
    except (TypeError, ValueError):
        return None
    if distance != distance or distance <= 0 or distance == float("inf"):
        return None
    return distance


def build_network(data: Dict[str, Any]) -> SubwayNetwork:
    """Build the weighted undirected graph and lookup tables from raw data.

    Station numbers are assigned here (caller side), in order of first
    appearance in the station list, followed by any station referenced only
    by connections. Invalid connections (self-loops, non-positive distances)
    are skipped; the integrity checker reports them.
    """
    station_to_number: Dict[str, int] = {}
    station_lines: Dict[str, list] = {}

    def register(name: str) -> int:
        if name not in station_to_number:
            station_to_number[name] = len(station_to_number)
            station_lines[name] = []
        return station_to_number[name]

    def add_line(name: str, line: str) -> None:
        if line not in station_lines[name]:
            station_lines[name].append(line)

    for entry in data["stations"]:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        register(name)
        for line in entry.get("lines", []):
            add_line(name, str(line).strip())

    connections = data["connections"]
    for conn in connections:
        src = str(conn.get("source", "")).strip()
        dst = str(conn.get("dest", "")).strip()
        line = str(conn.get("line", "")).strip()
        if not src or not dst or src == dst or not line:
            continue
        register(src)
        register(dst)
        add_line(src, line)
        add_line(dst, line)

    graph = Graph()
    for name, number in station_to_number.items():
        graph.add_vertex(number)
        graph.set_station_lines(name, station_lines[name])

    for conn in connections:
        src = str(conn.get("source", "")).strip()
        dst = str(conn.get("dest", "")).strip()
        line = str(conn.get("line", "")).strip()
        if not src or not dst or src == dst or not line:
            continue
        distance = parse_distance(conn.get("distance"))
        if distance is None:
            continue
        graph.add_edge(Edge(station_to_number[src], station_to_number[dst], distance, line))

    line_names = sorted({line for lines in station_lines.values() for line in lines})
    stations = {
        number: Station(
            station_id=number,
            name=name,
            station_number=f"{number + 1:04d}",
            is_transfer_station=len(station_lines[name]) > 1,
        )
        for name, number in station_to_number.items()
    }
    return SubwayNetwork(
        graph=graph,
        station_to_number=station_to_number,
        stations=stations,
        line_names=line_names,
    )
