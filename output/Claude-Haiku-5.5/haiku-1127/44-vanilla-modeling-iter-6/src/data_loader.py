"""Loading of the Beijing Subway dataset and construction of the network graph."""

import json
import os

from models import Edge, Graph
from subway_errors import DataLoadError

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path=DATA_FILE_PATH):
    """Read and validate the subway JSON dataset.

    Args:
        path: path of the JSON file (defaults to src/subway_data.json).

    Returns:
        The parsed dictionary with keys "stations" and "connections".

    Raises:
        DataLoadError: if the file cannot be read, is not valid JSON, or does
            not match the expected structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise DataLoadError(f"cannot read '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"invalid JSON in '{path}': {exc}") from exc
    _validate_data(data)
    return data


def _validate_data(data):
    """Check the structure of the dataset; raise DataLoadError on problems."""
    if not isinstance(data, dict):
        raise DataLoadError("top-level JSON value must be an object")
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list) or not isinstance(connections, list):
        raise DataLoadError("'stations' and 'connections' must be lists")

    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise DataLoadError(f"stations[{index}] must be an object")
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise DataLoadError(f"stations[{index}].name must be a non-empty string")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            raise DataLoadError(f"stations[{index}].lines must be a list of strings")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise DataLoadError(f"connections[{index}] must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str):
                raise DataLoadError(f"connections[{index}].{key} must be a string")
        distance = conn.get("distance")
        if (isinstance(distance, bool) or not isinstance(distance, (int, float))
                or distance <= 0):
            raise DataLoadError(
                f"connections[{index}].distance must be a positive number")


def _ensure_station(graph, name, lines):
    """Register a station if needed and attach the given lines to it."""
    if not graph.has_station(name):
        graph.add_station(name, graph.allocate_number(), [])
    for line in lines:
        graph.add_line_to_station(name, line)


def build_graph(data):
    """Build a Graph from a validated subway dataset.

    Station numbers are allocated here (the caller of Graph). Duplicate
    connections between the same pair of stations are ignored after the
    first occurrence; the data checker reports such duplicates.

    Raises:
        DataLoadError: if a connection is invalid for the graph.
    """
    graph = Graph()
    for station in data["stations"]:
        _ensure_station(graph, station["name"], station.get("lines", []))

    for conn in data["connections"]:
        source, dest, line = conn["source"], conn["dest"], conn["line"]
        _ensure_station(graph, source, [line])
        _ensure_station(graph, dest, [line])
        a = graph.number_of(source)
        b = graph.number_of(dest)
        if a == b:
            raise DataLoadError(f"self-loop connection at station '{source}'")
        if graph.edge_between(a, b) is not None:
            continue
        try:
            graph.add_edge(Edge(a, b, conn["distance"], line))
        except ValueError as exc:
            raise DataLoadError(str(exc)) from exc
    return graph


def load_graph(path=DATA_FILE_PATH):
    """Convenience helper: load the dataset file and build the graph."""
    return build_graph(load_subway_data(path))
