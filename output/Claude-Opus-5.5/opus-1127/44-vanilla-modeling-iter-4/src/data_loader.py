"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network is stored in ``subway_data.json`` (located next to this
module) with the following structure::

    {
      "stations":    [{"name": str, "lines": [str]}],
      "connections": [{"source": str, "dest": str,
                       "distance": int (meters), "line": str}]
    }

This module provides:

* ``DATA_FILE_PATH``      - absolute path to the data file (independent of cwd)
* ``load_subway_data``    - read the JSON file and return its content
* ``build_network``       - turn the raw data into the station mapping,
                            the adjacency-list ``graph`` dictionary and a
                            :class:`models.Graph` instance
"""

import json
import os

from models import Edge, Graph

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file and return its content as a dict.

    :param path: path of the JSON data file (defaults to ``DATA_FILE_PATH``)
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file content is not valid JSON / not a dict
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in data file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Data file '{path}' must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


class SubwayNetwork:
    """Container for the modeled subway network.

    Attributes:
        data_source:        where the data came from
        station_to_number:  dict mapping station name -> station number
        number_to_station:  dict mapping station number -> station name
        graph:              adjacency-list dict ``{number: [(neighbor, distance, line), ...]}``
        graph_obj:          :class:`models.Graph` instance used by path finding
        lines:              dict mapping line name -> ordered list of station names
    """

    def __init__(self, data, data_source=None):
        self.data_source = data_source
        self.raw_data = data
        self.station_to_number = {}
        self.number_to_station = {}
        self.graph = {}
        self.graph_obj = Graph()
        self.lines = {}
        self._build(data)

    # ------------------------------------------------------------------
    def _register_station(self, name, lines=None):
        if name not in self.station_to_number:
            number = len(self.station_to_number)
            self.station_to_number[name] = number
            self.number_to_station[number] = name
            self.graph[number] = []
            self.graph_obj.add_station(number, name)
        number = self.station_to_number[name]
        existing = self.graph_obj.station_lines.get(name, [])
        merged = list(existing)
        for line in lines or []:
            if line not in merged:
                merged.append(line)
        self.graph_obj.set_station_lines(name, merged)
        for line in lines or []:
            seq = self.lines.setdefault(line, [])
            if name not in seq:
                seq.append(name)
        return number

    def _build(self, data):
        for station in data.get("stations", []):
            name = station.get("name")
            if not name:
                continue
            self._register_station(name, station.get("lines", []) or [])

        for conn in data.get("connections", []):
            src = conn.get("source")
            dst = conn.get("dest")
            if not src or not dst or src == dst:
                continue
            line = conn.get("line")
            try:
                distance = conn.get("distance")
                if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
                    continue
            except Exception:  # pragma: no cover - defensive
                continue
            u = self._register_station(src, [line] if line else [])
            v = self._register_station(dst, [line] if line else [])
            self.graph_obj.add_edge(Edge(u, v, distance, line))
            self.graph[u].append((v, distance, line))
            self.graph[v].append((u, distance, line))

    # ------------------------------------------------------------------
    def station_names(self):
        return list(self.station_to_number.keys())

    def all_lines(self):
        result = []
        for lines in self.graph_obj.station_lines.values():
            for line in lines:
                if line not in result:
                    result.append(line)
        return result

    def is_transfer_station(self, name):
        return len(self.graph_obj.station_lines.get(name, [])) > 1


def build_network(data=None, data_source=None):
    """Build a :class:`SubwayNetwork` from raw data (loads the default file if None)."""
    if data is None:
        data_source = data_source or DATA_FILE_PATH
        data = load_subway_data(data_source)
    return SubwayNetwork(data, data_source)
