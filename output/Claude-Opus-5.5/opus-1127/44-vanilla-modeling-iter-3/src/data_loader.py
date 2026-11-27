"""Data loading utilities for the Beijing Subway fare calculation system.

This module locates and reads ``subway_data.json`` and converts the raw JSON
content into the graph data structures used by the path-finding module.

The JSON format is::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int (meters), "line": str}]}
"""

import json
import os

from models import Edge, Graph

# Absolute path of the bundled data file; valid from any working directory.
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway data file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is not valid JSON or has the wrong shape.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    return data


def build_graph(data):
    """Build the weighted undirected graph from raw subway data.

    Returns:
        (graph, station_to_number, number_to_station)
        ``station_to_number`` maps station names to integer numbers;
        ``number_to_station`` is the reverse mapping.
    """
    graph = Graph()
    station_to_number = {}
    number_to_station = {}

    def register(name, lines=None):
        if name not in station_to_number:
            number = len(station_to_number)
            station_to_number[name] = number
            number_to_station[number] = name
            graph.add_vertex(number)
            graph.set_station_lines(name, list(lines or []))
        elif lines:
            merged = list(graph.station_lines.get(name, []))
            for line in lines:
                if line not in merged:
                    merged.append(line)
            graph.set_station_lines(name, merged)
        return station_to_number[name]

    for station in data.get("stations", []) or []:
        name = station.get("name")
        if not name:
            continue
        register(name, station.get("lines", []) or [])

    for conn in data.get("connections", []) or []:
        src_name = conn.get("source")
        dst_name = conn.get("dest")
        if not src_name or not dst_name:
            continue
        line = conn.get("line", "")
        src = register(src_name, [line] if line else None)
        dst = register(dst_name, [line] if line else None)
        try:
            distance = int(conn.get("distance", 0))
        except (TypeError, ValueError):
            continue
        if distance < 0:
            continue
        graph.add_edge(Edge(src, dst, distance, line))

    return graph, station_to_number, number_to_station
