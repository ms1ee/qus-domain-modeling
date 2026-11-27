"""Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module and has
the following layout::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int (meters), "line": str}]}

This module loads that file and converts it into the graph structure used
by the path-finding algorithms.
"""

import json
import os

from models import Edge, Graph

# Absolute path of the bundled data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway data file cannot be loaded or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``).
    :return: the parsed JSON content as a ``dict``.
    :raises DataLoadError: when the file is missing or not valid JSON.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file is not valid JSON: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise DataLoadError("Data file root must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def build_station_mapping(data):
    """Build the ``station_to_number`` dictionary.

    Station numbers are assigned in the order the stations appear in the
    ``stations`` list; stations referenced only by connections are appended
    afterwards.

    :return: (station_to_number, number_to_station)
    """
    station_to_number = {}
    number_to_station = {}

    def _register(name):
        if name not in station_to_number:
            number = len(station_to_number)
            station_to_number[name] = number
            number_to_station[number] = name

    for station in data.get("stations", []):
        name = station.get("name")
        if name:
            _register(name)
    for conn in data.get("connections", []):
        for key in ("source", "dest"):
            name = conn.get(key)
            if name:
                _register(name)
    return station_to_number, number_to_station


def build_graph(data):
    """Create the weighted undirected subway graph from raw data.

    :return: (graph, station_to_number, number_to_station)
    """
    station_to_number, number_to_station = build_station_mapping(data)
    graph = Graph()

    for number in number_to_station:
        graph.add_vertex(number)

    # Line affiliations (stations on more than one line are transfer stations).
    lines_by_station = {name: [] for name in station_to_number}
    for station in data.get("stations", []):
        name = station.get("name")
        if not name:
            continue
        for line in station.get("lines", []) or []:
            if line not in lines_by_station[name]:
                lines_by_station[name].append(line)
    for conn in data.get("connections", []):
        line = conn.get("line")
        for key in ("source", "dest"):
            name = conn.get(key)
            if name and line and line not in lines_by_station[name]:
                lines_by_station[name].append(line)
    for name, lines in lines_by_station.items():
        graph.set_station_lines(name, lines)
        graph.set_station_name(station_to_number[name], name)

    for conn in data.get("connections", []):
        src = conn.get("source")
        dst = conn.get("dest")
        if not src or not dst or src == dst:
            continue
        try:
            distance = int(conn.get("distance", 0))
        except (TypeError, ValueError):
            continue
        if distance < 0:
            continue
        graph.add_edge(
            Edge(station_to_number[src], station_to_number[dst], distance, conn.get("line"))
        )
    return graph, station_to_number, number_to_station
