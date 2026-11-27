"""Data loading utilities for the Beijing Subway fare calculation system.

The subway network is stored in ``subway_data.json`` located next to this
module.  The format is::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int (meters), "line": str}]}
"""

import json
import os

from models import Edge, Graph

# Absolute path of the bundled data file (valid from any working directory).
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway data file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def build_station_mapping(data):
    """Build ``station_to_number`` and ``number_to_station`` mappings.

    Stations are numbered in the order they appear in the ``stations`` list;
    stations referenced only in connections are appended afterwards.
    """
    station_to_number = {}
    number_to_station = {}

    def _add(name):
        if name not in station_to_number:
            idx = len(station_to_number)
            station_to_number[name] = idx
            number_to_station[idx] = name

    for st in data.get("stations", []):
        name = st.get("name")
        if name:
            _add(name)
    for conn in data.get("connections", []):
        for key in ("source", "dest"):
            name = conn.get(key)
            if name:
                _add(name)
    return station_to_number, number_to_station


def build_graph(data):
    """Build a directed weighted ``Graph`` from the loaded data.

    Returns ``(graph, station_to_number, number_to_station)``.
    """
    station_to_number, number_to_station = build_station_mapping(data)
    graph = Graph()
    for idx in number_to_station:
        graph.add_vertex(idx)
    for st in data.get("stations", []):
        name = st.get("name")
        if name:
            graph.set_station_lines(name, st.get("lines", []) or [])
    for conn in data.get("connections", []):
        src = conn.get("source")
        dst = conn.get("dest")
        if src is None or dst is None:
            continue
        try:
            distance = int(conn.get("distance", 0))
        except (TypeError, ValueError):
            continue
        graph.add_edge(
            Edge(station_to_number[src], station_to_number[dst], distance,
                 conn.get("line"))
        )
    return graph, station_to_number, number_to_station


def build_adjacency_dict(data):
    """Return a ``graph`` dictionary: station name -> list of (neighbor, distance, line)."""
    graph = {}
    for st in data.get("stations", []):
        if st.get("name"):
            graph.setdefault(st["name"], [])
    for conn in data.get("connections", []):
        src, dst = conn.get("source"), conn.get("dest")
        if src is None or dst is None:
            continue
        graph.setdefault(src, []).append((dst, conn.get("distance", 0), conn.get("line")))
        graph.setdefault(dst, [])
    return graph
