"""
Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module and has the
following structure::

    {
        "stations":    [{"name": str, "lines": [str, ...]}, ...],
        "connections": [{"source": str, "dest": str,
                         "distance": int (meters), "line": str}, ...]
    }

Besides the raw loader this module offers helpers that build the two core
data structures required by the PRD:

* ``station_to_number`` - a dictionary mapping station names to numbers
* ``graph``             - a dictionary based adjacency list representing the
                          weighted undirected network graph
"""

import json
import os

#: Absolute path of the bundled data file (valid from any working directory).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(ValueError):
    """Raised when the subway data file cannot be parsed or has a bad structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file and return its content as a dict.

    :param path: path of the JSON file (defaults to :data:`DATA_FILE_PATH`).
    :raises FileNotFoundError: if the file does not exist.
    :raises DataLoadError: if the file is not valid JSON or not a JSON object.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise DataLoadError(f"Invalid JSON in data file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise DataLoadError(f"Data file '{path}' must contain a JSON object")
    return data


def build_station_to_number(data):
    """Build the ``station_to_number`` dictionary (station name -> number).

    Stations are numbered in order of appearance in the ``stations`` list;
    stations that only appear in ``connections`` are appended afterwards.
    """
    station_to_number = {}
    for station in data.get("stations", []) or []:
        name = str(station.get("name", "")).strip()
        if name and name not in station_to_number:
            station_to_number[name] = len(station_to_number)
    for conn in data.get("connections", []) or []:
        for key in ("source", "dest"):
            name = str(conn.get(key, "")).strip()
            if name and name not in station_to_number:
                station_to_number[name] = len(station_to_number)
    return station_to_number


def build_graph_dict(data, station_to_number=None):
    """Build the ``graph`` dictionary: an undirected weighted adjacency list.

    The result maps a station number to a list of ``(neighbor_number,
    distance_in_meters, line_name)`` tuples. Each connection is inserted in
    both directions.
    """
    if station_to_number is None:
        station_to_number = build_station_to_number(data)
    graph = {number: [] for number in station_to_number.values()}
    for conn in data.get("connections", []) or []:
        source = str(conn.get("source", "")).strip()
        dest = str(conn.get("dest", "")).strip()
        if source not in station_to_number or dest not in station_to_number:
            continue
        try:
            distance = int(conn.get("distance"))
        except (TypeError, ValueError):
            continue
        if distance < 0 or source == dest:
            continue
        line = conn.get("line")
        u, v = station_to_number[source], station_to_number[dest]
        graph[u].append((v, distance, line))
        graph[v].append((u, distance, line))
    return graph
