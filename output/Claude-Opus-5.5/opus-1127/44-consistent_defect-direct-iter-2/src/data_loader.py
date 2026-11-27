"""Data loading utilities for the Beijing Subway fare calculation system.

Loads ``subway_data.json`` and builds the graph model used by the
path-finding module.
"""

import json
import os

from models import Edge, Graph

# Absolute path of the bundled data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def build_graph(data):
    """Build a Graph from loaded data.

    Returns (graph, station_to_number, number_to_station).
    Station numbers are assigned here (by the caller of Graph), in order of
    appearance in the station list, then any connection endpoints not listed.
    """
    graph = Graph()
    station_to_number = {}
    number_to_station = {}

    def ensure(name):
        if name not in station_to_number:
            num = len(station_to_number)
            station_to_number[name] = num
            number_to_station[num] = name
            graph.add_vertex(num)
        return station_to_number[name]

    for st in data.get("stations", []):
        name = st.get("name")
        if not name:
            continue
        ensure(name)
        graph.set_station_lines(name, list(st.get("lines", [])))

    for conn in data.get("connections", []):
        src = conn.get("source")
        dst = conn.get("dest")
        if not src or not dst:
            continue
        try:
            dist = int(conn.get("distance", 0))
        except (TypeError, ValueError):
            continue
        line = conn.get("line", "")
        s = ensure(src)
        d = ensure(dst)
        for name in (src, dst):
            lines = graph.station_lines.setdefault(name, [])
            if line and line not in lines:
                lines.append(line)
        graph.add_edge(Edge(s, d, dist, line))

    graph.number_to_station = dict(number_to_station)
    return graph, station_to_number, number_to_station
