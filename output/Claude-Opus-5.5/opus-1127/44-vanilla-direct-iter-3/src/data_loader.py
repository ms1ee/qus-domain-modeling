"""Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
Its layout is::

    {
      "stations":    [{"name": str, "lines": [str, ...]}, ...],
      "connections": [{"source": str, "dest": str,
                       "distance": int (meters), "line": str}, ...]
    }
"""

import json
import os

from models import Edge, Graph

# Absolute path, so it is valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``).
    :raises FileNotFoundError: if the file does not exist.
    :raises json.JSONDecodeError: if the file is not valid JSON.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_graph(data):
    """Build a :class:`Graph` from loaded subway data.

    Station numbers are assigned in the order stations appear in the data.
    Stations that are only referenced by connections are appended afterwards.
    The returned graph exposes ``station_to_number`` and
    ``number_to_station`` dictionaries.
    """
    graph = Graph()
    stations = data.get("stations", []) if isinstance(data, dict) else []
    connections = data.get("connections", []) if isinstance(data, dict) else []

    for record in stations:
        name = record.get("name")
        if not name or name in graph.station_to_number:
            if name in graph.station_to_number:
                # merge lines for duplicated records
                merged = list(graph.station_lines.get(name, []))
                for line in record.get("lines", []) or []:
                    if line not in merged:
                        merged.append(line)
                graph.set_station_lines(name, merged)
            continue
        graph.add_station(name, len(graph.station_to_number), record.get("lines", []) or [])

    for conn in connections:
        src = conn.get("source")
        dst = conn.get("dest")
        if not src or not dst:
            continue
        line = conn.get("line")
        for name in (src, dst):
            if name not in graph.station_to_number:
                graph.add_station(name, len(graph.station_to_number), [line] if line else [])
        distance = conn.get("distance", 0)
        try:
            edge = Edge(graph.station_to_number[src], graph.station_to_number[dst],
                        distance, line)
        except (TypeError, ValueError):
            continue
        graph.add_edge(edge)
    return graph
