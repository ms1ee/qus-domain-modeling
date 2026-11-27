"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
The file has the following structure::

    {
        "stations": [{"name": str, "lines": [str, ...]}, ...],
        "connections": [{"source": str, "dest": str,
                         "distance": int (meters), "line": str}, ...]
    }
"""

import json
import os

from models import Edge, Graph

# Absolute path of the bundled data file; valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file content is not valid JSON or lacks the
            required top-level keys.
    """
    if path is None:
        path = DATA_FILE_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Subway data file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be lists")
    return data


def build_graph(data):
    """Build a weighted undirected graph from raw subway data.

    Returns:
        (graph, station_to_number, number_to_station)
        - graph: :class:`models.Graph`
        - station_to_number: dict mapping station name -> station number
        - number_to_station: list where index is the station number
    """
    graph = Graph()
    station_to_number = {}
    number_to_station = []

    def number_of(name):
        if name not in station_to_number:
            station_to_number[name] = len(number_to_station)
            number_to_station.append(name)
            graph.add_vertex(station_to_number[name])
        return station_to_number[name]

    declared_lines = {}
    for station in data.get("stations", []):
        name = station.get("name")
        if not name:
            continue
        number_of(name)
        declared_lines[name] = list(station.get("lines") or [])

    connection_lines = {}
    for conn in data.get("connections", []):
        src, dst = conn.get("source"), conn.get("dest")
        dist, line = conn.get("distance"), conn.get("line")
        if not src or not dst:
            continue
        if not isinstance(dist, (int, float)) or isinstance(dist, bool) or dist < 0:
            continue
        s, d = number_of(src), number_of(dst)
        graph.add_edge(Edge(s, d, dist, line))
        for n in (src, dst):
            connection_lines.setdefault(n, [])
            if line is not None and line not in connection_lines[n]:
                connection_lines[n].append(line)

    for name in number_to_station:
        lines = declared_lines.get(name) or connection_lines.get(name, [])
        graph.set_station_lines(name, lines)

    return graph, station_to_number, number_to_station
