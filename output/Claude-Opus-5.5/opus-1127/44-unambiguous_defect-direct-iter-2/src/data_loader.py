"""Data loading utilities for the Beijing Subway fare calculation system.

This module locates and loads ``subway_data.json`` and builds the network
data structures:

* ``station_to_number``: a dictionary mapping station names to numbers
* ``graph``: a weighted undirected graph (see :class:`models.Graph`)
"""

import json
import os

from models import Edge, Graph

# Absolute path of the data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway JSON data file and return its content as a dict.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is not valid JSON or has the wrong structure.
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
        raise ValueError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def build_station_mapping(data):
    """Assign a number to every station.

    Stations are numbered in the order they appear in ``data['stations']``;
    stations referenced only by connections are numbered afterwards.

    Returns:
        (station_to_number, number_to_station)
    """
    station_to_number = {}
    number_to_station = {}

    def _register(name):
        if name not in station_to_number:
            num = len(station_to_number)
            station_to_number[name] = num
            number_to_station[num] = name

    for station in data.get("stations", []):
        name = station.get("name")
        if isinstance(name, str) and name:
            _register(name)
    for conn in data.get("connections", []):
        for key in ("source", "dest"):
            name = conn.get(key)
            if isinstance(name, str) and name:
                _register(name)
    return station_to_number, number_to_station


def build_graph(data):
    """Build the subway graph from loaded data.

    Returns:
        (graph, station_to_number, number_to_station)
    """
    station_to_number, number_to_station = build_station_mapping(data)
    graph = Graph()
    for num in number_to_station:
        graph.add_vertex(num)

    for station in data.get("stations", []):
        name = station.get("name")
        if isinstance(name, str) and name:
            graph.set_station_lines(name, list(station.get("lines", []) or []))

    for conn in data.get("connections", []):
        src = conn.get("source")
        dst = conn.get("dest")
        dist = conn.get("distance")
        line = conn.get("line", "")
        if src not in station_to_number or dst not in station_to_number:
            continue
        if src == dst:
            continue
        if isinstance(dist, bool) or not isinstance(dist, (int, float)) or dist < 0:
            continue
        graph.add_edge(Edge(station_to_number[src], station_to_number[dst], dist, line))
        # Make sure line affiliation information is consistent.
        for name in (src, dst):
            lines = graph.station_lines.setdefault(name, [])
            if line and line not in lines:
                lines.append(line)

    return graph, station_to_number, number_to_station


class SubwayNetwork:
    """Convenience container bundling the graph and station mappings."""

    def __init__(self, data):
        self.data = data
        self.graph, self.station_to_number, self.number_to_station = build_graph(data)

    @classmethod
    def from_file(cls, path=DATA_FILE_PATH):
        return cls(load_subway_data(path))

    def station_names(self):
        return list(self.station_to_number.keys())
