"""Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
Its structure is::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int (meters), "line": str}]}
"""

import json
import os

# Absolute path of the bundled data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be loaded."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path to the JSON data file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict)
    :raises DataLoadError: if the file is missing or malformed
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


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def build_graph(data):
    """Build a directed weighted graph from the loaded data.

    Station numbers are assigned here (in order of appearance) and passed to
    the ``Graph``.

    :return: tuple ``(graph, station_to_number, number_to_station)``
    """
    from models import Edge, Graph

    graph = Graph()
    station_to_number = {}
    number_to_station = {}

    def _number_of(name):
        if name not in station_to_number:
            num = len(station_to_number)
            station_to_number[name] = num
            number_to_station[num] = name
            graph.add_vertex(num)
        return station_to_number[name]

    for station in data.get("stations", []):
        name = station.get("name")
        if not name:
            continue
        _number_of(name)
        graph.set_station_lines(name, list(station.get("lines", [])))

    for conn in data.get("connections", []):
        src = conn.get("source")
        dst = conn.get("dest")
        if not src or not dst:
            continue
        try:
            distance = int(conn.get("distance", 0))
        except (TypeError, ValueError):
            continue
        s = _number_of(src)
        d = _number_of(dst)
        line = conn.get("line")
        graph.add_edge(Edge(s, d, distance, line))
        # Make sure every endpoint has a line list (transfer detection).
        for nm in (src, dst):
            lines = graph.station_lines.setdefault(nm, [])
            if line and line not in lines:
                lines.append(line)

    return graph, station_to_number, number_to_station
